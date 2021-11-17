# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, merge_informative_pair, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from functools import reduce

# --------------------------------
import pandas as pd
import numpy as np
import technical.indicators as ftt
from freqtrade.exchange import timeframe_to_minutes
import logging

logger = logging.getLogger(__name__)

# Obelisk_Ichimoku_ZEMA v1 - 2021-05-20
#
# EXPERIMENTAL
#
# RUN AT YOUR OWN RISK
#
# by Obelisk
# https://github.com/brookmiles/


def ssl_atr(dataframe, length=7):
    df = dataframe.copy()
    df['smaHigh'] = df['high'].rolling(length).mean() + df['atr']
    df['smaLow'] = df['low'].rolling(length).mean() - df['atr']
    df['hlv'] = np.where(df['close'] > df['smaHigh'], 1,
                         np.where(df['close'] < df['smaLow'], -1, np.NAN))
    df['hlv'] = df['hlv'].ffill()
    df['sslDown'] = np.where(df['hlv'] < 0, df['smaHigh'], df['smaLow'])
    df['sslUp'] = np.where(df['hlv'] < 0, df['smaLow'], df['smaHigh'])
    return df['sslDown'], df['sslUp']


class IchimokuV1(IStrategy):

    # Optimal timeframe for the strategy
    timeframe = '15m'

    # generate signals from the 1h timeframe
    informative_timeframe = '1h'

    # WARNING: ichimoku is a long indicator, if you remove or use a
    # shorter startup_candle_count your backtest results will be unreliable
    startup_candle_count = 500

    # NOTE: this strat only uses candle information, so processing between
    # new candles is a waste of resources as nothing will change
    process_only_new_candles = True

    # ROI table:
    minimal_roi = {
        "0": 0.078,
        "40": 0.062,
        "99": 0.039,
        "218": 0
    }

    stoploss = -0.294

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe)
                             for pair in pairs]
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        displacement = 26
        ichimoku = ftt.ichimoku(dataframe,
                                conversion_line_period=9,
                                base_line_periods=26,
                                laggin_span=52,
                                displacement=displacement
                                )

        dataframe['chikou_span'] = ichimoku['chikou_span']

        # cross indicators
        dataframe['tenkan_sen'] = ichimoku['tenkan_sen']
        dataframe['kijun_sen'] = ichimoku['kijun_sen']

        # cloud, green a > b, red a < b
        dataframe['senkou_a'] = ichimoku['senkou_span_a']
        dataframe['senkou_b'] = ichimoku['senkou_span_b']
        dataframe['leading_senkou_span_a'] = ichimoku['leading_senkou_span_a']
        dataframe['leading_senkou_span_b'] = ichimoku['leading_senkou_span_b']
        dataframe['cloud_green'] = ichimoku['cloud_green'] * 1
        dataframe['cloud_red'] = ichimoku['cloud_red'] * -1

        dataframe.loc[:, 'cloud_top'] = dataframe.loc[:,
                                                      ['senkou_a', 'senkou_b']].max(axis=1)
        dataframe.loc[:, 'cloud_bottom'] = dataframe.loc[:,
                                                         ['senkou_a', 'senkou_b']].min(axis=1)

        # DANGER ZONE START

        # NOTE: Not actually the future, present data that is normally shifted forward for display as the cloud
        dataframe['future_green'] = (
            dataframe['leading_senkou_span_a'] > dataframe['leading_senkou_span_b']).astype('int') * 2
        dataframe['future_red'] = (dataframe['leading_senkou_span_a']
                                   < dataframe['leading_senkou_span_b']).astype('int') * 2

        # The chikou_span is shifted into the past, so we need to be careful not to read the
        # current value.  But if we shift it forward again by displacement it should be safe to use.
        # We're effectively "looking back" at where it normally appears on the chart.
        dataframe['chikou_high'] = (
            (dataframe['chikou_span'] > dataframe['cloud_top'])
        ).shift(displacement).fillna(0).astype('int')

        dataframe['chikou_low'] = (
            (dataframe['chikou_span'] < dataframe['cloud_bottom'])
        ).shift(displacement).fillna(0).astype('int')

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(
            (
                (dataframe['volume'] > 0)
            )
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'buy'
            ]

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        conditions.append(
            (
                dataframe['volume'] > 0
            )
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'sell'
            ]=1

        return dataframe

    def confirm_trade_exit(self, pair: str, trade: 'Trade', order_type: str, amount: float,
                           rate: float, time_in_force: str, sell_reason: str,
                           current_time: 'datetime', **kwargs) -> bool:

        if sell_reason in ('roi',):
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            current_candle = dataframe.iloc[-1]
            if current_candle is not None:
                current_candle = current_candle.squeeze()
                # don't sell during ichimoku uptrend
                if current_candle['trending'] > 0:
                    return False

        return True

    plot_config = {
        # Main plot indicators (Moving averages, ...)
        'main_plot': {
            'senkou_a': {
                'color': 'green',
                'fill_to': 'senkou_b',
                'fill_label': 'Ichimoku Cloud',
                'fill_color': 'rgba(0,0,0,0.2)',
            },
            # plot senkou_b, too. Not only the area to it.
            'senkou_b': {
                'color': 'red',
            },
            'tenkan_sen': {'color': 'blue'},
            'kijun_sen': {'color': 'orange'},

            # 'chikou_span': { 'color': 'lightgreen' },

            'ssl_up': {'color': 'green'},
            # 'ssl_down': { 'color': 'red' },

            # 'ema50': { 'color': 'violet' },
            # 'ema200': { 'color': 'magenta' },

            'zema_buy': {'color': 'blue'},
            'zema_sell': {'color': 'orange'},
        },
        'subplots': {
            "Trend": {
                'trending': {'color': 'green'},
                'bear_trending': {'color': 'red'},
            },
            "Bull": {
                'trend_pulse': {'color': 'blue'},
                'trending': {'color': 'orange'},
                'trend_over': {'color': 'red'},
            },
            "Bull Signals": {
                'ichimoku_ok': {'color': 'green'},
                'ssl_ok': {'color': 'red'},
            },
            "Bear": {
                'bear_trend_pulse': {'color': 'blue'},
                'bear_trending': {'color': 'orange'},
                'bear_trend_over': {'color': 'red'},
            },
            "Bear Signals": {
                'ichimoku_bear': {'color': 'green'},
                'ssl_bear': {'color': 'red'},
            },
            "Misc": {
                'ichimoku_valid': {'color': 'green'},
            },
        }
    }

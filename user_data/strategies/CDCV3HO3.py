# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from functools import reduce

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class CDCV3HO3(IStrategy):
    # from https://www.tradingview.com/script/rGpAOoLi-CDC-ActionZone-V3-2020/

    INTERFACE_VERSION = 2

    buy_params = {
        'buy_0': True,
        'buy_1': True,
        'buy_2': True,
        'ob_lvl': 30,

    }

    sell_params = {
        'sell_0': True,
        'sell_1': True,
        'sell_2': False,
        'os_lvl': 70,
    }

    # custom params
    buy_0 = BooleanParameter(
        default=buy_params['buy_0'], space='buy', optimize=True)
    buy_1 = BooleanParameter(
        default=buy_params['buy_1'], space='buy', optimize=True)
    buy_2 = BooleanParameter(
        default=buy_params['buy_2'], space='buy', optimize=True)
    ob_lvl = IntParameter(
        0, 50, default=buy_params['ob_lvl'], space="buy", optimize=True)

    sell_0 = BooleanParameter(
        default=sell_params['sell_0'], space='sell', optimize=True)
    sell_1 = BooleanParameter(
        default=sell_params['sell_1'], space='sell', optimize=True)
    sell_2 = BooleanParameter(
        default=sell_params['sell_2'], space='sell', optimize=True)

    os_lvl = IntParameter(
        30, 90, default=sell_params['os_lvl'], space="sell", optimize=True)

    minimal_roi = {
        "0": 0.15,
        "720": 0.10,
        "1080": 0.05,
        "1440": 0.03
    }

    stoploss = -0.99

    # Trailing stoploss
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.05  # Disabled / not configured

    # Optimal timeframe for the strategy.
    timeframe = '1h'

    inf_tf = '1h'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the "ask_strategy" section in the config.
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Optional order type mapping.
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
    }

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        inf_pair = [(pair, self.inf_tf) for pair in pairs]
        return inf_pair

    def get_informative_indicators(self, metadata: dict):

        dataframe = self.dp.get_pair_dataframe(
            pair=metadata['pair'], timeframe=self.inf_tf)

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # ema
        dataframe["fast_ema"] = ta.EMA(dataframe, 12)
        dataframe["slow_ema"] = ta.EMA(dataframe, 26)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, 14)

        # ADX
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['s_adx'] = (dataframe['adx'] >= 50)

        # STOCHRSI
        period = 14
        smooth_d = 3
        smooth_k = 3
        stochrsi = (dataframe['rsi'] - dataframe['rsi'].rolling(period).min()) / (
            dataframe['rsi'].rolling(period).max() - dataframe['rsi'].rolling(period).min())
        dataframe['srsi_k'] = stochrsi.rolling(smooth_k).mean() * 100
        dataframe['srsi_d'] = dataframe['srsi_k'].rolling(smooth_d).mean()

        # condition buy
        dataframe['bull'] = dataframe['fast_ema'] > dataframe['slow_ema']
        dataframe['buy_0'] = ((dataframe['fast_ema'] > dataframe["slow_ema"]) & (dataframe['fast_ema'].shift(
            1) <= dataframe['slow_ema'].shift(1)) & dataframe['s_adx'])

        dataframe['buy_1'] = (
            (dataframe['srsi_d'] < self.ob_lvl.value) & dataframe['s_adx'])

        dataframe['buy_2'] = dataframe['srsi_d'] > self.ob_lvl.value

        # condition sell
        dataframe['bear'] = dataframe['fast_ema'] < dataframe['slow_ema']
        dataframe['sell_0'] = ((dataframe['fast_ema'] < dataframe["slow_ema"]) & (dataframe['fast_ema'].shift(
            1) >= dataframe['slow_ema'].shift(1)))

        dataframe['sell_1'] = dataframe['srsi_d'] > self.os_lvl.value
        dataframe['sell_2'] = dataframe['srsi_d'] < self.os_lvl.value

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        if self.buy_0.value:
            conditions.append((
                dataframe['buy_0']
                & (dataframe['volume'] > 0)
            ))

        if self.buy_1.value:
            conditions.append(
                (
                    dataframe['buy_1']
                    & qtpylib.crossed_above(dataframe['srsi_k'], dataframe['srsi_d'])
                    & (dataframe['volume'] > 0)
                )
            )

        if self.buy_2.value:
            conditions.append(
                (
                    dataframe['buy_2']
                    & qtpylib.crossed_above(dataframe['srsi_k'], dataframe['srsi_d'])
                    & (dataframe['volume'] > 0)
                )
            )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'buy'
            ]=1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        if self.sell_0.value:
            conditions.append((
                (dataframe['sell_0'])
                & (dataframe['volume'] > 0)
            ))

        if self.sell_1.value:
            conditions.append(
                (
                    dataframe['sell_1']
                    & dataframe['bear']
                    & qtpylib.crossed_above(dataframe['srsi_k'], dataframe['srsi_d'])
                    & (dataframe['volume'] > 0)
                )
            )

        if self.sell_2.value:
            conditions.append(
                (
                    dataframe['sell_2']
                    & dataframe['bear']
                    & qtpylib.crossed_above(dataframe['srsi_k'], dataframe['srsi_d'])
                    & (dataframe['volume'] > 0)
                )
            )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'sell'
            ]=1

        return dataframe

    plot_config = {
        # Main plot indicators (Moving averages, ...)
        'main_plot': {
            'tema': {},
            'sar': {'color': 'white'},
        },
        'subplots': {
            # Subplots - each dict defines one additional plot
            "MACD": {
                'macd': {'color': 'blue'},
                'macdsignal': {'color': 'orange'},
            },
            "RSI": {
                'rsi': {'color': 'red'},
            }
        }
    }

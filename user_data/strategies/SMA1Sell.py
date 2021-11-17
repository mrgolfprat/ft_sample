from datetime import datetime
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IntParameter
from freqtrade.strategy.interface import IStrategy

# Author @Jooopieeert#0239
class SMA1Sell(IStrategy):
    INTERFACE_VERSION = 2
    buy_params = {
        "base_nb_candles_buy": 18,
        "low_offset": 0.968,
    }
    sell_params = {
        "base_nb_candles_sell": 26,
        "high_offset": 0.985,
    }

    base_nb_candles_buy = IntParameter(16, 60, default=buy_params['base_nb_candles_buy'], space='buy', optimize=True)
    base_nb_candles_sell = IntParameter(16, 60, default=sell_params['base_nb_candles_sell'], space='sell', optimize=False)
    low_offset = DecimalParameter(0.8, 0.99, default=buy_params['low_offset'], space='buy', optimize=True)
    high_offset = DecimalParameter(0.8, 1.1, default=sell_params['high_offset'], space='sell', optimize=False)

    timeframe = '5m'
    stoploss = -0.23
    minimal_roi = {"0": 10,}
    trailing_stop = False
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.003
    trailing_stop_positive_offset = 0.018
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False
    process_only_new_candles = True
    startup_candle_count = 400

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['rsi_exit'] = ta.RSI(dataframe, timeperiod=2)
        if not self.config['runmode'].value == 'hyperopt':
            dataframe['ma_offset_buy'] = ta.SMA(dataframe, int(self.base_nb_candles_buy.value)) * self.low_offset.value
            dataframe['ma_offset_sell'] = ta.EMA(dataframe, int(self.base_nb_candles_sell.value)) * self.high_offset.value
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.config['runmode'].value == 'hyperopt':
            dataframe['ma_offset_buy'] = ta.SMA(dataframe, int(self.base_nb_candles_buy.value)) * self.low_offset.value
        dataframe.loc[
            (
                    (dataframe['ema_50'] > dataframe['ema_200']) &
                    (dataframe['close'] > dataframe['ema_200']) &
                    (dataframe['close'] < dataframe['ma_offset_buy']) &
                    (dataframe['volume'] > 0)
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.config['runmode'].value == 'hyperopt':
            dataframe['ma_offset_sell'] = ta.EMA(dataframe, int(self.base_nb_candles_sell.value)) * self.high_offset.value
        dataframe.loc[
            (
                    (dataframe['close'] > dataframe['ma_offset_sell']) &
                    (
                        (dataframe['open'] < dataframe['open'].shift(1)) |
                        (dataframe['rsi_exit'] < 50) |
                        (dataframe['rsi_exit'] < dataframe['rsi_exit'].shift(1))
                    ) &
                    (dataframe['volume'] > 0)
            ),
            'sell'] = 1
        return dataframe

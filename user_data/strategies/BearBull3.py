from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame
import talib.abstract as ta

# based on BinHV45 strategy: https://github.com/freqtrade/freqtrade-strategies/blob/master/user_data/strategies/berlinguyinca/BinHV45.py
# use at own risk

class BearBull3(IStrategy):

    timeframe = '3m' # works best on short timeframes 3 or 5 min

    minimal_roi = {
        "0": 0.15,
    }

    stoploss = -0.15

    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    startup_candle_count = 200

    def informative_pairs(self):

        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, '2h') for pair in pairs]
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # macd timeframe for trend detection
        macd_df = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='2h')
        macd_df['macdhist'] = ta.MACD(macd_df, fastperiod=10, slowperiod=20, signalperiod=10)['macdhist']
        dataframe = merge_informative_pair(dataframe, macd_df, self.timeframe, '2h', ffill=True)

        # normal timeframe
        bb = ta.BBANDS(dataframe, timeperiod=40, nbdevup=2.0, nbdevdn=2.0)
        dataframe['mid'] = bb['middleband']
        dataframe['lower'] = bb['lowerband']
        dataframe['bbdelta'] = (dataframe['mid'] - dataframe['lower']).abs()
#        dataframe['pricedelta'] = (dataframe['open'] - dataframe['close']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (
                    (
                        dataframe['macdhist_2h'].lt(0) #Bear
                        &
                        dataframe['lower'].shift().gt(0)
                        &
                        dataframe['bbdelta'].gt(dataframe['close'] * 0.014)
                        &
                        dataframe['closedelta'].gt(dataframe['close'] * 0.008)
                        &
                        dataframe['tail'].lt(dataframe['bbdelta'] * 0.23)
                        &
                        dataframe['close'].lt(dataframe['lower'].shift())
                        &
                        dataframe['close'].le(dataframe['close'].shift())
                    )
                    |
                    (
                        dataframe['macdhist_2h'].gt(0) # Bull
                        &
                        dataframe['lower'].shift().gt(0)
                        &
                        dataframe['bbdelta'].gt(dataframe['close'] * 0.035)
                        &
                        dataframe['closedelta'].gt(dataframe['close'] * 0.007)
                        &
                        dataframe['tail'].lt(dataframe['bbdelta'] * 0.2)
                        &
                        dataframe['close'].lt(dataframe['lower'].shift())
                        &
                        dataframe['close'].le(dataframe['close'].shift())
                    )
                )
                &
                (dataframe['volume'] > 0)
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        no sell signal
        """
        dataframe['sell'] = 0
        return dataframe

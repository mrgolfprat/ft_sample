# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame, Series
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter
import freqtrade.vendor.qtpylib.indicators as qtpylib
pd.set_option("display.precision",8)

class bbrsittfv1(IStrategy):
    INTERFACE_VERSION = 3

    stoploss = -0.99
    timeframe = '15m'

    #############################################################

    #TTF
    ttf_length       = IntParameter(1, 50, default=15)
    ttf_upperTrigger = IntParameter(1, 400, default=100)
    ttf_lowerTrigger = IntParameter(1, -400, default=-100)

    plot_config = {
        'main_plot': {
            'bb_upperband': {'color': 'blue'},
            'bb_middleband': {'color': 'white'},
            'bb_lowerband': {'color': 'yellow'},
        },
        'subplots': {
            "RSI": {
                'rsi': {'color': 'blue'},
                'rsiob': {'color': '#d3d3d3'},
                'rsios': {'color': '#d3d3d3'},
            },
            "TTF": {
                'ttf': {'color': 'red'},
                'ttfhigh': {'color': '#d3d3d3'},
                'ttflow': {'color': '#d3d3d3'},
            }
        }
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # TTF -  Trend Trigger Factor
        dataframe['ttf'] = ttf(dataframe, self.ttf_length.value)
        dataframe['ttfhigh'] = self.ttf_upperTrigger.value
        dataframe['ttflow'] = self.ttf_lowerTrigger.value

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsiob'] = 70
        dataframe['rsios'] = 30

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['ttf'] < self.ttf_lowerTrigger.value) &
                (dataframe['close'] < dataframe['bb_lowerband'])
            ),
            'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) &
                (dataframe['ttf'] > self.ttf_upperTrigger.value) &
                (dataframe['close'] > dataframe['bb_upperband'])
            ),
            'sell'] = 1
        return dataframe

def ttf(dataframe, ttf_length):
    # Thanks to FeelsGoodMan for the TTF Maths
    df = dataframe.copy()
    high, low = df['high'], df['low']
    buyPower = high.rolling(ttf_length).max() - low.shift(ttf_length).fillna(99999).rolling(ttf_length).min()
    sellPower = high.shift(ttf_length).fillna(0).rolling(ttf_length).max() - low.rolling(ttf_length).min()
    
    ttf = 200 * (buyPower - sellPower) / (buyPower + sellPower)
    return Series(ttf, name ='ttf')
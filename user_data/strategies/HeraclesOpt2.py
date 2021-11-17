# Heracles Strategy: Strongest Son of GodStra
# ( With just 1 Genome! its a bacteria :D )
# Author: @Mablue (Masoud Azizi)
# github: https://github.com/mablue/
# IMPORTANT:Add to your pairlists inside config.json (Under StaticPairList):
#   {
#       "method": "AgeFilter",
#       "min_days_listed": 100
#   },
# IMPORTANT: INSTALL TA BEFOUR RUN(pip install ta)
# ######################################################################
# Optimal config settings:
# "max_open_trades": 100,
# "stake_amount": "unlimited",

# --- Do not remove these libs ---
import logging

from numpy.lib import math
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
# --------------------------------

# Add your lib to import here
# import talib.abstract as ta
import pandas as pd
import ta
from ta.utils import dropna
import freqtrade.vendor.qtpylib.indicators as qtpylib
from functools import reduce
import numpy as np


class HeraclesOpt2(IStrategy):
    # 65/600:   2275 trades. 1438/7/830 W/D/L.
    # Avg profit   3.10%. Median profit   3.06%.
    # Total profit  113171 USDT ( 7062 Σ%).
    # Avg duration 345 min. Objective: -23.0

    # Buy hyperspace params:
    buy_params = {
        "buy-div": 0.24933,
        "DFINDShift": 1,
        "DFCRSShift": 5,
    }

    # Sell hyperspace params:
    sell_params = {
        "sell-rtol": 0.88537,
        "sell-atol": 0.29868,
        "DFINDShift": 1,
        "DFCRSShift": 5,
    }

    # ROI table:
    minimal_roi = {
        "0": 0.621,
        "3100": 0.241,
        "6961": 0.078,
        "20515": 0
    }

    # Stoploss:
    stoploss = -0.041

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.24
    trailing_stop_positive_offset = 0.274
    trailing_only_offset_is_reached = False

    # Buy hypers
    timeframe = '12h'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Add all ta features
        dataframe = dropna(dataframe)

        dataframe['volatility_kcw'] = ta.volatility.keltner_channel_wband(
            dataframe['high'],
            dataframe['low'],
            dataframe['close'],
            window=20,
            window_atr=10,
            fillna=False,
            original_version=True
        )
        dataframe['volatility_dcp'] = ta.volatility.donchian_channel_pband(
            dataframe['high'],
            dataframe['low'],
            dataframe['close'],
            window=10,
            offset=0,
            fillna=False
        )
        dataframe['trend_macd_signal'] = ta.trend.macd_signal(
            dataframe['close'],
            window_slow=26,
            window_fast=12,
            window_sign=9,
            fillna=False
        )

        dataframe['trend_ema_fast'] = ta.trend.EMAIndicator(
            close=dataframe['close'], window=12, fillna=False
        ).ema_indicator()

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Buy strategy Hyperopt will build and use.
        """
        conditions = []

        IND = 'volatility_dcp'
        CRS = 'volatility_kcw'
        DFIND = dataframe[IND]
        DFCRS = dataframe[CRS]

        conditions.append(
            DFIND.shift(self.buy_params['DFINDShift']).div(
                DFCRS.shift(self.buy_params['DFCRSShift'])
            ) <= self.buy_params['buy-div']
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Sell strategy Hyperopt will build and use.
        """
        conditions = []

        IND = 'trend_ema_fast'
        CRS = 'trend_macd_signal'
        DFIND = dataframe[IND]
        DFCRS = dataframe[CRS]

        conditions.append(
            np.isclose(
                DFIND.shift(self.sell_params['DFINDShift']),
                DFCRS.shift(self.sell_params['DFCRSShift']),
                rtol=self.sell_params['sell-rtol'],
                atol=self.sell_params['sell-atol']
            )
        )

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell']=1

        return dataframe

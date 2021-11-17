import talib.abstract as ta
from pandas import DataFrame
from typing import Dict, Any, Callable, List
from functools import reduce

from skopt.space import Categorical, Dimension, Integer, Real

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.optimize.hyperopt_interface import IHyperOpt

shortRangeBegin = 10
shortRangeEnd = 20
mediumRangeBegin = 100
mediumRangeEnd = 120


class AverageHyperopt(IHyperOpt):
    """
    Hyperopt file for optimizing AverageStrategy.
    Uses ranges of EMA periods to find the best parameter combination.
    """

    @staticmethod
    def populate_indicators(dataframe: DataFrame, metadata: dict) -> DataFrame:

        for short in range(shortRangeBegin, shortRangeEnd):
            dataframe[f'maShort({short})'] = ta.EMA(dataframe, timeperiod=short)

        for medium in range(mediumRangeBegin, mediumRangeEnd):
            dataframe[f'maMedium({medium})'] = ta.EMA(dataframe, timeperiod=medium)

        return dataframe

    @staticmethod
    def buy_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the buy strategy parameters to be used by hyperopt
        """
        def populate_buy_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            """
            Buy strategy Hyperopt will build and use
            """
            conditions = []
            # TRIGGERS
            if 'trigger' in params:
                trigger = [int(item) for item in params['trigger'].split('-')]

                conditions.append(qtpylib.crossed_above(
                    dataframe[f"maShort({trigger[0]})"],
                    dataframe[f"maMedium({trigger[1]})"])
                    )

            # Check that volume is not 0
            conditions.append(dataframe['volume'] > 0)

            if conditions:
                dataframe.loc[
                    reduce(lambda x, y: x & y, conditions),
                    'buy'] = 1

            return dataframe

        return populate_buy_trend

    @staticmethod
    def indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching strategy parameters
        """
        buyTriggerList = []
        for short in range(shortRangeBegin, shortRangeEnd):
            for medium in range(mediumRangeBegin, mediumRangeEnd):
                """
                The output will be '{short}-{long}' so we can split it on the trigger
                this will prevent an error on scikit-optimize not accepting tuples as
                first argument to Categorical
                """
                buyTriggerList.append(
                    '{}-{}'.format(short, medium)
                )
        return [
            Categorical(buyTriggerList, name='trigger')
        ]

    @staticmethod
    def sell_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the sell strategy parameters to be used by hyperopt
        """
        def populate_sell_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            """
            Sell strategy Hyperopt will build and use
            """
            # print(params)
            conditions = []

            # TRIGGERS
            if 'sell-trigger' in params:
                trigger = [int(item) for item in params['sell-trigger'].split('-')]

                conditions.append(qtpylib.crossed_above(
                    dataframe[f"maMedium({trigger[1]})"],
                    dataframe[f"maShort({trigger[0]})"])
                )

            if conditions:
                dataframe.loc[
                    reduce(lambda x, y: x & y, conditions),
                    'sell'] = 1

            return dataframe

        return populate_sell_trend

    @staticmethod
    def sell_indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching sell strategy parameters
        """
        sellTriggerList = []
        for short in range(shortRangeBegin, shortRangeEnd):
            for medium in range(mediumRangeBegin, mediumRangeEnd):
                """
                The output will be '{short}-{long}' so we can split it on the trigger
                this will prevent an error on scikit-optimize not accepting tuples as
                first argument to Categorical
                """
                sellTriggerList.append(
                    '{}-{}'.format(short, medium)
                )

        return [
            Categorical(sellTriggerList, name='sell-trigger')
        ]

#!/bin/bash


docker-compose run --rm freqtrade hyperopt --hyperopt-loss SharpeHyperOptLossDaily --spaces stoploss --strategy ElliotV5HOMod1 --timerange 20210715-20210815 --config user_data/config-hyperopt.json -j 1
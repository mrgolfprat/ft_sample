#!/bin/bash


docker-compose run --rm freqtrade backtesting --export trades --strategy-list ElliotV5HO NASOSv4HO --timerange=20211020- -c user_data/config-backtest.json -i 5m
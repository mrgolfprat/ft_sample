#!/bin/bash

docker-compose run --rm freqtrade plot-dataframe --strategy ElliotV5HO -p CHR/BUSD -c user_data/config-backtest.json -i 5m
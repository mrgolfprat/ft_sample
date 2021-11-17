#!/bin/bash

docker-compose run --rm freqtrade edge -s ElliotV5HOMod3 --timerange=20210807- -c user_data/config-backtest.json -i 5m
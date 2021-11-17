#!/bin/bash

docker-compose run --rm freqtrade download-data --days 30 -t 5m 1h -c user_data/config-backtest.json
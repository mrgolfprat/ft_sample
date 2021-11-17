#!/bin/bash

docker-compose run --rm freqtrade test-pairlist --config user_data/config.json --quote BUSD --print-json
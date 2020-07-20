#!/bin/bash

source ~/venvbot/bin/activate

cd ~/yata-bot/

export DB_CREDENTIALS='{"dbname": "x", "user": "x", "password": "x", "host": "x", "port": "x"}'
export YATA_ID="1"
export GITHUB_TOKEN='x'

kill -9 $(cat bot.pid)
nohup python yata.py > bot.log 2>&1 &
echo $! > bot.pid

#python yata.py

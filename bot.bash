#!/bin/bash

source ~/venvbot/bin/activate

cd ~/yata-bot/

source source.bash
export YATA_ID="3"

kill -9 $(cat bot.pid)
nohup python yata.py > bot.log 2>&1 &
echo $! > bot.pid

#python yata.py

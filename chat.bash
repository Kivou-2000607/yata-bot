#!/bin/bash

source ~/venvbot/bin/activate
pip install -U cloudscraper

cd ~/yata-bot/

source source.bash

kill -9 $(cat chat-faction.pid)
nohup python chat-faction.py > chat-faction.log 2>&1 &
echo $! > chat-faction.pid

kill -9 $(cat chat-trade.pid)
nohup python chat-trade.py > chat-trade.log 2>&1 &
echo $! > chat-trade.pid

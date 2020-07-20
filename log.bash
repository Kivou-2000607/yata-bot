#!/bin/bash


source ~/venvbot/bin/activate

cd ~/yata-bot/

kill -9 $(cat stream-log.pid)
nohup python stream-log.py > stream-log.log 2>&1 &
echo $! > stream-log.pid

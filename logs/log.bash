#!/bin/bash


source ~/venvbot/bin/activate

cd ~/yata-bot/

source source.bash

kill -9 $(cat log.pid)
nohup python log.py > log.log 2>&1 &
echo $! > log.pid

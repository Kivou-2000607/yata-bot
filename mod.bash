#!/bin/bash

source ~/venvbot/bin/activate

cd ~/yata-bot/

source source.bash
export YATA_ID="2"

kill -9 $(cat mod.pid)
nohup python yata.py > mod.log 2>&1 &
echo $! > mod.pid

#python yata.py

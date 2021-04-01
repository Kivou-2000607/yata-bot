#!/bin/bash

source ~/.virtualenvs/yata-bot/bin/activate

echo "    kill $1"
kill -9 $(cat pids/$1.pid)
echo "    run $1"
nohup python yata.py ".env-$1" > logs/$1.log 2>&1 &
echo $! > pids/$1.pid

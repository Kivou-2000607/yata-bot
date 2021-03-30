#!/bin/bash

# load virtual env
source /usr/local/share/venv_py3.9/bin/activate
#pip install -U cloudscraper

# move to appropriate folder
# cd ~/yata-bot/

# run the yata bot
echo "    kill yata"
kill -9 $(cat pids/yata.pid)
echo "    run yata"
nohup python yata.py ".env-yata" > logs/yata.log 2>&1 &
echo $! > pids/yata.pid

# run marvin
echo "    kill marvin"
kill -9 $(cat pids/marvin.pid)
echo "    run marvin"
nohup python yata.py ".env-marvin" > logs/marvin.log 2>&1 &
echo $! > pids/marvin.pid

# send the logs
echo "    kill logs"
kill -9 $(cat pids/logs.pid)
echo "    run logs"
nohup python logs.py ".env-yata" > logs/logs.log 2>&1 &
echo $! > pids/logs.pid

# python yata.py

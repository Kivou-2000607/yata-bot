#!/bin/bash

# load virtual env
source /usr/local/share/venv_py3.9/bin/activate
#pip install -U cloudscraper

# move to appropriate folder
cd ~/yata-bot/

# run the yata bot
kill -9 $(cat pids/yata.pid)
nohup python yata.py ".env-yata" > logs/yata.log 2>&1 &
echo $! > pids/yata.pid

# run marvin
kill -9 $(cat pids/marvin.pid)
nohup python yata.py ".env-marvin" > logs/marvin.log 2>&1 &
echo $! > pids/marvin.pid

# run the nub bot
kill -9 $(cat pids/nub.pid)
nohup python yata.py ".env-nub" > logs/nub.log 2>&1 &
echo $! > pids/nub.pid

# send the logs
kill -9 $(cat pids/logs.pid)
nohup python logs.py ".env-yata" > logs/logs.log 2>&1 &
echo $! > pids/logs.pid

# python yata.py

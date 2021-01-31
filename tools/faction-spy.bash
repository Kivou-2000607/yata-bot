#!/bin/bash

source ~/.virtualenvs/yata-bot/bin/activate

cd ~/yata-bot/tools/

python faction-spy.py --instance $1 >> faction-spy-$1.log

#!/bin/bash

source /usr/local/share/venv_py3.9/bin/activate

echo "    kill $1"
kill -9 $(cat pids/$1.pid)
echo "    run $1"
nohup python $1.py ".env-$1" > logs/$1.log 2>&1 &
echo $! > pids/$1.pid

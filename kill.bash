#!/bin/bash

echo "    kill $1"
kill -9 $(cat pids/$1.pid)

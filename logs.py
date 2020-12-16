import sys
import os
import sh
import requests
# change folder for .env file if
if len(sys.argv) > 1:
    from decouple import AutoConfig
    print(os.path.join(os.getcwd(), sys.argv[1]))
    config = AutoConfig(search_path=os.path.join(os.getcwd(), sys.argv[1]))
else:
    from decouple import config


for line in sh.tail("-f", "./logs/yata.log", _iter=True):
    log = '```{}```'.format(line.strip())
    x = requests.post(config("WEBHOOK_LOG"), data={"content": log})

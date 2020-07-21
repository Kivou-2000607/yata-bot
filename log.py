import os
import sh
import requests

for line in sh.tail("-f", "./bot.log", _iter=True):
    log = '```{}```'.format(line.strip())
    x = requests.post(os.environ.get("WEBHOOK_LOG"), data={"content": log})

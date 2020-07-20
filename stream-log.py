import sh
import requests

webhook_url ="https://discordapp.com/api/webhooks/x/x"

for line in sh.tail("-f", "./yata-bot.log", _iter=True):
    log = '```{}```'.format(line.strip())
    x = requests.post(webhook_url, data={"content": log})

# # import standard modules
import requests
import os
import json
import psycopg2

# import discord modules
from discord import Webhook, RequestsWebhookAdapter
from discord import Embed

# import bot functions and classes
import includes.formating as fmt




class LootHook():
    def __init__(self):
        
        # get configurations from YATA's database
        db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
        con = psycopg2.connect(**db_cred)
        cur = con.cursor()
        cur.execute("SELECT * FROM bot_configuration WHERE id = 1;")
        _, _, configs = cur.fetchone()
        cur.close()
        con.close()

        # create tokens
        hooks = dict({})
        for k, v in json.loads(configs).items():
            if v.get("loot_hook") is not None and v.get("loot_hook") is not None:
                hooks[v.get("loot_hook")] = v.get("loot_id")

        self.hooks = hooks

    def notify(self):

        # images and items
        thumbs = {'4': "https://i.snipboard.io/hUlRLD.jpg", '15': "https://i.snipboard.io/U2v1QZ.jpg"}
        thumbd = "https://cdn.discordapp.com/app-icons/547341843788988416/32772ee397ec7c5d9cb85fd530c8f58e.png"
        items = {'4': ["Rheinmetall MG", "Homemade Pocket Shotgun", "Madball", "Nail Bomb"], '15': ["Nock Gun", "Beretta Pico", "Riding Crop", "Sand"]}
        itemd = "Nice item"

        # YATA api
        url = "https://yata.alwaysdata.net/loot/timings/"
        req = requests.get(url).json()

        # loop over NPCs
        mentions = []
        embeds = []
        for id, npc in req.items():
            lvl = npc["levels"]["current"]
            due = npc["timings"]["4"]["due"]
            ts = npc["timings"]["4"]["ts"]

            ll = {0: "hospitalized", 1: "level I", 2: "level II", 3: "level III", 4: "level IV", 5: " level V"}
            if due > -60 and due < 10 * 60:
                notification = "{} {}".format(npc["name"], "in " + fmt.s_to_ms(due) if due > 0 else "**NOW**")
                mentions.append(notification)

                title = "**{}** is currently {}".format(npc["name"], ll[lvl])
                msg = "{}".format("https://www.torn.com/profiles.php?XID={}".format(id))
                embed = Embed(title=title, description=msg, color=550000)

                if due < 0:
                    embed.add_field(name='Loot level IV since', value='{}'.format(fmt.s_to_ms(abs(due))))
                    embed.add_field(name='Date', value='{} TCT'.format(fmt.ts_to_datetime(npc["timings"]["4"]["ts"]).strftime("%y/%m/%d %H:%M:%S")))
                else:
                    embed.add_field(name='Loot {} in'.format(ll[lvl + 1]), value='{}'.format(fmt.s_to_ms(due)))
                    embed.add_field(name='At', value='{} TCT'.format(fmt.ts_to_datetime(ts).strftime("%H:%M:%S")))

                url = thumbs.get(id, thumbd)
                embed.set_thumbnail(url=url)
                embed.set_footer(text='Items to loot: {}'.format(', '.join(items.get(id, ["Nice things"]))))
                embeds.append(embed)

        if len(mentions):
            # send notifications for all hooks
            for k, v in self.hooks.items():
                webhook = Webhook.from_url(k, adapter=RequestsWebhookAdapter())
                content = "<@&{}> Go for {}, equip Tear Gas or Smoke Grenade".format(v, " and ".join(mentions))
                webhook.send(content, username='Loot', embeds=embeds)

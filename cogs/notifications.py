# import standard modules
import asyncio
import asyncpg
import os
import aiohttp
import json

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get

# import bot functions and classes
import includes.formating as fmt


class Notifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

    @tasks.loop(minutes=5)
    async def notify(self):
        print("[NOTIFICATIONS] start task")

        # YATA guild
        # guild = get(self.bot.guilds, id=432226682506575893)  # nub navy guild
        guild = get(self.bot.guilds, id=581227228537421825)  # yata guild

        # connect to YATA database of notifiers
        db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
        dbname = db_cred["dbname"]
        del db_cred["dbname"]
        sql = 'SELECT "tId", "dId", "notifications", "key" FROM player_player WHERE "activateNotifications" = True;'
        con = await asyncpg.connect(database=dbname, **db_cred)

        # async loop over notifiers
        async with con.transaction():
            async for record in con.cursor(sql, prefetch=50, timeout=2):

                # get corresponding discord member
                member = get(guild.members, id=record["dId"])
                if member is None:
                    continue

                # make Torn API call
                url = f'https://api.torn.com/user/?selections=events&key={record["key"]}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                notifications = json.loads(record["notifications"])

                # notify news
                if "event" in notifications:
                    # loop over events
                    for k, v in req["events"].items():

                        # if new event not notified -> notify
                        if not v["seen"] and k not in notifications["news"]:
                            await member.send(fmt.cleanhtml(v["event"]))
                            notifications["news"][k] = True

                        # if seen even already notified -> clean table
                        elif v["seen"] and k in notifications["news"]:
                            del notifications["news"][k]

                # update notifications in YATA's database
                await con.execute('UPDATE player_player SET "notifications"=$1 WHERE "dId"=$2', json.dumps(notifications), member.id)

        await con.close()

    @notify.before_loop
    async def before_notify(self):
        print('[NOTIFICATIONS] waiting...')
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

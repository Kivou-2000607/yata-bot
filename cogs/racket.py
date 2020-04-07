# import standard modules
import asyncio
import aiohttp
import datetime
import json
import re

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt
from includes.yata_db import get_rackets
from includes.yata_db import push_rackets
from includes.yata_db import get_faction_name


class Racket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.racketsTask.start()

    def cog_unload(self):
        self.racketsTask.cancel()


    @tasks.loop(minutes=15)
    async def racketsTask(self):
        print("[RACKETS] start task")

        guild = self.bot.get_guild(581227228537421825)
        _, _, key = await self.bot.get_master_key(guild)
        url = f'https://api.torn.com/torn/?selections=rackets,territory,timestamp&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        if "error" in req:
            return

        timestamp_p, randt_p = get_rackets()
        rackets_p = randt_p["rackets"]
        territory_p = randt_p["territory"]

        tsnow = int(req["timestamp"])
        mentions = []
        for k, v in req["rackets"].items():
            title = False
            war = v.get("war", False)
            # New racket
            if k not in rackets_p:
                title = "New racket"

            elif v["level"] != rackets_p[k]["level"]:
                title = f'Racket moved {"up" if v["level"] > rackets_p[k]["level"] else "down"} from {rackets_p[k]["level"]} to {v["level"]}'

            if title:
                factionO = await get_faction_name(v["faction"])

                lst = [f'**{title}**',
                       f'```YAML',
                       f'Territory: {k}',
                       f'Name: {v["name"]}',
                       f'Reward: {v["reward"]}',
                       f'Level: {v["level"]}',
                       f'Created: {fmt.ts_to_datetime(v["created"], fmt="short")}',
                       f'Changed: {fmt.ts_to_datetime(v["changed"], fmt="short")}',
                       f'Faction: {factionO}']
                if war:
                    factionA = await get_faction_name(v["war"]["assaulting_faction"])
                    lst.append(f'Assault: {factionA} since {fmt.ts_to_datetime(v["war"]["started"], fmt="short")}')
                lst.append(f'```Territory: https://www.torn.com/city.php#terrName={k}')
                lst.append(f'Owner: https://www.torn.com/factions.php?step=profile&ID={v["faction"]}')
                if war:
                    lst.append(f'Assaulting: https://www.torn.com/factions.php?step=profile&ID={v["war"]["assaulting_faction"]}')
                mentions.append(lst)

        for k, v in rackets_p.items():
            if k not in req["rackets"]:
                lst = [f'**Racket vanished**',
                       f'```YAML',
                       f'Territory: {k}',
                       f'Name: {v["name"]}',
                       f'Reward: {v["reward"]}',
                       f'Level: {v["level"]}',
                       f'Created: {fmt.ts_to_datetime(v["created"], fmt="short")}',
                       f'Changed: {fmt.ts_to_datetime(v["changed"], fmt="short")}',
                       f'Faction: {v["faction"]}'
                       f'```']
                mentions.append(lst)

        for k, v in req["territory"].items():
            title = False
            war = v.get("war", False)
            racket = v.get("racket", False)
            if not (war and racket):
                continue

            # New racket
            if not territory_p[k].get("war", False):
                factionO = await get_faction_name(v["faction"])
                factionA = await get_faction_name(v["war"]["assaulting_faction"])
                title = f'New war for a {racket["name"]}'
                lst = [f'**{title}**',
                       f'```YAML',
                       f'Territory: {k}',
                       f'Name: {v["racket"]["name"]}',
                       f'Reward: {v["racket"]["reward"]}',
                       f'Level: {v["racket"]["level"]}',
                       f'Created: {fmt.ts_to_datetime(v["racket"]["created"], fmt="short")}',
                       f'Changed: {fmt.ts_to_datetime(v["racket"]["changed"], fmt="short")}',
                       f'Faction: {factionO}']
                lst.append(f'Assault: {factionA} since {fmt.ts_to_datetime(v["war"]["started"], fmt="short")}')
                lst.append(f'```Territory: https://www.torn.com/city.php#terrName={k}')
                lst.append(f'Owner: https://www.torn.com/factions.php?step=profile&ID={v["faction"]}')
                lst.append(f'Assaulting: https://www.torn.com/factions.php?step=profile&ID={v["war"]["assaulting_faction"]}')
                mentions.append(lst)

        if not len(mentions):
            return

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                # ignore servers with no verify
                if not self.bot.check_module(guild, "rackets"):
                    continue

                guild = self.bot.get_guild(guild.id)
                config = self.bot.get_config(guild)

                # get role
                role_name = config["rackets"].get("roles", [None])[0]
                role = get(guild.roles, name=role_name)
                # get channel
                channel_name = config["rackets"].get("channels")[0]
                channel = get(guild.channels, name=channel_name)

                if channel is not None:
                    mention = "" if role is None else f"{role.mention}"
                    for lst in mentions:
                        if role is not None:
                            lst[0] += f' {role.mention}'
                        await channel.send("\n".join(lst))

            except BaseException as e:
                print(f"[Racket] guild {guild}: retal failed {e}.")

        await push_rackets(int(req["timestamp"]), req)


    @racketsTask.before_loop
    async def before_racketsTask(self):
        print('[racket] waiting...')
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)

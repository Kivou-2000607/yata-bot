"""
Copyright 2020 kivou.2000607@gmail.com

This file is part of yata-bot.

    yata is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    yata is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with yata-bot. If not, see <https://www.gnu.org/licenses/>.
"""

# import standard modules
import asyncio
import aiohttp
import datetime
import json
import re
import logging

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks
from discord import Embed

# import bot functions and classes
import html

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

    # @tasks.loop(seconds=5)
    @tasks.loop(minutes=5)
    async def racketsTask(self):
        logging.info("[RACKETS] start task")

        # guild = self.bot.get_guild(650701692853288991)  # chappie
        guild = self.bot.get_guild(581227228537421825)  # yata
        _, _, key = await self.bot.get_master_key(guild)
        url = f'https://api.torn.com/torn/?selections=rackets,territory,timestamp&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                try:
                    req = await r.json()
                except BaseException as e:
                    logging.info(f"[RACKETS] error json: {e}")
                    req = {"error": e}

        if "error" in req:
            return

        logging.info(f'[RACKETS] {req["timestamp"]}')

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
                color = 550000

            elif v["level"] != rackets_p[k]["level"]:
                title = f'Racket moved {"up" if v["level"] > rackets_p[k]["level"] else "down"} from {rackets_p[k]["level"]} to {v["level"]}'
                color = 550000

            if title:
                factionO = await get_faction_name(v["faction"])
                embed = Embed(title=title, description=f'[{v["name"]} at {k}](https://www.torn.com/city.php#terrName={k})', color=color)

                embed.add_field(name='Reward', value=f'{v["reward"]}')
                embed.add_field(name='Territory', value=f'{k}')
                embed.add_field(name='Level', value=f'{v["level"]}')

                embed.add_field(name='Owner', value=f'[{html.unescape(factionO)}](https://www.torn.com/factions.php?step=profile&ID={v["faction"]})')
                if war:
                    warId = v["war"]["assaulting_faction"]
                    factionA = await get_faction_name(warId)
                    embed.add_field(name='Assaulting', value=f'[{html.unescape(factionA)}](https://www.torn.com/factions.php?step=profile&ID={warId})')

                embed.set_thumbnail(url=f'https://yata.alwaysdata.net/static/images/citymap/territories/50x50/{k}.png')
                # embed.set_footer(text=f'Created {fmt.ts_to_datetime(v["created"], fmt="short")} Changed {fmt.ts_to_datetime(v["changed"], fmt="short")}')
                embed.set_footer(text=f'{fmt.ts_to_datetime(v["changed"], fmt="short")}')
                mentions.append(embed)

        for k, v in rackets_p.items():
            if k not in req["rackets"]:
                color = 550000
                factionO = await get_faction_name(v["faction"])
                embed = Embed(title=f'Racket vanished', description=f'[{v["name"]} at {k}](https://www.torn.com/city.php#terrName={k})', color=color)
                embed.add_field(name='Reward', value=f'{v["reward"]}')
                embed.add_field(name='Territory', value=f'{k}')
                embed.add_field(name='Level', value=f'{v["level"]}')

                embed.add_field(name='Owner', value=f'[{html.unescape(factionO)}](https://www.torn.com/factions.php?step=profile&ID={v["faction"]})')

                embed.set_thumbnail(url=f'https://yata.alwaysdata.net/static/images/citymap/territories/50x50/{k}.png')
                # embed.set_footer(text=f'Created {fmt.ts_to_datetime(v["created"], fmt="short")} Changed {fmt.ts_to_datetime(v["changed"], fmt="short")}')
                embed.set_footer(text=f'{fmt.ts_to_datetime(v["changed"], fmt="short")}')
                mentions.append(embed)

        # req["territory"]["TVG"]["war"] = {"assaulting_faction": 44974, "defending_faction": 44974, "started": 1586510047, "ends": 1586769247}

        for k, v in req["territory"].items():
            title = False
            war = v.get("war", False)
            racket = v.get("racket", False)
            if not (war and racket):
                continue

            # New war
            if not territory_p[k].get("war", False):
                factionO = await get_faction_name(v["faction"])
                factionA = await get_faction_name(v["war"]["assaulting_faction"])
                color = 550000
                title = f'New war for a {racket["name"]}'
                embed = Embed(title=title, description=f'[{racket["name"]} at {k}](https://www.torn.com/city.php#terrName={k})', color=color)

                embed.add_field(name='Reward', value=f'{racket["reward"]}')
                embed.add_field(name='Territory', value=f'{k}')
                embed.add_field(name='Level', value=f'{racket["level"]}')

                embed.add_field(name='Owner', value=f'[{html.unescape(factionO)}](https://www.torn.com/factions.php?step=profile&ID={v["faction"]})')
                warId = v["war"]["assaulting_faction"]
                embed.add_field(name='Assaulting', value=f'[{html.unescape(factionA)}](https://www.torn.com/factions.php?step=profile&ID={warId})')

                embed.set_thumbnail(url=f'https://yata.alwaysdata.net/static/images/citymap/territories/50x50/{k}.png')
                # embed.set_footer(text=f'Created {fmt.ts_to_datetime(v["created"], fmt="short")} Changed {fmt.ts_to_datetime(v["changed"], fmt="short")}')
                embed.set_footer(text=f'{fmt.ts_to_datetime(racket["changed"], fmt="short")}')
                mentions.append(embed)

        logging.info(f'[RACKETS] mentions: {len(mentions)}')

        logging.info(f"[RACKETS] push rackets")
        await push_rackets(int(req["timestamp"]), req)

        if not len(mentions):
            return

        # iteration over all guilds
        for guild in self.bot.get_guild_module("rackets"):
            try:
                logging.info(f"[RACKETS] guild {guild}: {datetime.datetime.now()}")
                # ignore servers with no rackets
                # if not self.bot.check_module(guild, "rackets"):
                #     continue
                #
                # guild = self.bot.get_guild(guild.id)
                config = self.bot.get_config(guild)

                # get role
                role_names = config["rackets"].get("roles", False)
                role = get(guild.roles, name=role_names[0]) if role_names and len(role_names) else None

                # get channel
                channel_name = config["rackets"].get("channels")[0]
                channel = get(guild.channels, name=channel_name)

                if channel is not None:
                    for m in mentions:
                        msg = await channel.send('' if role is None else f'{role.mention}', embed=m)

            except BaseException as e:
                logging.error(f'[racketTask] {guild} [{guild.id}]: {e}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on racket notifications"}
                await self.bot.send_log_main(e, headers=headers)

    @racketsTask.before_loop
    async def before_racketsTask(self):
        logging.info('[racket] waiting...')
        await self.bot.wait_until_ready()

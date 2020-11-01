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
import html

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks
from discord import Embed

# import bot functions and classes
from inc.yata_db import get_data
from inc.yata_db import push_data
from inc.yata_db import get_faction_name
from inc.handy import *


class Racket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.racketsTask.start()

    def cog_unload(self):
        self.racketsTask.cancel()

    @tasks.loop(minutes=5)
    async def racketsTask(self):
        logging.debug("[racket/notifications] start task")

        guild = self.bot.get_guild(self.bot.main_server_id)
        _, _, key = await self.bot.get_master_key(guild)

        if key is None:
            logging.error(f"[racket/notifications] Error no key found for on main server id {self.bot.main_server_id}")
            return

        response, e = await self.bot.api_call("torn", "", ["rackets", "territory", "timestamp"], key)
        if e:
            logging.error(f"[racket/notifications] Error {e}")
            return

        _, randt_p = get_data(self.bot.bot_id, "rackets")        
        rackets_p = randt_p["rackets"] if "rackets" in randt_p else {}
        territory_p = randt_p["territory"] if "territory" in randt_p else {}

        mentions = []
        for k, v in response["rackets"].items():
            title = False
            war = v.get("war", False)
            # New racket
            if k not in rackets_p:
                title = "New racket"

            elif v["level"] != rackets_p[k]["level"]:
                title = f'Racket moved {"up" if v["level"] > rackets_p[k]["level"] else "down"} from {rackets_p[k]["level"]} to {v["level"]}'

            if title:
                factionO = await get_faction_name(v["faction"])
                embed = Embed(title=title, description=f'[{v["name"]} at {k}](https://www.torn.com/city.php#terrName={k})', color=my_blue)

                embed.add_field(name='Reward', value=f'{v["reward"]}')
                embed.add_field(name='Territory', value=f'{k}')
                embed.add_field(name='Level', value=f'{v["level"]}')

                embed.add_field(name='Owner', value=f'[{html.unescape(factionO)}](https://www.torn.com/factions.php?step=profile&ID={v["faction"]})')
                if war:
                    warId = v["war"]["assaulting_faction"]
                    factionA = await get_faction_name(warId)
                    embed.add_field(name='Assaulting', value=f'[{html.unescape(factionA)}](https://www.torn.com/factions.php?step=profile&ID={warId})')

                embed.set_thumbnail(url=f'https://yata.alwaysdata.net/media/images/citymap/territories/50x50/{k}.png')
                # embed.set_footer(text=f'Created {ts_to_datetime(v["created"], fmt="short")} Changed {ts_to_datetime(v["changed"], fmt="short")}')
                embed.set_footer(text=f'{ts_to_datetime(v["changed"], fmt="short")}')
                mentions.append(embed)

        for k, v in rackets_p.items():
            if k not in response["rackets"]:
                factionO = await get_faction_name(v["faction"])
                embed = Embed(title=f'Racket vanished', description=f'[{v["name"]} at {k}](https://www.torn.com/city.php#terrName={k})', color=my_blue)
                embed.add_field(name='Reward', value=f'{v["reward"]}')
                embed.add_field(name='Territory', value=f'{k}')
                embed.add_field(name='Level', value=f'{v["level"]}')

                embed.add_field(name='Owner', value=f'[{html.unescape(factionO)}](https://www.torn.com/factions.php?step=profile&ID={v["faction"]})')

                embed.set_thumbnail(url=f'https://yata.alwaysdata.net/media/images/citymap/territories/50x50/{k}.png')
                # embed.set_footer(text=f'Created {ts_to_datetime(v["created"], fmt="short")} Changed {ts_to_datetime(v["changed"], fmt="short")}')
                embed.set_footer(text=f'{ts_to_datetime(v["changed"], fmt="short")}')
                mentions.append(embed)

        # response["territory"]["TVG"]["war"] = {"assaulting_faction": 44974, "defending_faction": 44974, "started": 1586510047, "ends": 1586769247}

        for k, v in response["territory"].items():
            title = False
            war = v.get("war", False)
            racket = v.get("racket", False)
            if not (war and racket):
                continue

            # New war
            if not territory_p[k].get("war", False):
                factionO = await get_faction_name(v["faction"])
                factionA = await get_faction_name(v["war"]["assaulting_faction"])
                title = f'New war for a {racket["name"]}'
                embed = Embed(title=title, description=f'[{racket["name"]} at {k}](https://www.torn.com/city.php#terrName={k})', color=my_blue)

                embed.add_field(name='Reward', value=f'{racket["reward"]}')
                embed.add_field(name='Territory', value=f'{k}')
                embed.add_field(name='Level', value=f'{racket["level"]}')

                embed.add_field(name='Owner', value=f'[{html.unescape(factionO)}](https://www.torn.com/factions.php?step=profile&ID={v["faction"]})')
                warId = v["war"]["assaulting_faction"]
                embed.add_field(name='Assaulting', value=f'[{html.unescape(factionA)}](https://www.torn.com/factions.php?step=profile&ID={warId})')

                embed.set_thumbnail(url=f'https://yata.alwaysdata.net/media/images/citymap/territories/50x50/{k}.png')
                # embed.set_footer(text=f'Created {ts_to_datetime(v["created"], fmt="short")} Changed {ts_to_datetime(v["changed"], fmt="short")}')
                embed.set_footer(text=f'{ts_to_datetime(racket["changed"], fmt="short")}')
                mentions.append(embed)

        logging.debug(f'[racket/notifications] mentions: {len(mentions)}')

        logging.debug(f"[racket/notifications] push rackets")
        await push_data(self.bot.bot_id, int(response["timestamp"]), response, "rackets")

        # DEBUG
        # embed = Embed(title="Test Racket")
        # mentions.append(embed)

        if not len(mentions):
            logging.debug(f"[racket/notifications] no notifications")
            return

        # iteration over all guilds
        for guild in self.bot.get_guilds_by_module("rackets"):
            try:
                logging.debug(f"[racket/notifications] {guild}")

                config = self.bot.get_guild_configuration_by_module(guild, "rackets", check_key="channels_alerts")
                if not config:
                    logging.info(f"[racket/notifications] No rackets channels for guild {guild}")
                    continue

                # get role & channel
                role = self.bot.get_module_role(guild.roles, config.get("roles_alerts", {}))
                channel = self.bot.get_module_channel(guild.channels, config.get("channels_alerts", {}))

                if channel is None:
                    continue

                for m in mentions:
                    msg = await channel.send('' if role is None else f'Rackets update {role.mention}', embed=m)

            except BaseException as e:
                logging.error(f'[racket/notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(f'Error during a racket alert: {e}', guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on racket notifications"}
                await self.bot.send_log_main(e, headers=headers, full=True)

    @racketsTask.before_loop
    async def before_racketsTask(self):
        await self.bot.wait_until_ready()

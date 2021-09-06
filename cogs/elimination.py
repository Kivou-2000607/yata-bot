"""
Copyright 2021 kivou@yata.yt

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
from inc.handy import *


class Elimination(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.score.start()
        self.wave.start()
        self.scores_embed = None

    def cog_unload(self):
        self.wave.cancel()
        self.score.cancel()

    @tasks.loop(seconds=60)
    async def score(self):

        async def _update_score(guild):
            if guild is None:
                logging.info(f"[elimination score] guild {guild}: None")
                return

            # get configuration
            config = self.bot.get_guild_configuration_by_module(guild, "elim", check_key="channels_scores")
            if not config:
                logging.info(f"[elimination score] guild {guild}: score not enabled")
                return

            # get channel
            for k, v in config["channels_scores"].items():  # only the first one
                channel = get(guild.channels, id=int(k))
                if channel is None:
                    logging.info(f"[elimination score] guild {guild}: channel {v} [{k}]")
                    return
                break

            try:
                msg = await channel.fetch_message(channel.last_message_id)
                await msg.edit(embed=self.scores_embed)
                logging.info(f"[elimination score] guild {guild}: edit message")
                return

            except BaseException as e:
                await channel.send(embed=self.scores_embed)
                logging.info(f"[elimination score] guild {guild}: send message")
                return

        # sleep to the minute
        sleep = 60 - ts_now() % 60 + 5
        logging.info(f'[elimination score] sleep for {sleep}s')
        await asyncio.sleep(sleep)

        # update scores
        guild = self.bot.get_guild(self.bot.main_server_id)
        _, _, key = await self.bot.get_master_key(guild)

        r, e = await self.bot.api_call("torn", "", ["competition", "timestamp"], key)
        if e:
            logging.error(f"[elimination score] Error {e}")
            return

        # create message content
        self.scores_embed = Embed(title="Elimination scores", color=550000)
        for team in r["competition"]["teams"]:
            values = [f'[Participants: {team["participants"]}](https://www.torn.com/competition.php#/p=team&team={team["team"]})',
                      f'Score: {team["score"]}',
                      f'Lives: **{team["lives"]}**']
            self.scores_embed.add_field(name=f'#{team["position"]} {team["name"]}', value='\n'.join(values))
            self.scores_embed.set_footer(text=f'Last update: {ts_format(ts_now(), fmt="time")}')

        # get score guild
        guilds = self.bot.get_guilds_by_module("elim")
        await asyncio.gather(*map(_update_score, guilds))

    @tasks.loop(seconds=10)
    async def wave(self):
        logging.info("prout")
        async def _update_wave(guild):
            if guild is None:
                logging.info(f"[elimination wave] guild {guild}: None")
                return

            # get configuration
            config = self.bot.get_guild_configuration_by_module(guild, "elim", check_key="channels_scores")
            if not config:
                logging.info(f"[elimination wave] guild {guild}: score not enabled")
                return

            # get channel
            for k, v in config["channels_scores"].items():  # only the first one
                channel = get(guild.channels, id=int(k))
                if channel is None:
                    logging.info(f"[elimination wave] guild {guild}: channel {v} [{k}]")
                    return
                break

            m = 14 - datetime.datetime.now().time().minute % 15
            s = 59 - datetime.datetime.now().time().second
            content = f"Next wave in **{m}:{s:02d}** seconds"

            try:
                msg = await channel.fetch_message(channel.last_message_id)
                await msg.edit(content=content)
                logging.info(f"[elimination wave] guild {guild}: edit message")
                return

            except BaseException as e:
                await channel.send(content=content)
                logging.info(f"[elimination wave] guild {guild}: send message")
                return

        # sleep to 10 seconds
        sleep = 9 - ts_now() % 10
        logging.info(f'[elimination score] sleep for {sleep}s')
        await asyncio.sleep(sleep)

        # get score guild
        guilds = self.bot.get_guilds_by_module("elim")
        await asyncio.gather(*map(_update_wave, guilds))

    @score.before_loop
    async def before_score(self):
        await self.bot.wait_until_ready()

    @wave.before_loop
    async def before_wave(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)

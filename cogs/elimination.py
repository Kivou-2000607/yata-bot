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
import json
import datetime
import re
import logging
# import termplotlib as tpl

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get
from discord import Embed

# import bot functions and classes
from inc.yata_db import get_data
from inc.yata_db import push_data
from inc.handy import *


class Elimination(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.score.start()

    def cog_unload(self):
        self.score.cancel()

    @tasks.loop(seconds=30)
    async def score(self):
        # get main guild
        guild = get(self.bot.guilds, id=self.bot.main_server_id)
        channel = get(guild.channels, name="elimination")
        _, _, key = await self.bot.get_master_key(guild)
        url = f'https://api.torn.com/torn/?selections=competition&key={key}'
        print(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        if not isinstance(req, dict):
            return
        if not "competition" in req:
            return

        eb = Embed(title="Elimination scores", color=550000)
        for team in req["competition"]["teams"]:
            print(team)
            values = [f'[Participants: {team["participants"]}](https://www.torn.com/competition.php#/p=team&team={team["team"]})',
                      f'Score: {team["score"]}',
                      f'Lives: **{team["lives"]}**']
            eb.add_field(name=f'#{team["position"]} {team["name"]}', value='\n'.join(values))

        try:
            msg = await channel.fetch_message(channel.last_message_id)
        except BaseException as e:
            await channel.send(embed=eb)
            return

        await msg.edit(content="", embed=eb)



    @score.before_loop
    async def before_score(self):
        print("coucou")
        await self.bot.wait_until_ready()

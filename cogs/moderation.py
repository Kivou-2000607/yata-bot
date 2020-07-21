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
import re
import json
import aiohttp
import traceback
import sys
import logging
import html
import asyncio
import datetime

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get
from discord.utils import oauth_url
from discord import Embed
from discord.ext import tasks

# import bot functions and classes
from inc.yata_db import get_yata_user

from inc.handy import *


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = self.bot.bot_id

    @commands.Cog.listener()
    async def on_message(self, message):

        # in #yata-bot-setup
        if message.channel.id in [703587583862505483]:
            splt = message.content.split(" ")
            if "<@&679669933680230430>" in splt:
                lst = [f"Hello {message.author.mention}, if you asked for a bot setup you're in the good place (otherwise checkout <#623906124428476427>).",
                       f"Wait just a moment for an @Helper to help you out. In the meantime",
                       f"- check that you gave us the server name",
                       f"- do an initial `!sync` on you server",
                       f"- read the documentation on the website if that doesn't make any sense to you"]
                await message.channel.send("\n".join(lst))

        # if needs to process other commands
        # await self.bot.process_commands(message)

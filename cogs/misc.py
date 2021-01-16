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
import xkcd
import asyncio
import aiohttp
import random
import logging

# import discord modules
from discord.ext import commands
from discord import Embed

# import bot functions and classes
from inc.handy import *


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def xkcd(self, ctx, *args):
        """gives random xkcd comic"""
        if len(args) and args[0].isdigit():
            comic = xkcd.Comic(args[0])
            id = args[0]
        else:
            comic = xkcd.getRandomComic()
            id = comic.getExplanation().split("/")[-1]

        eb = Embed(description=f'[{comic.getTitle()} #{id}]({comic.getExplanation()})', color=my_blue)
        eb.set_image(url=comic.getImageLink())
        eb.set_footer(text=comic.getAltText())
        await ctx.send(embed=eb)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def crimes2(self, ctx):
        """gives latest update on crimes 2.0"""
        await ctx.send("https://yata.yt/media/misc/crimes2.gif")

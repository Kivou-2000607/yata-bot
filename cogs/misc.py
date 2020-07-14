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
        await ctx.send(f"xkcd #{id} **{comic.getTitle()}** {comic.getImageLink()}")
        await asyncio.sleep(15)
        await ctx.send(f"*{comic.getAltText()}*")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def whatif(self, ctx, *args):
        """gives random xkcd comic"""
        if len(args) and args[0].isdigit():
            comic = xkcd.getWhatIf(args[0])
        else:
            comic = xkcd.getRandomWhatIf()
        await ctx.send(f"WhatIf #{comic.getNumber()} **{comic.getTitle()}** {comic.getLink()}")
        # await asyncio.sleep(15)
        # await ctx.send(f"*{comic.getAltText()}*")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, read_message_history=True)
    @commands.guild_only()
    async def explain(self, ctx, *args):
        """explain random xkcd comic"""
        if len(args) and args[0].isdigit():
            comic = xkcd.Comic(args[0])
            await ctx.send(f"Explanations for xkcd #{args[0]} **{comic.getTitle()}**: {comic.getExplanation()}")
            return
        else:
            async for m in ctx.channel.history(limit=50):
                if m.author.bot and m.content[:6] == "xkcd #":
                    id = m.content.split("#")[-1].split(" ")[0]
                    if id.isdigit():
                        comic = xkcd.Comic(id)
                        await ctx.send(f"Explanations for xkcd #{id} **{comic.getTitle()}**: {comic.getExplanation()}")
                        return
        await ctx.send("No xkcd found in this channel recent history")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def crimes2(self, ctx):
        """gives latest update on crimes 2.0"""
        await ctx.send("https://yata.alwaysdata.net/static/images/crimes2.gif")

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

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.formating as fmt
from includes.torn_pages import  pages


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def xkcd(self, ctx):
        """gives random xkcd comic"""
        comic = xkcd.getRandomComic()
        await ctx.send(f"**{comic.getTitle()}** {comic.getImageLink()}")
        await asyncio.sleep(15)
        await ctx.send(f"*{comic.getAltText()}*")

    @commands.command()
    async def crimes2(self, ctx):
        """gives latest update on crimes 2.0"""
        await ctx.send("https://yata.alwaysdata.net/static/images/crimes2.gif")

    @commands.command()
    async def banners(self, ctx, *args):
        """Gives missing honor banners or displays banner if id given"""

        # get yata's honor dict
        url = "https://yata.alwaysdata.net/awards/bannersId"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                honorBanners = await r.json()

        # display honor banners
        if len(args):
            for id in args:
                bannerId = honorBanners.get(id)
                if bannerId is None:
                    await ctx.send("Honor **#{}**: *honor not known*".format(id))
                elif int(bannerId) == 0:
                    await ctx.send("Honor **#{}**: *banner not known*".format(id))
                else:
                    await ctx.send("Honor **#{}**: https://awardimages.torn.com/{}.png".format(id, bannerId))

        # display missing banners
        else:
            # get configuration for guild
            status, tornId, key = await self.bot.get_master_key(ctx.guild)
            if status == -1:
                await ctx.send(":x: No master key given")
                return

            # get torn's honor dict
            url = "https://api.torn.com/torn/?selections=honors&key={}".format(key)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    tornHonors = await r.json()

            # handle API error
            if 'error' in tornHonors:
                await ctx.send(f':x: Master key problem: *{tornHonors["error"]["error"]}*')
                return

            # dirtiest way to deal with API error
            tornHonors = tornHonors.get('honors', dict({}))

            # select missing honors
            honors = []
            for k, v in honorBanners.items():
                if int(v) == 0:
                    honor = tornHonors.get(k, dict({}))
                    h = " #{} **{}** *{}*".format(k, honor.get('name', 'API'), honor.get('description', 'ERROR'))
                    honors.append(h)

            message = "Missing banners:\n{}".format("\n".join(honors))

            await ctx.send(message)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Welcome message"""

        # check if bot
        if member.bot:
            return

        # get system channel and send message
        welcome_channel = member.guild.system_channel

        # get config
        c = self.bot.get_config(member.guild)

        if welcome_channel is None or not c["admin"].get("welcome", False):
            pass
        else:
            lst = [f"Welcome {member.mention}."]
            msg = []
            for w in c["admin"]["welcome"].split(" "):
                if w[0] == "#":
                    ch = get(member.guild.channels, name=w[1:])
                    if ch is not None:
                        msg.append(f'{ch.mention}')
                    else:
                        msg.append(f'`{w}`')
                elif w[0] == "@":
                    ro = get(member.guild.roles, name=w[1:])
                    if ro is not None:
                        msg.append(f'{ro.mention}')
                    else:
                        msg.append(f'`{w}`')
                else:
                    msg.append(w)

            lst.append(" ".join(msg))
            await fmt.send_tt(welcome_channel, lst, tt=False)

    @commands.command()
    async def egg(self, ctx):
        p = random.choice(pages)
        lst = [f'You want to find an egg? Try here:',
               f'**{p.get("title", "here")}** https://www.torn.com{p.get("url", "")}']
        await ctx.send("\n".join(lst))

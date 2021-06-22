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
from discord.utils import get

# import bot functions and classes
from inc.handy import *


class JFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def stalk(self, ctx):
        """gives/removes the retal role for jfk and jfk 2.1"""
        # debug values
        # channel_id_main = 650701692853288997
        # channel_id_sub = 792138823853146133
        # role_id_main = 826557408989151293
        # role_id_sub = 789249556423770132

        # jfk values
        channel_id_main = 356171252706181140
        channel_id_sub = 356143232435879937
        role_id_main = 841431434572857354
        role_id_sub = 841431662318452786

        if ctx.channel.id == channel_id_main:
            guild = get(self.bot.guilds, id=ctx.guild.id)
            channel = get(guild.channels, id=channel_id_main)
            role = get(guild.roles, id=role_id_main)

        elif ctx.channel.id == channel_id_sub:
            guild = get(self.bot.guilds, id=ctx.guild.id)
            channel = get(guild.channels, id=channel_id_sub)
            role = get(guild.roles, id=role_id_sub)

        else:
            return


        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f'```role @{role.name} removed to {ctx.author.display_name}```')
        else:
            await ctx.author.add_roles(role)
            msg = await ctx.send(f'```role @{role.name} added to {ctx.author.display_name}```')

        # await asyncio.sleep(5)
        # await msg.delete()
        # await ctx.message.delete()

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def invest(self, ctx):
        """gives/removes the stocks role for jfk and jfk 2.1"""
        # debug values
        # channel_id_main = 650701692853288997
        # channel_id_sub = 792138823853146133
        # role_id_main = 826557408989151293
        # role_id_sub = 789249556423770132

        # jfk values
        channel_id_main = 856913052201254952
        role_id_main = 856913807631843329

        if ctx.channel.id == channel_id_main:
            guild = get(self.bot.guilds, id=ctx.guild.id)
            channel = get(guild.channels, id=channel_id_main)
            role = get(guild.roles, id=role_id_main)

        else:
            return


        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f'```role @{role.name} removed to {ctx.author.display_name}```')
        else:
            await ctx.author.add_roles(role)
            msg = await ctx.send(f'```role @{role.name} added to {ctx.author.display_name}```')

        # await asyncio.sleep(5)
        # await msg.delete()
        # await ctx.message.delete()


    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def notify(self, ctx):
        """gives/removes the chain role for jfk and jfk 2.1"""
        # debug values
        # channel_id_main = 650701692853288997
        # channel_id_sub = 792138823853146133
        # role_id_main = 826557408989151293
        # role_id_sub = 789249556423770132

        # jfk values
        channel_id_main = 356171252706181140
        channel_id_sub = 356143232435879937
        role_id_main = 629005125234589707
        role_id_sub = 629005185880162355

        if ctx.channel.id == channel_id_main:
            guild = get(self.bot.guilds, id=ctx.guild.id)
            channel = get(guild.channels, id=channel_id_main)
            role = get(guild.roles, id=role_id_main)

        elif ctx.channel.id == channel_id_sub:
            guild = get(self.bot.guilds, id=ctx.guild.id)
            channel = get(guild.channels, id=channel_id_sub)
            role = get(guild.roles, id=role_id_sub)

        else:
            return


        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f'```role @{role.name} removed to {ctx.author.display_name}```')
        else:
            await ctx.author.add_roles(role)
            msg = await ctx.send(f'```role @{role.name} added to {ctx.author.display_name}```')

        # await asyncio.sleep(5)
        # await msg.delete()
        # await ctx.message.delete()

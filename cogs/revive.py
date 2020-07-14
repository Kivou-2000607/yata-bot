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
# import datetime
# import json
import logging

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
from inc.handy import *


class Revive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["r", "R"])
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.guild_only()
    async def revive(self, ctx, *args):
        """ send revive message to @Reviver
        """
        logging.info(f'[revive/revive] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "revive")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        # Get user key
        lst = []
        errors = []
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        # return 0, id, Name, Key: All good
        # return -1, None, None, None: no master key given
        # return -2, None, None, None: master key api error
        # return -3, master_id, None, master_key: user not verified
        # return -4, id, None, master_key: did not find torn id in yata db

        sendFrom = f'Sent from {ctx.guild}'

        # in this case it's not possible to link discordID with torn player
        # -> backup is to have the id as an argument
        # note: if status == -3 it converts master_id to actual tornId
        if status in [-1, -2, -3]:
            if len(args) and args[0].isdigit():
                sendFrom += f' on behalf of {ctx.author.display_name}'
                tornId = int(args[0])
                name = "Player"
            else:
                msg = await ctx.send(":x: Impossible to send revive call because you're not verified on the official Torn discord server.\nYou can use `!revive <tornId>`.")
                await asyncio.sleep(30)
                await msg.delete()
                return

        else:
            if len(args) and args[0].isdigit():
                sendFrom += f' on behalf of {ctx.author.display_name}'
                tornId = int(args[0])
            else:
                tornId = id

        if key is not None:
            # api call to get potential status and faction
            url = f'https://api.torn.com/user/{tornId}?key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # handle API error
            if 'error' in req:
                if status in [0]:
                    errors.append(f':x: Problem using {name} [{id}]\'s key: *{req["error"]["error"]}*')
                elif status in [-3, -4]:
                    errors.append(f':x: Problem using server admin key: *{req["error"]["error"]}*')
                else:
                    errors.append(f':x: Problem with API key (status = {status}): *{req["error"]["error"]}*')
                errors.append(":x: I cannot specify faction or hospitalization time")

        # create call message
        name = req.get("name", "Player")
        url = f'https://www.torn.com/profiles.php?XID={tornId}'
        if req.get('faction', False) and req["faction"]["faction_id"]:
            lst.append(f'**{name} [{tornId}]** from **{req["faction"]["faction_name"]} [{req["faction"]["faction_id"]}]** needs a revive {url}')
        else:
            lst.append(f'**{name} [{tornId}]** needs a revive {url}')

        # add status
        if req.get('status', False) and req["status"]["state"] == "Hospital":
            lst.append(f'{req["status"]["description"]} ({cleanhtml(req["status"]["details"])})')

        # list of messages to delete them after
        msgList = []
        # send message to current channel
        if len(errors):
            msg = "\n".join(errors)
            m = await ctx.send(f'{msg}')
            msgList.append([m, ctx.channel])
        msg = "\n".join(lst)
        role = self.bot.get_module_role(ctx.guild.roles, config.get("roles_alerts", {}))
        mention = '' if role is None else f'{role.mention} '
        m = await ctx.send(f'{mention}{msg}')
        msgList.append([m, ctx.channel])

        # loop over all server to send the calls
        for id in config.get("sending", []):
            try:
                # get remote server coonfig
                remote_guild = get(self.bot.guilds, id=int(id))
                logging.debug(f'[revive/revive] Sending call: {ctx.guild} -> {remote_guild}')
                remote_config = self.bot.get_guild_configuration_by_module(remote_guild, "revive")

                if str(ctx.guild.id) in remote_config.get("blacklist", {}):
                    m = await ctx.send(f'*Server {remote_guild.name} has blacklisted you*')
                    msgList.append([m, ctx.channel])
                else:
                    # get guild, role and channel
                    remote_role = self.bot.get_module_role(remote_guild.roles, remote_config.get("roles_alerts", {}))
                    remote_channel = self.bot.get_module_channel(remote_guild.channels, remote_config.get("channels_alerts", {}))
                    mention = '' if remote_role is None else f'{remote_role.mention} '
                    if remote_channel is not None:
                        m = await remote_channel.send('{}{}\n*{}*'.format(mention, msg, sendFrom))
                        msgList.append([m, remote_channel])
                    else:
                        await self.bot.send_log(f'Error sending revive call to server {remote_guild}: revive channel not found', guild_id=ctx.guild.id)

            except BaseException as e:
                await self.bot.send_log(f'Error sending revive call to server {remote_guild}: {e}', guild_id=ctx.guild.id)

        # wait for 1 minute
        await asyncio.sleep(50)
        for [msg, cha] in msgList:
            try:
                await msg.delete()
            except BaseException:
                await cha.send(":x: There is no need to delete the calls. They are automatically deleted after 5 minutes. *You can delete this message thought* ^^")

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
import includes.checks as checks
import includes.formating as fmt
from includes.yata_db import load_configurations
from includes.yata_db import push_configurations


class Revive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["r", "R"])
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.guild_only()
    async def revive(self, ctx, *args):
        """ send revive message to @Reviver
        """
        logging.info(f'[revive/revive] {ctx.guild}: {ctx.member.nick} / {ctx.member}')

        # return if revive not active
        if not self.bot.check_module(ctx.guild, "revive"):
            await ctx.send(":x: Revive module not activated")
            return

        # check role and channel
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "revive")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
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
        # return -5, id, Name, master_key: member did not give perm

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

        if key is None:
            # should be for case -1, -2
            req = dict({"name": "Player"})

        else:
            # api call to get potential status and faction
            url = f'https://api.torn.com/user/{tornId}?key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # handle API error
            if 'error' in req:
                if status in [0]:
                    errors.append(f':x: Problem with {name} [{id}]\'s key: *{req["error"]["error"]}*')
                elif status in [-3, -4]:
                    errors.append(f':x: Problem with server master key: *{req["error"]["error"]}*')
                else:
                    errors.append(f':x: Problem with API key (status = {status}): *{req["error"]["error"]}*')
                errors.append(":x: I cannot specify faction or hospitalization time")

        # get reviver role
        role = get(ctx.guild.roles, name="Reviver")
        name = req["name"]
        url = f'https://www.torn.com/profiles.php?XID={tornId}'
        if req.get('faction', False) and req["faction"]["faction_id"]:
            lst.append(f'**{name} [{tornId}]** from **{req["faction"]["faction_name"]} [{req["faction"]["faction_id"]}]** needs a revive {url}')
        else:
            lst.append(f'**{name} [{tornId}]** needs a revive {url}')

        # add status
        if req.get('status', False) and req["status"]["state"] == "Hospital":
            lst.append(f'{req["status"]["description"]} ({fmt.cleanhtml(req["status"]["details"])})')

        # list of messages to delete them after
        msgList = []
        # send message to current channel
        if len(errors):
            msg = "\n".join(errors)
            m = await ctx.send(f'{msg}')
            msgList.append([m, ctx.channel])
        msg = "\n".join(lst)
        m = await ctx.send(f'{role.mention} {msg}')
        msgList.append([m, ctx.channel])

        for id in self.bot.configs[str(ctx.guild.id)]["revive"].get("servers", []):
            try:
                if ctx.guild.id in self.bot.configs[str(id)]["revive"].get("blacklist", []):
                    m = await ctx.send(f'Server {ctx.guild.name} has blacklisted you')
                    msgList.append([m, ctx.channel])
                else:
                    # get guild, role and channel
                    guild = self.bot.get_guild(id)
                    role = get(guild.roles, name="Reviver")
                    localConf = self.bot.get_config(guild)
                    for channelName in self.bot.get_allowed_channels(localConf, "revive"):
                        channel = get(guild.channels, name=channelName)
                        m = await channel.send('{} {}\n*{}*'.format(role.mention, msg, sendFrom))
                        msgList.append([m, channel])
                    # await ctx.send(f'Sent to {id}')
            except BaseException as e:
                await ctx.send(f":x: Error with guild {id}: {e}")

        # wait for 1 minute
        await asyncio.sleep(50)
        # await asyncio.sleep(5)
        for [msg, cha] in msgList:
            try:
                await msg.delete()
            except BaseException:
                await cha.send(":x: There is no need to delete the calls. They are automatically deleted after 5 minutes. *You can delete this message thought* ^^")

    @commands.command(aliases=["rs"])
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def reviveServers(self, ctx, *args):
        logging.info(f'[revive/reviveServers] {ctx.guild}: {ctx.member.nick} / {ctx.member}')

        # return if revive not active
        if not self.bot.check_module(ctx.guild, "revive"):
            await ctx.send(":x: Revive module not activated")
            return

        # check role and channel
        ALLOWED_CHANNELS = ["yata-admin"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # load configuration
        configs = self.bot.configs

        # dictionnary of all servers with revive enables
        servers = {k: [v["admin"], v["revive"].get("servers", []), v["revive"].get("blacklist", [])] for k, v in configs.items() if v.get("revive", dict({})).get("active", False) and int(k) != ctx.guild.id}

        # update configuration
        if len(args) and args[0].replace("-", "").isdigit() and args[0].replace("-", "") in servers:
            serverId = int(args[0])
            if serverId > 0:
                servTmp = configs[str(ctx.guild.id)]["revive"].get('servers', [])
                # toogle server id
                if serverId in servTmp:
                    servTmp.remove(serverId)
                else:
                    servTmp.append(serverId)
                configs[str(ctx.guild.id)]["revive"]['servers'] = servTmp

            else:
                serverId = -serverId
                servTmp = configs[str(ctx.guild.id)]["revive"].get('blacklist', [])
                # toogle server id
                if serverId in servTmp:
                    servTmp.remove(serverId)
                else:
                    servTmp.append(serverId)
                configs[str(ctx.guild.id)]["revive"]['blacklist'] = servTmp

            self.bot.configs = configs
            await push_configurations(self.bot.bot_id, configs)

        myServers = configs[str(ctx.guild.id)]["revive"].get("servers", [])  # id of all servers I want to send message
        myBlackList = configs[str(ctx.guild.id)]["revive"].get("blacklist", [])  # id of all servers I want to send message

        if len(servers):
            lst = ["List of servers with the *revive module* activated\n"]
            for k, [s, r, b] in servers.items():
                lst.append(f'**{s["name"]}** server (contact **{s["contact"]} [{s["contact_id"]}]**)')
                if int(k) in myServers:
                    lst.append('\tSending: **on**')
                else:
                    lst.append('\tSending: **off**')
                if ctx.guild.id in r:
                    lst.append('\tReceiving: **on**')
                else:
                    lst.append('\tReceiving: **off**')
                if int(k) in myBlackList:
                    lst.append('\tThis server is on your blacklist')
                if ctx.guild.id in b:
                    lst.append('\tThis server have you on their blacklist')

                lst.append('\tType `!reviveServers {}` to start or stop sending this server your revive calls'.format(k))
                lst.append('\tType `!reviveServers -{}` to add or remove this server from your blacklist\n'.format(k))

        else:
            await ctx.send(":x: No other servers have activated their revive option")
            return

        await fmt.send_tt(ctx, lst, tt=False)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.guild_only()
    async def reviver(self, ctx):
        """Add/remove @Reviver role"""
        logging.info(f'[revive/reviver] {ctx.guild}: {ctx.member.nick} / {ctx.member}')

        # return if revive not active
        if not self.bot.check_module(ctx.guild, "revive"):
            await ctx.send(":x: Revive module not activated")
            return

        # Get Reviver role
        role = get(ctx.guild.roles, name="Reviver")

        if role in ctx.author.roles:
            # remove Reviver
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **stop** receiving notifications for revives.")
        else:
            # assign Reviver
            await ctx.author.add_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **start** receiving notifications for revives.")

        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()

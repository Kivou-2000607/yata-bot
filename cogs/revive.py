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
import html

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord import Embed

# import bot functions and classes
from inc.handy import *
from inc.yata_db import set_configuration


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
                msg = await self.bot.send_error_message(ctx.channel, "Impossible to send revive call because you're not verified on the official Torn discord server.\nYou can use `!revive <tornId>`.")
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
            response, e = await self.bot.api_call("user", tornId, ["profile", "timestamp"], key)
            if e and "error" in response:
                if status in [0]:
                    errors.append(f'Problem using {name} [{id}]\'s key: *{response["error"]["error"]}*')
                elif status in [-3, -4]:
                    errors.append(f'Problem using server admin key: *{response["error"]["error"]}*')
                else:
                    errors.append(f'Problem with API key (status = {status}): *{response["error"]["error"]}*')
                errors.append("I cannot specify faction or hospitalization time")
        else:
            return

        # create call message
        name = response.get("name", "Player")
        url = f'https://www.torn.com/profiles.php?XID={tornId}'
        lst = []
        if response.get('faction', False) and response["faction"]["faction_id"]:
            f = response["faction"]
            lst.append(f'[{name} [{tornId}]](https://www.torn.com/profiles.php?XID={tornId}) from [{html.unescape(f["faction_name"])} [{f["faction_id"]}]](https://www.torn.com/factions.php?&step=profile&ID={f["faction_id"]}) needs a revive.')
        else:
            lst.append(f'[{name} [{tornId}]](https://www.torn.com/profiles.php?XID={tornId}) needs a revive.')

        # add status
        if response.get('status', False) and response["status"]["state"] == "Hospital":
            lst.append(f'{response["status"]["description"]} ({cleanhtml(response["status"]["details"])}).')

        eb = Embed(description='\n'.join(lst), color=my_blue)
        eb.set_author(name=f'Revive call from {ctx.author.display_name}', icon_url=ctx.author.avatar_url)
        eb.timestamp = now()

        # list of messages to delete them after
        delete = config.get("other", {}).get("delete", False)
        msgList = [[ctx.message, ctx.channel, delete]]
        ts_init = ts_now()
        # send message to current channel
        if len(errors):
            msg = "\n".join(errors)
            m = await self.bot.send_error_message(ctx.channel, msg)
            msgList.append([m, ctx.channel, delete])
        msg = "\n".join(lst)
        role = self.bot.get_module_role(ctx.guild.roles, config.get("roles_alerts", {}))
        mention = '' if role is None else f'{role.mention} '
        alert_channel = self.bot.get_module_channel(ctx.guild.channels, config.get("channels_alerts", {}))
        if alert_channel is None:
            m = await ctx.send(f'{mention}', embed=eb)
        else:
            m = await alert_channel.send(f'{mention}', embed=eb)
        msgList.append([m, ctx.channel, delete])

        # loop over all server to send the calls
        to_delete = []
        sending_ids = config.get("sending", {})
        for server_id, server_name in sending_ids.items():
            logging.debug(f'[revive/revive] {ctx.guild} -> {server_name} [{server_id}]')
            eb_remote = eb
            try:
                # get remote server coonfig
                remote_guild = get(self.bot.guilds, id=int(server_id))
                remote_guild = True
                if remote_guild is None or isinstance(remote_guild, bool):
                    logging.debug(f'[revive/revive] Delete unknown server: {ctx.guild} -> {server_name} [{server_id}]')
                    to_delete.append(server_id)
                    continue

                logging.debug(f'[revive/revive] Sending call: {ctx.guild} -> {remote_guild}')
                remote_config = self.bot.get_guild_configuration_by_module(remote_guild, "revive")

                if str(ctx.guild.id) in remote_config.get("blacklist", {}):
                    eb_bl = Embed(title="Revive call blacklisted", description=f'Server {remote_guild.name} has blacklisted you.', color=my_red)
                    m = await ctx.send(embed=eb_bl)
                    msgList.append([m, ctx.channel, delete])
                else:
                    # get guild, role, channel and delete option
                    remote_role = self.bot.get_module_role(remote_guild.roles, remote_config.get("roles_alerts", {}))
                    remote_channel = self.bot.get_module_channel(remote_guild.channels, remote_config.get("channels_alerts", {}))
                    remote_delete = remote_config.get("other", {}).get("delete", False)
                    mention = '' if remote_role is None else f'{remote_role.mention} '
                    delay = f'(delay: {ts_now() - ts_init}s)'
                    eb_remote.set_footer(text=f'{sendFrom} {delay}.')
                    if remote_channel is not None:
                        m = await remote_channel.send(mention, embed=eb_remote)
                        msgList.append([m, remote_channel, remote_delete])
                    else:
                        await self.bot.send_log(f'Error sending revive call to server {remote_guild}: revive channel not found', guild_id=ctx.guild.id)

            except BaseException as e:
                await self.bot.send_log(f'Error sending revive call to server {remote_guild}: {e}', guild_id=ctx.guild.id)


        if len(to_delete):
            for server_id in to_delete:
                del sending_ids[server_id]

            self.bot.configurations[ctx.guild.id]["revive"]["sending"] = sending_ids
            await set_configuration(self.bot.bot_id, ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            logging.debug(f"[revive/revive] <{ctx.guild}> push new sending list")

        # delete messages
        # wait for 5 minutes
        await asyncio.sleep(5 * 60)
        for [msg, cha] in [(m, c) for m, c, d in msgList if d]:
            try:
                await msg.delete()
            except BaseException as e:
                pass

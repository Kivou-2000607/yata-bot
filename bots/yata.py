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
import json
import os
import aiohttp
import traceback
import html
import logging
import asyncio

# import discord modules
import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

# import bot functions and classes
# from includes.yata_db import get_member_key
from inc.yata_db import set_configuration
from inc.yata_db import get_yata_user
from inc.handy import *


# Child class of Bot with extra configuration variables
class YataBot(Bot):
    def __init__(self, configurations=None, administrators=None, main_server_id=0, bot_id=0, github_token=None, **args):
        Bot.__init__(self, **args)
        self.configurations = configurations
        self.administrators = administrators
        self.bot_id = int(bot_id)
        self.github_token = github_token
        self.main_server_id = int(main_server_id)

    async def on_guild_join(self, guild):

        self.configurations[guild.id] = {}
        await set_configuration(self.bot_id, guild.id, guild.name, self.configurations[guild.id])

        user_to_send = [self.get_user(administrator_did) for administrator_did in self.administrators]
        owner = self.get_user(guild.owner_id)
        if owner not in user_to_send:
            user_to_send.append(owner)
        for user in user_to_send:
            await user.send(f"I **joined** the server **{guild} [{guild.id}]**")

    async def on_guild_remove(self, guild):

        if guild.id in self.configurations:
            self.configurations.pop(guild.id)
        await set_configuration(self.bot_id, guild.id, guild.name, {})

        user_to_send = [self.get_user(administrator_did) for administrator_did in self.administrators]
        owner = self.get_user(guild.owner_id)
        if owner not in user_to_send:
            user_to_send.append(owner)
        for user in user_to_send:
            await user.send(f"I **left** the server **{guild} [{guild.id}]**")

    async def discord_to_torn(self, member, key):
        """ get a torn id form discord id
            return tornId, None: okay
            return -1, error: api error
            return -2, None: not verified on discord
        """
        url = f"https://api.torn.com/user/{member.id}?selections=discord&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        if 'error' in req:
            # logging.info(f'[DISCORD TO TORN] api error "{key}": {req["error"]["error"]}')
            return -1, req['error']

        elif req['discord'].get("userID") == '':
            # logging.info(f'[DISCORD TO TORN] discord id {member.id} not verified')
            return -2, None

        else:
            return int(req['discord'].get("userID")), None

    async def get_master_key(self, guild):
        """ gets a random master key from configuration
            return 0, id, Name, Key: All good
            return -1, None, None, None: no key given
        """
        import random
        c = self.configurations.get(guild.id)
        if c is None:
            return -1, None, None

        torn_ids = [v["torn_id"] for k, v in c.get("admin", {}).get("server_admins", {}).items()]
        if len(torn_ids):
            user = await get_yata_user(random.choice(torn_ids), type="T")
            if not len(user):
                return -1, None, None
            else:
                user = tuple(user[0])
                return 0, user[0], user[2]
        else:
            return -1, None, None

    async def get_user_key(self, ctx, member, needPerm=True, returnMaster=False, delError=False, guild=False):
        """ gets a key from discord member
            return status, tornId, Name, key
            return 0, id, Name, Key: All good
            return -1, None, None, None: no master key given
            return -2, None, None, None: master key api error
            return -3, master_id, None, master_key: user not verified
            return -4, id, None, master_key: did not find torn id in yata db

            if returnMaster: return master key if key not available
            else return None
        """
        guild = ctx.guild if not guild and ctx else guild

        # skip all if user in yata with discord id
        user = await get_yata_user(member.id, type="D")
        if len(user):
            user = tuple(user[0])
            logging.debug(f"[get_user_key] got user from discord id: {user[1]} {user[0]}")
            return 0, user[0], user[1], user[2]

        # get master key to check identity

        # logging.info(f"[GET USER KEY] <{ctx.guild}> get master key")
        master_status, master_id, master_key = await self.get_master_key(ctx.guild)
        if master_status == -1:
            # logging.info(f"[GET USER KEY] <{ctx.guild}> no master key given")
            if ctx:
                m = await ctx.send(f'```md\n# Get torn ID\n< error > no master key given```')
                if delError:
                    await asyncio.sleep(5)
                    await m.delete()
            return -1, None, None, None
        # logging.info(f"[GET USER KEY] <{ctx.guild}> master key id {master_id}")

        # get torn id from discord id

        # logging.info(f"[GET USER KEY] <{ctx.guild}> get torn id for {member} [{member.id}]")
        tornId, msg = await self.discord_to_torn(member, master_key)

        # handle master api error or not verified member

        if tornId == -1:
            # logging.info(f'[GET MEMBER KEY] status -1: master key error {msg["error"]}')
            if ctx:
                m = await ctx.send(f'```md\n# Get torn ID\n< error > Torn API error with master key id {master_id}: {msg["error"]}```')
                if delError:
                    await asyncio.sleep(5)
                    await m.delete()
            return -2, None, None, None
        elif tornId == -2:
            # logging.info(f'[GET MEMBER KEY] status -2: user not verified')
            if ctx:
                m = await ctx.send(f'```md\n# Get torn ID\n< error > {member} are not not officially verified by Torn```')
                if delError:
                    await asyncio.sleep(5)
                    await m.delete()
            return -3, master_id, None, master_key if returnMaster else None

        # get YATA user

        user = await get_yata_user(tornId, type="T")

        # handle user not on YATA
        if not len(user):
            # logging.info(f"[GET MEMBER KEY] torn id {tornId} not in YATA")
            if ctx:
                m = await ctx.send(f':x: **{member}** is not in the YATA database. They have to log there so that I can use their key: https://yata.alwaysdata.net')
                if delError:
                    await asyncio.sleep(5)
                    await m.delete()
            return -4, tornId, None, master_key if returnMaster else None

        # Return user if perm given

        user = tuple(user[0])
        return 0, user[0], user[1], user[2]

    async def on_ready(self):
        # change activity
        activity = discord.Activity(name="TORN", type=discord.ActivityType.playing)
        await self.change_presence(activity=activity)

        logging.info("[SETUP] Ready...")

    def get_guilds_by_module(self, module):
        guilds = [g for g in self.guilds if self.configurations.get(g.id, {}).get(module, False)]
        return guilds

    def get_guild_configuration_by_module(self, guild, module, check_key=False):
        c = self.configurations.get(guild.id, {}).get(module, False)
        if check_key and c:
            return c if len(c.get(check_key, {})) else False
        else:
            return c

    def get_guild_admin_channel(self, guild):
        admin_id = [k for k in self.configurations.get(guild.id, {}).get("admin", {}).get("channels_admin", {})]
        if len(admin_id) and str(admin_id[0]).isdigit():
            return get(guild.channels, id=int(admin_id[0]))
        else:
            return None

    async def check_channel_allowed(self, ctx, config, channel_key=None):
        channel_key = "channels_allowed" if channel_key is None else channel_key

        if str(ctx.channel.id) not in config.get(channel_key, []):
            channels = [get(ctx.guild.channels, id=int(k)) for k in config.get(channel_key, {}) if str(k).isdigit()]
            msg = await ctx.send(f':no_entry: Command not allowed in this channel. Try {", ".join([c.mention for c in channels if c is not None])}.')
            await asyncio.sleep(5)
            await msg.delete()
            await ctx.message.delete()
            return False
        else:
            return True

    async def check_channel_admin(self, ctx):
        channel_admin = self.get_guild_admin_channel(ctx.guild)
        if ctx.channel is not channel_admin or channel_admin is None:
            msg = await ctx.send(f':no_entry: This command needs to be done in the admin channel: {"unset" if channel_admin is None else channel_admin.mention}.')
            await asyncio.sleep(5)
            await msg.delete()
            await ctx.message.delete()
            return False
        else:
            return True

    async def send_log_main(self, log, headers=dict({}), full=False):
        guild = get(self.guilds, id=self.main_server_id)
        logging.debug(f'[send_log_main] Guild: {guild}')
        channel = self.get_guild_admin_channel(guild)
        logging.debug(f'[send_log_main] channel: {channel}')
        if channel is None:
            logging.error(f'[send_log_main] no main system channel')
        else:
            await channel.send(log_fmt(log, headers=headers, full=full))

    async def send_log_dm(self, log, author):
        await author.send(log_fmt(log))

    async def send_log(self, log, guild_id=0, channel_id=0, ctx=None):
        # fallback if guild_id or channel_id has not been given
        if not guild_id:
            logging.warning(f'[send_log] guild_id not given -> sending to main server')
            await self.send_log_main(log, headers={"message": "guild_id not given"})
            return

        headers = {"guild_id": guild_id, "channel_id": channel_id, "note": []}
        if ctx is not None:
            headers["author_name"] = f'{ctx.author.nick} / {ctx.author}'
            headers["author_guild"] = ctx.guild
            headers["author_channel"] = ctx.channel
            headers["author_message"] = ctx.message.content
            headers["author_command"] = ctx.command

        if not log or log == "":
            loggin.warning('[send_log] empty log message')
            await self.send_log_main("empty log", headers=headers)
            return

        logging.debug(f'[send_log] guild_id: {guild_id} channel_id: {channel_id}')
        guild = get(self.guilds, id=guild_id)
        headers["guild"] = guild

        # fallback is guild not found
        if guild is None:
            logging.warning(f'[send_log] guild id {guild_id} not found -> sending to main server')
            await self.send_log_main(log, headers=headers)
            return

        channel = get(guild.channels, id=channel_id)
        if channel is None:
            headers["note"].append("channel id not provided")
            channel = self.get_guild_admin_channel(guild)
        headers["channel"] = channel

        # fallback if channel is not found
        if channel is None:
            logging.warning(f'[send_log] channel id {channel_id} not found')
            headers["note"].append("server admin channel not found")
            await self.send_log_main(log, headers=headers)
            return

        try:
            await channel.send(log_fmt(log))
            logging.info(f'[send_log] error {hide_key(log)} sent to {guild} #{channel}')

        except discord.errors.Forbidden:
            headers["note"].append(f"Forbidden to write in channel {channel}")
            channel_fb = self.get_guild_admin_channel(guild)

            if channel_fb == channel:
                await self.send_log_main(log, headers=headers)
                return

            headers["fallback_channel"] = channel_fb
            if channel_fb is None:
                headers["note"].append(f"server admin channel as fallback not found")
                await self.send_log_main(log, headers=headers)
                return

            try:
                await channel_fb.send(log_fmt(log))
                logging.info(f'[send_log] error {hide_key(log)} sent to {guild} #{channel} (fallback channel)')
                return
            except discord.errors.Forbidden:
                headers["note"].append(f"Forbidden to write in admin channel {channel_fb}")
                await self.send_log_main(log, headers=headers)
                return

    def get_module_role(self, guild_roles, configuration_roles, all=False):
        """ gets the role of a module for a guild:
            - guild_roles: the list of the roles of the guild
            - configuration_roles: the list of the roles of the configuration
            - all: return all roles if true, only the first one if False

            return: role, list of roles or None (if didn't find anything)
        """
        role_ids = [id for id in configuration_roles if id.isdigit()]
        if len(role_ids):
            if all:
                return [get(guild_roles, id=int(id)) for id in role_ids]
            else:
                return get(guild_roles, id=int(role_ids[0]))
        else:
            if all:
                return [None]
            else:
                return None

    def get_module_channel(self, guild_channels, configuration_channels, all=False):
        """ gets the channel of a module for a guild:
            - guild_channels: the list of the channels of the guild
            - configuration_channels: the list of the channels of the configuration
            - all: return all channels if true, only the first one if False

            return: channel, list of channels or None (if didn't find anything)
        """
        channel_ids = [id for id in configuration_channels if id.isdigit()]
        if len(channel_ids):
            if all:
                return [get(guild_channels, id=int(id)) for id in channel_ids]
            else:
                return get(guild_channels, id=int(channel_ids[0]))
        else:
            if all:
                return [None]
            else:
                return None

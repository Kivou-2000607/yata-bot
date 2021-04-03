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
import asyncpg
import random

# import discord modules
import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get
from discord import Embed

# import bot functions and classes
# from includes.yata_db import get_member_key
from inc.handy import *


# Child class of Bot with extra configuration variables
class YataBot(Bot):
    def __init__(self, configurations=None, database={}, main_server_id=0, bot_id=0, master_key="", github_token=None, **args):
        Bot.__init__(self, **args)
        self.configurations = configurations
        self.bot_id = int(bot_id)
        self.master_key = master_key
        self.github_token = github_token
        self.main_server_id = int(main_server_id)
        self.database = database
        self.factions_names = {}

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
        c = self.configurations.get(guild.id)
        if c is None:
            return -1, None, None

        torn_ids = [v["torn_id"] for k, v in c.get("admin", {}).get("server_admins", {}).items()]
        logging.info(f"[get_master_key] {guild}: {torn_ids}")
        if len(torn_ids):
            user = await self.get_yata_user(random.choice(torn_ids), type="T")
            # logging.info(f"[get_master_key] {guild}: user={user} len(user)={len(user)}")
            if not len(user):
                logging.warning(f"[get_master_key] {guild}: empty user")
                return -1, None, None
            else:
                user = tuple(user[0])
                return 0, user[0], user[2]
        else:
            logging.warning(f"[get_master_key] {guild}: no master keys ids found")
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
        user = await self.get_yata_user(member.id, type="D")
        if len(user):
            user = tuple(user[0])
            logging.debug(f"[get_user_key] got user from discord id: {user[1]} {user[0]}")
            return 0, user[0], user[1], user[2]

        # get master key to check identity

        logging.debug(f"[GET USER KEY] <{ctx.guild}> get master key")
        master_status, master_id, master_key = await self.get_master_key(ctx.guild)
        if master_status == -1:
            logging.debug(f"[GET USER KEY] <{ctx.guild}> no master key given")
            if ctx:
                m = await self.send_error_message(ctx, f'No master key given.', title="Error getting user API key")
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
            if ctx and msg is not None:
                m = await self.send_error_message(ctx, f'API error with master key id {master_id}: {msg["error"]}.', title="Error getting user API key")
                if delError:
                    await asyncio.sleep(5)
                    await m.delete()
            return -2, None, None, None
        elif tornId == -2:
            # logging.info(f'[GET MEMBER KEY] status -2: user not verified')
            if ctx:
                m = await self.send_error_message(ctx, f'{member} is not officially verified by Torn.', title="Error getting user API key")
                if delError:
                    await asyncio.sleep(5)
                    await m.delete()
            return -3, master_id, None, master_key if returnMaster else None

        # get YATA user

        user = await self.get_yata_user(tornId, type="T")

        # handle user not on YATA
        if not len(user):
            # logging.info(f"[GET MEMBER KEY] torn id {tornId} not in YATA")
            if ctx:
                m = await self.send_error_message(ctx, f'{member} is not in the YATA database. They have to log in the [website](https://yata.yt) so that I can use their key.', title="Error getting user API key")

                if delError:
                    await asyncio.sleep(5)
                    await m.delete()
            return -4, tornId, None, master_key if returnMaster else None

        # Return user if perm given

        user = tuple(user[0])
        return 0, user[0], user[1], user[2]

    async def on_connect(self):
        logging.info("Create async pool")
        self.pool = await asyncpg.create_pool(**self.database)
        logging.info("Pool created")

    async def on_ready(self):
        # change activity
        # activity = discord.Activity(name="over TORN's players", type=discord.ActivityType.watching)
        activity = discord.Activity(name="Torn", type=discord.ActivityType.playing)
        await self.change_presence(activity=activity)

        logging.info("Ready...")

    def get_guilds_by_module(self, module):
        guilds = [g for g in self.guilds if self.configurations.get(g.id, {}).get(module, False)]
        return guilds

    def get_guild_configuration_by_module(self, guild, module, check_key=False):
        c = self.configurations.get(guild.id, {}).get(module, False)
        if check_key and c:
            return c if len(c.get(check_key, {})) else False
        else:
            return c

    def get_guild_beta(self, guild):
        return self.configurations.get(guild.id, {}).get("admin", {}).get("other", {}).get("beta", False)

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
            allowed_channels = [c.mention for c in channels if c is not None]
            if len(allowed_channels):
                msg = await self.send_error_message(ctx, f'Command not allowed in this channel. Try {", ".join(allowed_channels)}.')
            else:
                msg = await self.send_error_message(ctx, f'Command not allowed in this channel. No channels have been setup.\nCheckout your [dashboard](https://yata.yt/bot/dashboard/).')

            await asyncio.sleep(5)
            try:
                await msg.delete()
                await ctx.message.delete()
            except BaseException:
                pass
            return False
        else:
            return True

    async def check_channel_admin(self, ctx):
        channel_admin = self.get_guild_admin_channel(ctx.guild)
        if ctx.channel is not channel_admin or channel_admin is None:
            msg = await self.send_error_message(ctx, f'This command needs to be done in the admin channel: {"unset" if channel_admin is None else channel_admin.mention}.')

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
            eb = log_fmt(log, headers=headers, full=full)
            await send(channel, embed=eb)

    async def send_log_dm(self, log, author):
        await send(author, embed=log_fmt(log))

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
            await send(channel, embed=log_fmt(log))
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
                await send(channel_fb, embed=log_fmt(log))
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

    async def on_guild_join(self, guild):

        channel = self.get_guild_admin_channel(get(self.guilds, id=self.main_server_id))
        eb = Embed(title="Bot joined a server", color=my_green)
        eb.add_field(name="Server name", value=guild)
        eb.add_field(name="Server id", value=f'`{guild.id}`')
        eb.add_field(name="Owner", value=guild.owner)
        eb.set_thumbnail(url=guild.icon_url)
        await send(channel, embed=eb)

        self.configurations[guild.id] = {}
        await self.set_configuration(guild.id, guild.name, self.configurations[guild.id])

    async def on_guild_remove(self, guild):

        channel = self.get_guild_admin_channel(get(self.guilds, id=self.main_server_id))
        eb = Embed(title="Bot left a server", color=my_red)
        eb.add_field(name="Server name", value=guild)
        eb.add_field(name="Server id", value=f'`{guild.id}`')
        eb.add_field(name="Owner", value=guild.owner)
        eb.set_thumbnail(url=guild.icon_url)
        await send(channel, embed=eb)

        if guild.id in self.configurations:
            self.configurations.pop(guild.id)
        await self.delete_configuration(guild.id)

    async def send_error_message(self, channel, description, fields={}, title=False, delete=False):
        title = title if title else "Error"
        eb = Embed(title=title, description=description, color=my_red)
        eb = append_update(eb, ts_now(), text="At ")
        for k, v in fields.items():
            eb.add_field(name=k, value=v)
        return await send(channel, embed=eb, delete=delete)

    async def send_help_message(self, channel, description, fields={}, delete=False):
        eb = Embed(title="Help", description=description, color=my_green)
        for k, v in fields.items():
            eb.add_field(name=k, value=v)
        return await send(channel, embed=eb, delete=delete)

    async def api_call(self, section, id, selections, key, check_key=[], error_channel=False, comment="yata-bot"):

        # proxy = True if len(key) == 32 else False
        # url = f'https://{"torn-proxy.com" if proxy else "api.torn.com"}/{section}/{id}?selections={",".join(selections)}&key={key}'
        proxy = False
        url = f'https://api.torn.com/{section}/{id}?selections={",".join(selections)}&key={key}&comment={comment}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                try:
                    response = await r.json()
                except BaseException:
                    response = {'error': {'error': 'API is talking shit... response not serializable.', 'code': -1}}

        if not isinstance(response, dict):
            response = {'error': {'error': 'API is talking shit... invalid response format.', 'code': -1}}

        if 'error' not in response:
            for key in check_key:
                if key not in response:
                    response = {'error': {'error': f'API is talking shit... key `{key}` not found in the response.', 'code': -1}}
                    break

        if 'error' in response:
            # change error message if it's a proxy error to format as per API error
            if proxy and 'proxy' in response:
                response = {'error': {'error': f'{response["error"]} (proxy error {response["proxy_code"]}: {response["proxy_error"]})', 'code': response["code"]}}
            if error_channel:
                await self.send_error_message(error_channel, response["error"]["error"], title=f'API Error code {response["error"]["code"]}')
            return response, True
        else:
            return response, False

    def get_faction_name(self, tId):
        return f'{html.unescape(self.factions_names.get(str(tId), "Faction"))} [{tId}]'


    # DB CALLS

    async def get_configuration(self, discord_id):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                server = await connection.fetchrow(f'SELECT configuration FROM bot_server WHERE bot_id = {self.bot_id} AND discord_id = {discord_id};')
                return False if server is None else json.loads(server.get("configuration"))


    async def set_n_servers(self, n):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute('''
                    UPDATE bot_bot SET number_of_servers = $1 WHERE id = $2'''
                    , n, self.bot_id)


    async def set_configuration(self, discord_id, server_name, configuration):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                # check if server already in the database
                server = await connection.fetchrow(f'SELECT * FROM bot_server WHERE bot_id = {self.bot_id} AND discord_id = {discord_id};')
                if server is None:  # create if not in the db
                    await connection.execute('''
                    INSERT INTO bot_server (bot_id, discord_id, name, configuration, secret) VALUES ($1, $2, $3, $4, $5)
                    ''', self.bot_id, discord_id, server_name, json.dumps(configuration), 'x')
                else:  # update otherwise
                    await connection.execute('''
                    UPDATE bot_server SET name = $3, configuration = $4 WHERE bot_id = $1 AND discord_id = $2
                    ''', self.bot_id, discord_id, server_name, json.dumps(configuration))


    async def delete_configuration(self, discord_id):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                # check if server already in the database
                server = await connection.fetchrow(f'SELECT * FROM bot_server WHERE bot_id = {self.bot_id} AND discord_id = {discord_id};')
                if server is not None:  # delete if in the db
                    # step 1 remove the admins
                    tmp = await connection.fetch(f'SELECT * FROM bot_server_server_admin WHERE server_id = {server.get("id")};')
                    await connection.execute(f'DELETE FROM bot_server_server_admin WHERE server_id = $1', server.get("id"))

                    # step 2 delete the configuration
                    await connection.execute(f'DELETE FROM bot_server WHERE bot_id = $1 AND discord_id = $2', self.bot_id, discord_id)


    async def get_server_admins(self, discord_id):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                server = await connection.fetchrow(f'SELECT * FROM bot_server WHERE bot_id = {self.bot_id} AND discord_id = {discord_id};')
                if server is None:
                    return {}, 'x'

                server_yata_id = server.get("id")
                players_yata_id = await connection.fetch(f'SELECT player_id FROM bot_server_server_admin WHERE server_id = {server_yata_id};')

                admins = {}
                for player_yata_id in [player.get("player_id") for player in players_yata_id]:
                    player = await connection.fetchrow(f'SELECT "tId", "dId", "name" FROM player_player WHERE "id" = {player_yata_id};')
                    dId = player.get("dId", 0)
                    if dId:
                        admins[str(dId)] = {"name": player.get("name", "?"), "torn_id": player.get("tId")}

                secret = json.loads(server.get("configuration", '{}')).get("admin", {}).get("secret", 'x')
                if secret == 'x':
                    secret = ''.join(random.choice(string.ascii_lowercase) for i in range(16))

                return admins, secret


    async def get_yata_user(self, user_id, type="T"):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                if type == "T":
                    user = await connection.fetch(f'SELECT "tId", "name", "value" FROM player_view_player_key WHERE "tId" = {user_id};')
                elif type == "D":
                    user = await connection.fetch(f'SELECT "tId", "name", "value" FROM player_view_player_key WHERE "dId" = {user_id};')

                return user


    async def push_data(self, timestamp, data, module):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                if module == "rackets":
                    await connection.execute('UPDATE bot_rackets SET timestamp = $1, rackets = $2 WHERE id = $3', timestamp, json.dumps(data), self.bot_id)
                elif module == "stocks":
                    await connection.execute('UPDATE bot_stocks SET timestamp = $1, rackets = $2 WHERE id = $3', timestamp, json.dumps(data), self.bot_id)
                elif module == "wars":
                    await connection.execute('UPDATE bot_wars SET timestamp = $1, wars = $2 WHERE id = $3', timestamp, json.dumps(data), self.bot_id)


    async def get_data(self, module):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                if module == "rackets":
                    resp = await connection.fetch(f"SELECT timestamp, rackets FROM bot_rackets WHERE id = {self.bot_id};")
                elif module == "stocks":
                    resp = await connection.fetch(f"SELECT timestamp, rackets FROM bot_stocks WHERE id = {self.bot_id};")
                elif module == "wars":
                    resp = await connection.fetch(f"SELECT timestamp, wars FROM bot_wars WHERE id = {self.bot_id};")

                timestamp, data = resp[0]
                return timestamp, json.loads(data)


    async def get_factions_names(self):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                rows = await connection.fetch('SELECT "tId", "name" FROM faction_faction')
                return rows


    async def reset_notifications(self, tornId):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute('UPDATE player_player SET "activateNotifications"=$1, "notifications"=$2 WHERE "tId"=$3', False, json.dumps({}), tornId)


    async def get_loots(self, scheduled=False):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                if scheduled:
                    loots = await connection.fetch(f'SELECT * FROM loot_scheduledAttack;')
                else:
                    loots = await connection.fetch(f'SELECT * FROM loot_NPC WHERE show = true;')

                return loots

    async def get_npc(self, id):
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                npc = await connection.fetch(f'SELECT * FROM loot_NPC WHERE "id"=$1;', id)
            return npc

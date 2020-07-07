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
import includes.formating as fmt
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

    # def get_config(self, guild):
    #     """ get_config: helper function
    #         gets configuration for a guild
    #     """
    #     return self.configs.get(str(guild.id), dict({}))
    #
    # def get_allowed_channels(self, config, key):
    #     channels = config.get(key)
    #     if channels is None:
    #         return [key]
    #     elif '*' in channels["channels"]:
    #         return ["*"]
    #     else:
    #         return channels["channels"]
    #
    # def get_allowed_roles(self, config, key):
    #     roles = config.get(key)
    #     if roles is None:
    #         return [key]
    #     elif '*' in roles["roles"]:
    #         return ["*"]
    #     else:
    #         return roles["roles"]
    #
    # async def discord_to_torn(self, member, key):
    #     """ get a torn id form discord id
    #         return tornId, None: okay
    #         return -1, error: api error
    #         return -2, None: not verified on discord
    #     """
    #     url = f"https://api.torn.com/user/{member.id}?selections=discord&key={key}"
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url) as r:
    #             req = await r.json()
    #
    #     if 'error' in req:
    #         # logging.info(f'[DISCORD TO TORN] api error "{key}": {req["error"]["error"]}')
    #         return -1, req['error']
    #
    #     elif req['discord'].get("userID") == '':
    #         # logging.info(f'[DISCORD TO TORN] discord id {member.id} not verified')
    #         return -2, None
    #
    #     else:
    #         return int(req['discord'].get("userID")), None

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

    async def get_user_key(self, ctx, member, needPerm=True, returnMaster=False, delError=False):
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
            m = await ctx.send(":x: no master key given")
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
            m = await ctx.send(f':x: Torn API error with master key id {master_id}: *{msg["error"]}*')
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -2, None, None, None
        elif tornId == -2:
            # logging.info(f'[GET MEMBER KEY] status -2: user not verified')
            m = await ctx.send(f':x: {member.mention} is not verified in the official Torn discord. They have to go there and get verified first: https://www.torn.com/discord')
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -3, master_id, None, master_key if returnMaster else None

        # get YATA user

        user = await get_yata_user(tornId, type="T")

        # handle user not on YATA
        if not len(user):
            # logging.info(f"[GET MEMBER KEY] torn id {tornId} not in YATA")
            m = await ctx.send(f':x: **{member}** is not in the YATA database. They have to log there so that I can use their key: https://yata.alwaysdata.net')
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -4, tornId, None, master_key if returnMaster else None

        # Return user if perm given

        user = tuple(user[0])
        return 0, user[0], user[1], user[2]

    # def check_module(self, guild, module):
    #     """ check_module: helper function
    #         check if guild activated a module
    #     """
    #     config = self.get_config(guild)
    #     if config.get(module) is None:
    #         return False
    #     else:
    #         return bool(config[module].get("active", False))
    #
    # async def on_ready(self):
    #     """ on_ready
    #         loop over the bot guilds and do the setup
    #     """
    #     await self.rebuildGuilds(reboot=True)
    #
    #     # change activity
    #     activity = discord.Activity(name="TORN", type=discord.ActivityType.playing)
    #     await self.change_presence(activity=activity)
    #
    #     logging.info("[SETUP] Ready...")
    #
    # async def on_guild_join(self, guild):
    #     """notifies me when joining a guild"""
    #     owner = self.get_user(guild.owner_id)
    #     for administratorId in self.administrators:
    #         administrator = self.get_user(int(administratorId))
    #         await administrator.send(f"I **joined** guild **{guild} [{guild.id}]** owned by **{owner}**")
    #
    # async def on_guild_remove(self, guild):
    #     """notifies me when leaving a guild"""
    #     owner = self.get_user(guild.owner_id)
    #     for administratorId in self.administrators:
    #         administrator = self.get_user(int(administratorId))
    #         await administrator.send(f"I **left** guild **{guild} [{guild.id}]** owned by **{owner}** because I got banned, kicked, left the guild or the guild was deleted.")
    #
    # async def rebuildGuild(self, guild, reboot=False, verbose=False):
    #     try:
    #         config = self.get_config(guild)
    #         lst = [f"{guild}  [{guild.id}]"]
    #
    #         # leave guild not in YATA database
    #         if not len(config):
    #             lst.append(f'\tWTF I\'m doing here?')
    #             # send message to guild
    #             owner = self.get_user(guild.owner_id)
    #             await owner.send(f"Contact and @Helper in the YATA server if you want me on your guild {guild} [{guild.id}].")
    #             await owner.send("As for now I can't do anything without him setting me up... so I'll be leaving.")
    #
    #             # leave guild
    #             await guild.leave()
    #
    #             # send message to creator
    #             for administratorId in self.administrators:
    #                 administrator = self.get_user(int(administratorId))
    #                 await administrator.send(f"On reboot I left **{guild} [{guild.id}]** owned by **{owner}** because no configurations were found in the database.")
    #
    #             if verbose:
    #                 await fmt.send_tt(verbose, lst)
    #             return
    #
    #         # push guild name to yata
    #         bot = get(guild.members, id=self.user.id)
    #         contact = self.get_user(int(config["admin"]["contact_discord_id"]))
    #         if contact is not None:
    #             lst.append("Guild info updated")
    #             config["admin"]["contact_discord"] = f'{contact}'
    #             await push_guild_info(guild, bot, contact, self.bot_id)
    #         else:
    #             lst.append(f'Guild info not updated because contact id {config["admin"]["contact_discord_id"]} (from config) not found by the bot.')
    #
    #         # stop if not managing channels
    #         if not config["admin"].get("manage", False):
    #             lst.append("Skip managing")
    #             if verbose:
    #                 await fmt.send_tt(verbose, lst)
    #             return
    #
    #         # create category
    #         yata_category = get(guild.categories, name="yata-bot")
    #         bot_role = get(guild.roles, name=self.user.name)
    #         if yata_category is None:
    #             lst.append("Create category yata-bot")
    #             yata_category = await guild.create_category("yata-bot")
    #
    #         # create admin channel
    #         channel_name = "yata-admin"
    #         if get(guild.channels, name=channel_name) is None:
    #             lst.append(f"\tCreate channel {channel_name}")
    #             overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), }
    #             if bot_role is not None:
    #                 overwrites[bot_role] = discord.PermissionOverwrite(read_messages=True)
    #             channel_admin = await guild.create_text_channel(channel_name, topic="Administration channel for the YATA bot", overwrites=overwrites, category=yata_category)
    #             await channel_admin.send(f"This is the admin channel for `!verifyAll`, `!checkFactions` or `!reviveServers`")
    #
    #         # create verified role and channels
    #         if self.check_module(guild, "verify"):
    #             role_verified = get(guild.roles, name="Verified")
    #             if role_verified is None:
    #                 lst.append(f"\tCreate role Verified")
    #                 role_verified = await guild.create_role(name="Verified")
    #
    #             # create faction roles
    #             fac = config.get("factions", dict({}))
    #             for k, v in fac.items():
    #                 role_name = html.unescape(f"{v} [{k}]" if config['verify'].get('id', False) else f"{v}")
    #                 if get(guild.roles, name=role_name) is None:
    #                     lst.append(f"\tCreate faction role {role_name}")
    #                     await guild.create_role(name=role_name)
    #
    #             # create common role
    #             com = config['verify'].get("common")
    #             if com:
    #                 role_name = get(guild.roles, name=com)
    #                 if role_name is None:
    #                     lst.append(f"\tCreate common role {com}")
    #                     await guild.create_role(name=com)
    #
    #             for channel_name in [c for c in config["verify"].get("channels", ["verify"]) if c != "*"]:
    #                 if get(guild.channels, name=channel_name) is None:
    #                     lst.append(f"\tCreate channel {channel_name}")
    #                     channel_verif = await guild.create_text_channel(channel_name, topic="Verification channel for the YATA bot", category=yata_category)
    #                     await channel_verif.send(f"If you haven't been assigned the {role_verified.mention} that's where you can type `!verify` or `!verify tornId` to verify another member")
    #
    #         if self.check_module(guild, "chain"):
    #             # create chain channel
    #             for channel_name in [c for c in config["chain"].get("channels", ["chain"]) if c != "*"]:
    #                 if get(guild.channels, name=channel_name) is None:
    #                     lst.append(f"\tCreate channel {channel_name}")
    #                     channel_chain = await guild.create_text_channel(channel_name, topic="Chain channel for the YATA bot", category=yata_category)
    #                     await channel_chain.send("Type `!chain` here to start getting notifications and `!stopchain` to stop them.")
    #                 # if reboot:
    #                 #     await get(guild.channels, name=channel_name).send(":arrows_counterclockwise: I had to reboot which stop all potential chains and retals watching. Please relaunch them.")
    #
    #         if self.check_module(guild, "crimes"):
    #             # create crimes channel
    #             for channel_name in [c for c in config["crimes"].get("channels", ["oc"]) if c != "*"]:
    #                 if get(guild.channels, name=channel_name) is None:
    #                     lst.append(f"\tCreate channel {channel_name}")
    #                     channel_oc = await guild.create_text_channel(channel_name, topic="Crimes channel for the YATA bot", category=yata_category)
    #                     await channel_oc.send("Type `!oc` here to start/stop getting notifications when ocs are ready.")
    #
    #         if self.check_module(guild, "rackets"):
    #             # create rackets channel
    #             for channel_name in [c for c in config["rackets"].get("channels", ["rackets"]) if c != "*"]:
    #                 if get(guild.channels, name=channel_name) is None:
    #                     lst.append(f"\tCreate channel {channel_name}")
    #                     await guild.create_text_channel(channel_name, topic="Rackets channel for the YATA bot", category=yata_category)
    #
    #             # create rackets roles
    #             for role_name in [c for c in config["rackets"].get("roles")]:
    #                 if role_name is not None and get(guild.roles, name=role_name) is None:
    #                     lst.append(f"\tCreate role {role_name}")
    #                     channel_oc = await guild.create_role(name=role_name, mentionable=True)
    #
    #         if self.check_module(guild, "loot"):
    #             # create Looter role
    #             role_loot = get(guild.roles, name="Looter")
    #             if role_loot is None:
    #                 lst.append(f"\tCreate role Looter")
    #                 role_loot = await guild.create_role(name="Looter", mentionable=True)
    #
    #             # create loot channel
    #             for channel_name in [c for c in config["loot"].get("channels", ["loot"]) if c != "*"]:
    #                 if get(guild.channels, name=channel_name) is None:
    #                     lst.append(f"\tCreate channel {channel_name}")
    #                     overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), }
    #                     if role_loot is not None:
    #                         overwrites[role_loot] = discord.PermissionOverwrite(read_messages=True)
    #                     if bot_role is not None:
    #                         overwrites[bot_role] = discord.PermissionOverwrite(read_messages=True)
    #                     logging.info(overwrites)
    #                     channel_loot = await guild.create_text_channel(channel_name, topic="Loot channel for the YATA bot", overwrites=overwrites, category=yata_category)
    #                     await channel_loot.send(f"{role_loot.mention} will reveive notification here")
    #                     await channel_loot.send("Type `!loot` here to get the npc timings")
    #                     await channel_loot.send(f"Type `!looter` to remove your {role_loot.mention} role")
    #
    #         if self.check_module(guild, "revive"):
    #             # create Reviver role
    #             reviver = get(guild.roles, name="Reviver")
    #             if reviver is None:
    #                 lst.append(f"\tCreate role Reviver")
    #                 reviver = await guild.create_role(name="Reviver", mentionable=True)
    #
    #             # create revive channel
    #             for channel_name in [c for c in config["revive"].get("channels", ["revive"]) if c != "*"]:
    #                 if get(guild.channels, name=channel_name) is None:
    #                     lst.append(f"\tCreate channel {channel_name}")
    #                     channel_revive = await guild.create_text_channel(channel_name, topic="Revive channel for the YATA bot", category=yata_category)
    #                     await channel_revive.send(f"{reviver.mention} will reveive notifications here")
    #                     await channel_revive.send("Type `!revive` or `!r` here to send a revive call")
    #                     await channel_revive.send(f"Type `!reviver` to add or remove your {reviver.mention} role")
    #
    #         if self.check_module(guild, "api"):
    #             # create api channels
    #             for channel_name in [c for c in config["api"].get("channels", ["api"]) if c != "*"]:
    #                 if get(guild.channels, name=channel_name) is None:
    #                     lst.append(f"\tCreate channel {channel_name}")
    #                     channel_api = await guild.create_text_channel(channel_name, topic="API channel for the YATA bot", category=yata_category)
    #                     await channel_api.send("Use the API module commands here")
    #
    #         # create socks role and channels
    #         if self.check_module(guild, "stocks"):
    #             stocks = config.get("stocks")
    #
    #             # wssb and tcb
    #             for stock in [s for s in stocks if s not in ["active", "channels", 'alerts', 'roles']]:
    #                 stock_role = get(guild.roles, name=stock)
    #                 if stock_role is None:
    #                     lst.append(f"\tCreate role {stock}")
    #                     stock_role = await guild.create_role(name=stock)
    #
    #                 # create stock channel
    #                 if get(guild.channels, name=stock) is None:
    #                     lst.append(f"\tCreate channel {stock}")
    #                     overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), }
    #                     if stock_role is not None:
    #                         overwrites[stock_role] = discord.PermissionOverwrite(read_messages=True)
    #                     if bot_role is not None:
    #                         overwrites[bot_role] = discord.PermissionOverwrite(read_messages=True)
    #                     channel_stock = await guild.create_text_channel(stock, topic=f"{stock} stock channel for the YATA bot", overwrites=overwrites, category=yata_category)
    #                     await channel_stock.send(f"Type `!{stock}` to see the {stock} BB status amoung the members")
    #
    #             # create alerts
    #             if stocks.get("alerts"):
    #                 stock_role = get(guild.roles, name="Trader")
    #                 if stock_role is None:
    #                     lst.append(f"\tCreate role Trader")
    #                     stock_role = await guild.create_role(name="Trader", mentionable=True)
    #
    #                 for channel_name in [c for c in config["stocks"].get("channels", ["stocks"]) if c != "*"]:
    #                     if get(guild.channels, name=channel_name) is None:
    #                         lst.append(f"\tCreate channel {channel_name}")
    #                         overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), }
    #                         if stock_role is not None:
    #                             overwrites[stock_role] = discord.PermissionOverwrite(read_messages=True)
    #                         if bot_role is not None:
    #                             overwrites[bot_role] = discord.PermissionOverwrite(read_messages=True)
    #                         channel_stock = await guild.create_text_channel(channel_name, topic=f"Alerts stock channel for the YATA bot", overwrites=overwrites, category=yata_category)
    #                         await channel_stock.send(f"{stock_role.mention} will be notified here")
    #
    #         if verbose:
    #             await fmt.send_tt(verbose, lst)
    #
    #     except BaseException as e:
    #         logging.error(f'[rebuildGuild] {guild} [{guild.id}]: {hide_key(e)}')
    #         await self.send_log(e, guild_id=guild.id)
    #         headers = {"guild": guild, "guild_id": guild.id, "error": "error on rebuild"}
    #         await self.send_log_main(e, headers=headers, full=True)
    #
    # async def rebuildGuilds(self, reboot=False, verbose=False):
    #     # loop over guilds
    #     for guild in self.guilds:
    #         await self.rebuildGuild(guild, reboot=reboot, verbose=verbose)

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
        admin_id = [k for k in self.configurations.get(guild.id, {}).get("admin", {}).get("channel_admin", {})]
        if len(admin_id) and str(admin_id[0]).isdigit():
            return get(guild.channels, id=int(admin_id[0]))
        else:
            return None

    async def check_channel_allowed(self, ctx, config):
        if str(ctx.channel.id) not in config.get("channels_allowed"):
            channels = [get(ctx.guild.channels, id=int(k)) for k in config.get("channels_allowed", {}) if str(k).isdigit()]
            msg = await ctx.send(f':no_entry: Command not allowed in this channel. Try {", ".join([c.mention for c in channels if c is not None])}.')
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

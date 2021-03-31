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
import re
import json
import aiohttp
import traceback
import sys
import logging
import html
import asyncio
import datetime
import lorem

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get
from discord.utils import oauth_url
from discord import Embed
from discord.ext import tasks

# import bot functions and classes
from inc.handy import *


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = self.bot.bot_id
        if self.bot.bot_id in [1, 3]:
            self.cleanServers.start()
            self.updateFactionNames.start()
        if self.bot.bot_id == 3:
            self.assignRoles.start()

    def cog_unload(self):
        if self.bot.bot_id in [1, 3]:
            self.cleanServers.cancel()
            self.updateFactionNames.cancel()
        if self.bot.bot_id == 3:
            self.assignRoles.cancel()

    @commands.command()
    @commands.guild_only()
    async def debug(self, ctx):
        content = "A " * 10000
        eb = Embed(title="Hello", color=my_blue)
        for i in range(2):
            eb.add_field(name=f'Field {i}'*200, value=f'YOLO' * 10000)

        eb.set_footer(text="way to long text for a footer" * 100)
        # eb.set_author(name="My name is way too long" * 100, url="https://www.torn.com/loader.php?sid=attack&user2ID=4", icon_url="https://yata.yt/media/loot/npc_4.png")
        eb.set_author(name="My name is way too long" * 100)
        await send(ctx, content, embed=eb)


    @commands.command()
    @commands.guild_only()
    async def sync(self, ctx):
        """updates dashboard and bot configuration"""
        logging.info(f'[admin/sync] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # for printing the updates
        updates = []

        # get configuration from the database and create if new
        configuration_db = await self.bot.get_configuration(ctx.guild.id)

        # create in database if new
        if not configuration_db:
            logging.info(f'[admin/sync] Create db configuration for {ctx.guild}')
            await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, {"admin": {}})
            updates.append("- create server database")

        # check if server admin and secret
        server_admins, server_secret = await self.bot.get_server_admins(ctx.guild.id)
        if len(server_admins):
            eb = Embed(title="Server administrators", color=my_blue)
            for server_admin_id, server_admin in server_admins.items():
                you = ' (you)' if int(server_admin_id) == ctx.author.id else ''
                eb.add_field(name=f'{server_admin["name"]} [{server_admin["torn_id"]}]{you}', value=f'{self.bot.get_user(int(server_admin_id))} [{server_admin_id}]')
        else:
            eb = Embed(title="Server administrators", description="No administrators", color=my_red)

        await send(ctx, embed=eb)

        if str(ctx.author.id) not in server_admins:
            updates.append("You need to be an administrator to continue, ask a @Staff for help on the [YATA discord server](https://yata.yt/discord).")
            eb = Embed(title="Dashboard synchronization", description="\n".join(updates), color=my_red)
            await send(ctx, embed=eb)
            return

        # create not configuration if need
        if ctx.guild.id not in self.bot.configurations:
            logging.info(f'[admin/sync] create bot configuration')
            self.bot.configurations[ctx.guild.id] = {"admin": {}}

        # deep copy of the bot configuration in a temporary variable to check differences
        configuration = dict(self.bot.configurations[ctx.guild.id])

        # get list of channels
        channels = {}
        for channel in ctx.guild.text_channels:
            channels[str(channel.id)] = f'{channel}'

        # get list of roles
        roles = {}
        role_list = [r for r in ctx.guild.roles if not any([r.managed, r.is_default()])]
        role_list.reverse()
        for role in role_list:
            roles[str(role.id)] = f'{role}'

        # set admin section of the configuration
        if "admin" not in configuration:
            configuration["admin"] = {}
        bot = get(ctx.guild.members, id=self.bot.user.id)
        configuration["admin"]["joined_at"] = int(datetime.datetime.timestamp(bot.joined_at))
        configuration["admin"]["guild_id"] = str(ctx.guild.id)
        configuration["admin"]["guild_name"] = ctx.guild.name
        configuration["admin"]["owner_did"] = str(ctx.guild.owner.id) if ctx.guild.owner is not None else 0
        configuration["admin"]["owner_dname"] = f'{ctx.guild.owner}' if ctx.guild.owner is not None else "Unknown owner"
        configuration["admin"]["channels"] = channels
        configuration["admin"]["roles"] = roles
        configuration["admin"]["server_admins"] = server_admins
        configuration["admin"]["secret"] = server_secret
        configuration["admin"]["last_sync"] = ts_now()

        # update modules
        for module in ["admin", "rackets", "wars", "loot", "revive", "verify", "oc", "stocks", "chain"]:
            # if configuration_db.get("rackets", False) and len(configuration_db["rackets"].get("channels", [])):
            if configuration_db.get(module, False):
                if module not in configuration:
                    updates.append(f":white_check_mark: **{module}** enabled")
                else:
                    for key, value in configuration_db[module].items():
                        if configuration[module].get(key, {}) != value:
                            updates.append(f":arrows_counterclockwise: **{module} {key}** updated")
                    for key in configuration[module]:
                        if key not in configuration_db[module]:
                            updates.append(f":x: **{module} {key}** disabled")

                # choose how to sync
                if module in ["rackets", "wars", "loot", "revive", "verify", "oc", "stocks", "chain"]:
                    # db erase completely bot config
                    configuration[module] = configuration_db[module]
                elif module in ["admin"]:
                    # db is updated with bot config
                    # except for prefix
                    configuration[module]["prefix"] = configuration_db[module].get("prefix", {'!': '!'})

                    # update admin channel
                    for key in ["channels_admin", "message_welcome", "channels_welcome", "other"]:
                        if configuration_db[module].get(key, False):
                            configuration[module][key] = configuration_db[module].get(key)
                        elif key in configuration[module]:
                            del configuration[module][key]

                else:
                    updates.append(f":no_entry_sign: {module} ignored")

            elif module in configuration and module not in ["admin"]:
                configuration.pop(module)
                updates.append(f":x: **{module}** disabled")

        # push configuration
        # print(json.dumps(configuration))
        await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, configuration)

        self.bot.configurations[ctx.guild.id] = configuration

        if not len(updates):
            updates.append("None")
        updates.append("\nCheck out [your dashboard](https://yata.yt/bot/dashboard/).")
        eb = Embed(title="Dashboard synchronization", description="\n".join(updates), color=my_blue)
        await send(ctx, embed=eb)


    @commands.command()
    @commands.has_any_role(679669933680230430, 669682126203125760)
    async def info(self, ctx, *args):
        """Admin tool for the bot owner"""
        logging.info(f'[admin/info] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        if not (len(args) and args[0].isdigit()):
            await self.bot.send_error_message(ctx, '!info < server id > or !info < member id >')
            return

        configurations = self.bot.configurations

        id = int(args[0])
        if id in configurations:
            guild = get(self.bot.guilds, id=id)
            server_admins = configurations[id].get("admin", {}).get("server_admins")

            eb = Embed(title=f'Server information', description=f"{guild} [{guild.id}]", color=my_blue)
            for i, (k, v) in enumerate(server_admins.items()):
                lst = []
                member = get(guild.members, id=int(k))
                if member is not None:
                    lst.append(f'__Discord__: {member} [{member.id}] aka {member.display_name}')
                else:
                    lst.append(f'__Discord__: Left his own server (id={int(k)})')
                lst.append(f'__Torn__: {v["name"]} [{v["torn_id"]}]')

                eb.add_field(name=f'Admin #{i + 1}', value="\n".join(lst))
            eb.add_field(name=f'Owner', value=f"{guild.owner} [{guild.owner.id}]")
            eb.set_thumbnail(url=guild.icon_url)

            await send(ctx, embed=eb)
            return

        # get all contacts
        contacts = []
        for k, v in configurations.items():
            admins = [discord_id for discord_id in v.get("admin", {}).get("server_admins", {})]
            contacts += admins

        if str(id) in contacts:
            member = get(ctx.guild.members, id=id)
            guild_ids = [k for k, v in configurations.items() if str(id) in v.get("admin", {}).get("server_admins", {})]

            if member is None:
                lst = [f"Discord member id {member.id} not found in this server", ""]
            else:
                lst = [f"Discord member {member} [{member.id}] aka {member.display_name}", ""]

            for i, k in enumerate(guild_ids):
                guild = get(self.bot.guilds, id=int(k))
                lst.append(f'__Server #{i + 1}__ {guild} [{guild.id}]')

            eb = Embed(title=f'Administrator information', description="\n".join(lst), color=my_blue)
            eb.set_thumbnail(url=member.avatar_url)
            await send(ctx, embed=eb)
            return

        await self.bot.send_error_message(ctx, f'Server or member id `{args[0]}` not found in the configuration')


    @commands.command()
    @commands.has_any_role(669682126203125760)
    async def talk(self, ctx, *args):
        """Admin tool for the bot owner"""
        logging.info(f'[admin/talk] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        for k in args:
            logging.info(f'[admin/talk] args: {k}')

        if not(len(args) == 2 and args[1].isdigit()):
            await send(ctx, ":x: You need to enter a channel and a message```!talk < #channel > < message_id >```Error: number of arguments = {}".format(len(args)))
            return

        msg = [_ for _ in await ctx.channel.history().flatten() if _.id == int(args[1])]
        if len(msg) < 1:
            await send(ctx, f':x: Message id `{args[1]}` not found in the channel recent history')
            return
        msg = msg[0].content

        if args[0] == "all_servers":  # send message to all servers
            for guild in self.bot.guilds:
                sent = False

                # try and get yata admin
                channel = get(guild.channels, name="yata-admin")
                if channel is None:
                    logging.info(f"[admin/talk] Guild {guild}: yata-admin not found")
                else:
                    try:
                        await send(channel, msg)
                        logging.info(f"[admin/talk] Guild {guild}: message sent to #{channel}")
                        sent = True
                        continue
                    except BaseException as e:
                        logging.info(f"[admin/talk] Guild {guild}: failed to send in #{channel} ({e})")
                        pass

                for channel in guild.text_channels:
                    try:
                        await send(channel, msg)
                        logging.info(f"[admin/talk] Guild {guild}: message sent to #{channel}")
                        sent = True
                        break
                    except BaseException as e:
                        logging.info(f"[admin/talk] Guild {guild}: failed to send in #{channel} ({e})")
                        pass

                if not sent:
                    logging.warning(f"[admin/talk] Guild {guild}: failed to send message")

        else:  # send message to specific channel on yata server
            channel_id = is_mention(args[0], type="channel")
            if not channel_id or not channel_id.isdigit():
                await send(ctx, ":x: You need to enter a channel and a message```!talk #channel < message_id >```Error: channel id = {}".format(channel_id))
                return

            channel = get(ctx.guild.channels, id=int(channel_id))
            if channel is None:
                await send(ctx, ":x: You need to enter a channel and a message```!talk #channel < message_id >```Error: channel = {}".format(channel))
                return

            await send(channel, msg)
            await send(ctx, f"Message send to {channel.mention}```{msg}```")

    @commands.command()
    async def rtfm(self, ctx, *args):
        modules = ["admin", "verify", "loot", "chain", "rackets", "wars", "stocks", "revive", "crimes", "api"]
        hash = f"#{args[0]}" if len(args) and args[0] in modules else ""
        await send(ctx, f"https://yata.yt/bot/documentation/{hash}")

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, read_message_history=True)
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(self, ctx, *args):
        """Clear not pinned messages"""
        logging.info(f'[admin/clear] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        if self.bot.bot_id in [2]:
            return

        limit = (int(args[0]) + 1) if (len(args) and args[0].isdigit()) else 100
        async for m in ctx.channel.history(limit=limit):
            if not m.pinned:
                try:
                    await m.delete()
                except BaseException as e:
                    return

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, read_message_history=True)
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def suppress(self, ctx, *args):
        """Clear not pinned messages"""
        logging.info(f'[admin/suppress] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        await ctx.message.delete()
        limit = (int(args[0]) + 1) if (len(args) and args[0].isdigit()) else 100
        async for m in ctx.channel.history(limit=limit):
            if not m.pinned:
                try:
                    await m.edit(suppress=True)
                except BaseException as e:
                    return

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def help(self, ctx):
        """help command"""
        logging.info(f'[admin/help] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        lst = [
            "Have a look at the [online documentation](https://yata.yt/bot/documentation/) or browse the links.",
            "If you need more information ping a @Staff in the [YATA server](https://yata.yt/discord).", ]
        embed = Embed(title="YATA bot help", description="\n".join(lst), color=550000)

        lst = ["[General information](https://yata.yt/bot/)",
               f"[Host the bot](https://yata.yt/bot/host/)",
               # f"[Invite]({oauth_url(self.bot.user.id, discord.Permissions(permissions=8))}) / [Dashboard](https://yata.yt/bot/dashboard/)"
               # "[FAQ]() soon...",
               ]
        embed.add_field(name='About the bot', value='\n'.join(lst))

        lst = ["[Official TORN verification](https://discordapp.com/api/oauth2/authorize?client_id=441210177971159041&redirect_uri=https%3A%2F%2Fwww.torn.com%2Fdiscord.php&response_type=code&scope=identify)",
               "[Permissions](https://discord.com/developers/docs/topics/permissions) / [hierarchy](https://discord.com/developers/docs/topics/permissions#permission-hierarchy)", ]
        embed.add_field(name='Links', value='\n'.join(lst))

        lst = ["[Forum tutorial](https://www.torn.com/forums.php#/p=threads&f=61&t=16121398)",
               "[Loot level timers](https://yata.yt/loot/)", ]
        embed.add_field(name='Loot', value='\n'.join(lst))

        embed.set_thumbnail(url="https://yata.yt/media/yata.png")

        await send(ctx, "", embed=embed)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.guild_only()
    async def assign(self, ctx, *args):
        logging.info(f'[admin/assign] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # ADMIN PART

        if len(args) and args[0].lower() == "host":
            # return if not admin
            admin_role = get(ctx.guild.roles, id=669682126203125760)
            if admin_role not in ctx.author.roles:
                return

            r = get(ctx.guild.roles, id=657131110077169664)
            if r is None:
                await send(ctx, f":x: no role {args[0]}")
                return

            msg = await send(ctx, f":clock1: Assigning {r}")

            # now that we have discord id of contacts it's easier to use that to assign roles

            # get all contacts
            contacts = []
            for k, v in self.bot.configurations.items():
                admins = [discord_id for discord_id in v.get("admin", {}).get("server_admins", {})]
                contacts += admins

            # loop over member
            n = len(ctx.guild.members)
            for i, member in enumerate(ctx.guild.members):

                if str(member.id) in contacts and r not in member.roles:
                    logging.info(f"[admin/assign] {member.display_name} add {r}")
                    await member.add_roles(r)
                elif str(member.id) not in contacts and r in member.roles:
                    logging.info(f"[admin/assign] {member.display_name} remove {r}")
                    await member.remove_roles(r)

                progress = int(100 * i / float(n))
                if not i % (1 + n // 4):
                    await msg.edit(content=f":clock{i%12 + 1}: Assigning {r} `{progress:>3}%`")

            await msg.edit(content=f":white_check_mark: Assigning {r} `100%`")

            return

        # elif len(args) and args[0].lower() == "yata":
        #     # return if not admin
        #     admin_role = get(ctx.guild.roles, id=669682126203125760)
        #     if admin_role not in ctx.author.roles:
        #         return

        #     r = get(ctx.guild.roles, id=703674852476846171)

        #     # loop over member
        #     if r is None:
        #         await send(ctx, f":x: no role {args[0]}")
        #     else:
        #         msg = await send(ctx, f":clock1: Assigning {r}")

        #     n = len(ctx.guild.members)
        #     for i, member in enumerate(ctx.guild.members):
        #         if len(await self.bot.get_yata_user(member.id, type="D")) and r not in member.roles:
        #             logging.info(f"[admin/assign] {member.display_name} add {r}")
        #             await member.add_roles(r)

        #         elif not len(await self.bot.get_yata_user(member.id, type="D")) and r in member.roles:
        #             logging.info(f"[admin/assign] {member.display_name} remove {r}")
        #             await member.remove_roles(r)

        #         progress = int(100 * i / float(n))
        #         if not i % (1 + n // 25):
        #             await msg.edit(content=f":clock{i%12 + 1}: Assigning {r} `{progress:>3}%`")

        #     await msg.edit(content=f":white_check_mark: Assigning {r} `100%`")

        #     return

        # PUBLIC PART

        # check argument
        logging.debug(f'[admin/assign] args: {args}')
        modules = ["revive", "rackets", "wars", "loot", "stocks"]
        if len(args) and args[0] in modules:
            module = args[0]
        else:
            await self.bot.send_error_message(ctx, f'Modules with self assignement roles: {", ".join(modules)}.')
            return

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, module)
        if not config:
            await self.bot.send_error_message(ctx, f'Module **{module}** not activated.')
            return

        # get role
        role = self.bot.get_module_role(ctx.guild.roles, config.get("roles_alerts", {}))

        if role is None:
            # not role
            await self.bot.send_error_message(ctx, f'No roles has been attributed to the module **{module}**.')
            return

        elif role in ctx.author.roles:
            # remove
            add = False
            await ctx.author.remove_roles(role)
        else:
            # assign
            add = True
            await ctx.author.add_roles(role)

        eb = Embed(description=f'Role @{html.unescape(role.name)} **{"added" if add else "removed"}** for module **{module}**', color=my_green if add else my_red)
        eb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        msg = await send(ctx, embed=eb)

        # clean messages
        await asyncio.sleep(5)
        try:
            await msg.delete()
            await ctx.message.delete()
        except BaseException:
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Welcome message"""

        # check if bot
        if member.bot:
            return

        # get configuration
        config = self.bot.get_guild_configuration_by_module(member.guild, "admin", check_key="message_welcome")
        if not config:
            return

        # get welcome channel
        welcome_channel = self.bot.get_module_channel(member.guild.channels, config.get("channels_welcome", {}))

        # fall back to system channel
        if welcome_channel is None:
            welcome_channel = member.guild.system_channel

        if welcome_channel is None:
            return

        # get system channel and send message
        logging.debug(f'[admin/on_member_join] welcome channel: #{welcome_channel}')

        msg = []
        for line in config["message_welcome"]:
            discord_line = []
            for w in line.split(" "):
                if not len(w):
                    pass

                elif w[0] in ["#", "@"]:
                    # search for ponctuation
                    search = re.search(r'([\,!?.;:]+)$', w)
                    if search:
                        ponc = w[search.span()[0]:]
                        word = w[1:search.span()[0]]
                    else:
                        ponc = ''
                        word = w[1:]

                    lookup = member.guild.channels if w[0] == '#' else member.guild.roles
                    obj = member if word == "new_member" else get(lookup, name=word.replace("_", " "))
                    if obj is not None:
                        if w[0] == '#':
                            discord_line.append(f'{obj.mention}{ponc}')
                        elif word == "new_member":
                            discord_line.append(f'**{obj.display_name}**{ponc}')
                        else:
                            discord_line.append(f'**@{obj}**{ponc}')
                    else:
                        discord_line.append(f'*{w[0]}{word.replace("_", " ")}*{ponc}')

                else:
                    discord_line.append(w)

            msg.append(" ".join(discord_line))

        eb = Embed(description="\n".join(msg), color=my_blue)
        # eb.set_author(name=self.bot.user.display_name, url="https://yata.yt/bot/documentation/", icon_url=self.bot.user.avatar_url)
        # eb.set_thumbnail(url=member.avatar_url)
        await send(welcome_channel, embed=eb)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        # ignored errors
        ignored = (commands.CommandNotFound, commands.UserInputError)
        if isinstance(error, ignored):
            return

        logging.info(f'[admin/on_command_error] {ctx.guild} / {ctx.author} / {ctx.command} / {hide_key(error)}')

        # dm/guild errors
        if isinstance(error, commands.NoPrivateMessage):
            await self.bot.send_log_dm(error, ctx.author)
            return

        if isinstance(error, commands.PrivateMessageOnly):
            await self.bot.send_log(error, guild_id=ctx.guild.id, channel_id=ctx.channel.id, ctx=ctx)
            return

        # classical errors
        classical = (commands.MissingPermissions,
                     commands.BotMissingPermissions,
                     commands.MissingAnyRole,
                     commands.MissingRole)
        if isinstance(error, classical):
            await self.bot.send_log(error, guild_id=ctx.guild.id, channel_id=ctx.channel.id, ctx=ctx)
            return

        # bugs or fatal errors

        if ctx.guild is None:
            logging.error("Could no send error message because guild is None")
            logging.error(ctx)
            logging.error(error)

        # headers
        headers = {
            "guild": f'{ctx.guild} [{ctx.guild.id}]',
            "channel": ctx.channel,
            "author": ctx.author,
            "command": ctx.command,
            "message": ctx.message.content,
            "error": f'{type(error)}'}

        # the user is missing role
        if isinstance(error, commands.MissingRole):
            headers["error"] = 'MissingRole'
            await self.bot.send_log_main(error, headers=headers, full=True)
            logging.error(error)
            return

        # if isinstance(error, discord.Forbidden):
        #     headers["error"] = 'Forbidden'
        #     logging.error(error)
        #     await self.bot.send_log_main(error, headers=headers, full=True)
        #     return

        if isinstance(error, commands.CommandInvokeError):
            headers["error"] = 'CommandInvokeError'
            logging.error(f'[admin/on_command_error] {hide_key(error)}')
            await self.bot.send_log_main(error, headers=headers, full=True)
            return

        headers["error"] = 'New error'
        logging.error(f'[admin/on_command_error] {hide_key(error)}')
        await self.bot.send_log_main(error, headers=headers, full=True)

    @tasks.loop(hours=24)
    async def updateFactionNames(self):
        logging.debug("[admin/updateFactionNames] start task")
        self.bot.factions_names = {str(f.get("tId")): f.get("name") for f in await self.bot.get_factions_names()}
        logging.debug("[admin/updateFactionNames] end task")

    @tasks.loop(hours=24)
    async def assignRoles(self):
        logging.debug("[admin/assignRoles] start task")

        guild = get(self.bot.guilds, id=self.bot.main_server_id)

        # assign @host and @yata
        host = get(guild.roles, id=657131110077169664)
        # yata = get(guild.roles, id=703674852476846171)
        # if host is None or yata is None:
        if host is None:
            return

        # get all contacts
        contacts = []
        for k, v in self.bot.configurations.items():
            admins = [discord_id for discord_id in v.get("admin", {}).get("server_admins", {})]
            contacts += admins

        # loop over member and toggle roles
        for member in guild.members:

            if str(member.id) in contacts and host not in member.roles:
                logging.info(f"[admin/assignRoles] {member.display_name} add {host}")
                await member.add_roles(host)
            elif str(member.id) not in contacts and host in member.roles:
                logging.info(f"[admin/assignRoles] {member.display_name} remove {host}")
                await member.remove_roles(host)

            # is_yata = await self.bot.get_yata_user(member.id, type="D")
            # if len(is_yata) and yata not in member.roles:
            #     logging.info(f"[admin/assignRoles] {member.display_name} add {yata}")
            #     await member.add_roles(yata)

            # elif not len(is_yata) and yata in member.roles:
            #     logging.info(f"[admin/assignRoles] {member.display_name} remove {yata}")
            #     await member.remove_roles(yata)


    @tasks.loop(hours=24)
    async def cleanServers(self):
        logging.info(f'[admin/cleanServers] start task')

        # get main channel
        guild = get(self.bot.guilds, id=self.bot.main_server_id)
        channel = self.bot.get_guild_admin_channel(guild)

        await send(channel, embed=Embed(description="Start cleaning servers and configurations", color=my_blue))

        await self.bot.set_n_servers(len(self.bot.guilds))
        for server in self.bot.guilds:
            config = self.bot.get_guild_configuration_by_module(server, "admin", check_key="server_admins")
            bot = get(server.members, id=self.bot.user.id)
            days_since_join = (ts_now() - int(datetime.datetime.timestamp(bot.joined_at))) / (60 * 60 * 24.)

            # logging.info(f'[admin/servers] Bot in server {server} [{server.id}]')
            if config:
                logging.info(f'[admin/servers] Bot in server {server} [{server.id}]: ok')
            else:
                logging.info(f'[admin/servers] Bot in server {server} [{server.id}]: no configuration or no admin since {days_since_join:.2f} days')

                if days_since_join > 7:
                    await send(channel, embed=Embed(title="Bot configuration cleaning", description=f"I left server {server} [{server.id}] because there is no configurations or no admins since {days_since_join:.2f} days", color=my_blue))
                    await server.leave()
                    if server.id in self.bot.configurations:
                        self.bot.configurations.pop(server.id)

        for server_id in [s for s in self.bot.configurations if s not in [g.id for g in self.bot.guilds]]:
            logging.info(f'[admin/servers] No bot in configuration id [{server_id}]')
            try:
                await self.bot.delete_configuration(server_id)
                await send(channel, embed=Embed(title="Bot configuration cleaning", description=f"I deleted the configuration of server ID {server_id} because I'm not in the server anymore", color=my_blue))
            except BaseException as e:
                await send(channel, embed=Embed(title="Bot configuration cleaning", description=f"I can't delete the configuration of server ID {server_id} because there is still an administartor even if I'm not in the server anymore", color=my_red))
                pass

        await send(channel, embed=Embed(description="Done cleaning servers and configurations", color=my_blue))

    @updateFactionNames.before_loop
    async def before_updateFactionNames(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    @assignRoles.before_loop
    async def before_assignRoles(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    @cleanServers.before_loop
    async def before_cleanServers(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

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

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get
from discord.utils import oauth_url
from discord import Embed

# import bot functions and classes
from inc.yata_db import set_configuration
from inc.yata_db import get_server_admins
from inc.yata_db import get_configuration

import includes.formating as fmt
from includes.checks import is_mention
from includes.yata_db import get_yata_user_by_discord
from inc.handy import *


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = self.bot.bot_id

    @commands.command()
    @commands.guild_only()
    async def update(self, ctx):
        """updates dashboard and bot configuration"""
        logging.info(f'[admin/update] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # for printing the updates
        updates = ["```md", "# Updates"]

        # get configuration from the database and create if new
        configuration_db = await get_configuration(self.bot_id, ctx.guild.id)

        # create in database if new
        if not configuration_db:
            logging.info(f'[admin/update] Create db configuration for {ctx.guild}')
            await set_configuration(self.bot_id, ctx.guild.id, ctx.guild.name, {"admin": {}})
            updates.append("- create server database")

        # check if server admin
        server_admins = await get_server_admins(self.bot_id, ctx.guild.id)
        admins_lst = ["```md", "# Bot admins"]
        if len(server_admins):
            for server_admin_id, server_admin in server_admins.items():
                you = ' (you)' if int(server_admin_id) == ctx.author.id else ''
                admins_lst.append(f'- < torn > {server_admin["name"]} [{server_admin["torn_id"]}] < discord > {self.bot.get_user(int(server_admin_id))} [{server_admin_id}]{you}')
        else:
            admins_lst.append('< no admins >\n\nAsk an @Helper for help: https://yata.alwaysdata.net/discord')
        admins_lst.append('```')
        await ctx.send("\n".join(admins_lst))

        if str(ctx.author.id) not in server_admins:
            updates.append("< You need to be a server admin to continue > \n\nAsk an @Helper for help: https://yata.alwaysdata.net/discord")
            updates.append("```")
            await ctx.send("\n".join(updates))
            return

        # create not configuration if need
        if ctx.guild.id not in self.bot.configurations:
            logging.info(f'[admin/update] create bot configuration')
            self.bot.configurations[ctx.guild.id] = {"admin": {}}

        # deep copy of the bot configuration in a temporary variable to check differences
        configuration = dict(self.bot.configurations[ctx.guild.id])

        # get list of channels
        channels = {}
        for channel in ctx.guild.text_channels:
            channels[str(channel.id)] = f'{channel}'

        # get list of roles
        roles = {}
        for role in ctx.guild.roles:
            roles[str(role.id)] = f'{role}'

        # set admin section of the configuration
        if "admin" not in configuration:
            configuration["admin"] = {}
        configuration["admin"]["guild_id"] = ctx.guild.id
        configuration["admin"]["guild_name"] = ctx.guild.name
        configuration["admin"]["owner_did"] = ctx.guild.owner.id
        configuration["admin"]["owner_dname"] = f'{ctx.guild.owner}'
        configuration["admin"]["channels"] = channels
        configuration["admin"]["roles"] = roles
        configuration["admin"]["server_admins"] = server_admins

        # update modules
        for module in ["admin", "rackets", "loot", "revive", "verify", "oc"]:
            # if configuration_db.get("rackets", False) and len(configuration_db["rackets"].get("channels", [])):
            if configuration_db.get(module, False):
                if module not in configuration:
                    updates.append(f"- [{module}](enabled)")
                else:
                    for key, value in configuration_db[module].items():
                        if configuration[module].get(key, {}) != value:
                            updates.append(f"- [{module}]({key})")

                # choose how to sync
                if module in ["rackets", "loot", "revive", "verify", "oc"]:
                    # db erase completely bot config
                    configuration[module] = configuration_db[module]
                elif module in ["admin"]:
                    # db is updated with bot config
                    # except for prefix
                    configuration[module]["prefix"] = configuration_db[module].get("prefix", {'!': '!'})
                    configuration[module]["channels_admin"] = configuration_db[module].get("channels_admin", {'None': 0})
                    pass
                else:
                    updates.append(f"- {module} ignored")

            elif module in configuration and module not in ["admin"]:
                configuration.pop(module)
                updates.append(f"- [{module}](disabled)")


        # push configuration
        print(json.dumps(configuration))
        await set_configuration(self.bot_id, ctx.guild.id, ctx.guild.name, configuration)

        self.bot.configurations[ctx.guild.id] = configuration

        if len(updates) < 3:
            updates.append("< none >")
        updates.append("```")
        await ctx.send("\n".join(updates))

        # print current configurations
        # for module, variables in configuration.items():
        #     for k, v in variables.items():
        #         if isinstance(v, dict):
        #             for a, b in v.items():
        #                 await ctx.send(f'**{module}** {k}: `{html.unescape(b)} [{a}]`')
        #         else:
        #             await ctx.send(f"**{module}**: `{k} = {v}`")

        # await ctx.send(":white_check_mark: configuration updated")

    # @commands.command()
    # @commands.has_any_role(679669933680230430, 669682126203125760)
    # async def reload(self, ctx, *args):
    #     """Admin tool for the bot owner"""
    #     logging.info(f'[admin/reload] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     from includes.yata_db import load_configurations
    #
    #     if ctx.channel.name != "yata-admin":
    #         await ctx.send(":x: Use this command in `#yata-admin`")
    #         return
    #
    #     await ctx.send("```html\n<reload>```")
    #     _, c, a = load_configurations(self.bot.bot_id)
    #     self.bot.configs = json.loads(c)
    #     self.bot.administrators = json.loads(a)
    #     # lst = []
    #     # for i, (k, v) in enumerate(self.bot.administrators.items()):
    #     #     lst.append(f'Administartor {i+1}: Discord {k}, Torn {v}')
    #     # await fmt.send_tt(ctx, lst)
    #
    #     if len(args) and args[0].isdigit():
    #         guild = get(self.bot.guilds, id=int(args[0]))
    #         if guild is not None:
    #             await self.bot.rebuildGuild(guild, verbose=ctx)
    #         else:
    #             await ctx.send(f"```ERROR: guild id {args[0]} bot found```")
    #     else:
    #         await self.bot.rebuildGuilds(verbose=ctx)
    #     await ctx.send("```html\n</reload>```")
    #
    # @commands.command()
    # @commands.has_any_role(679669933680230430, 669682126203125760)
    # async def check(self, ctx):
    #     """Admin tool for the bot owner"""
    #     logging.info(f'[admin/check] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     if ctx.channel.name != "yata-admin":
    #         await ctx.send(":x: Use this command in `#yata-admin`")
    #         return
    #
    #     # loop over guilds
    #     guildIds = []
    #     for guild in self.bot.guilds:
    #         if str(guild.id) in self.bot.configs:
    #             guildIds.append(str(guild.id))
    #             # await ctx.send(f"```Guild {guild} owned by {guild.owner}: ok```")
    #         else:
    #             await ctx.send(f"```Guild {guild} owned by {guild.owner}: no config in the db```")
    #
    #     for k, v in self.bot.configs.items():
    #         if k not in guildIds:
    #             await ctx.send(f'```Guild {v["admin"]["name"]} owned by {v["admin"]["owner"]}: no bot in the guild```')
    #
    # @commands.command()
    # @commands.has_any_role(679669933680230430, 669682126203125760)
    # async def info(self, ctx, *args):
    #     """Admin tool for the bot owner"""
    #     logging.info(f'[admin/info] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     config = self.bot.configs.get(args[0], dict({}))
    #     guild = get(self.bot.guilds, id=int(args[0]))
    #     if len(config):
    #         contact_torn = f'[{config["admin"]["contact_torn"]} [{config["admin"]["contact_torn_id"]}]](https://www.torn.com/profiles.php?XID={config["admin"]["contact_torn_id"]})'
    #         contact_disc = f'{config["admin"]["contact_discord"]} [{config["admin"]["contact_discord_id"]}]'
    #         description = [contact_torn, contact_disc]
    #         embed = Embed(title=f'{guild}', description='\n'.join(description), color=550000)
    #
    #         for module in ["verify", "loot", "revive", "stocks", "rackets", "chain", "crimes", "api", "factions"]:
    #             if module in config:
    #                 value = []
    #
    #                 # get channels
    #                 for txt in [_ for _ in config[module].get("channels", [])]:
    #                     if txt in ["*"]:
    #                         value.append("all channels")
    #                     else:
    #                         gui = get(guild.channels, name=txt)
    #                         value.append(f':x: `#{txt}`' if gui is None else f':white_check_mark: `#{txt}`')
    #
    #                 # get basic roles
    #                 if module == "factions":
    #                     if config.get("verify", dict({})).get("id", False):
    #                         role_list = [f'{html.unescape(name)} [{id}]' for id, name in config[module].items()]
    #                     else:
    #                         role_list = [f'{html.unescape(name)}' for id, name in config[module].items()]
    #                 else:
    #                     role_list = [_ for _ in config[module].get("roles", [])] + [_ for _ in [config[module].get("common")] if _ is not None]
    #
    #                 for txt in role_list:
    #                     if txt in ["*"]:
    #                         value.append("all roles")
    #                     else:
    #                         gui = get(guild.roles, name=txt)
    #                         value.append(f':x: `@{txt}`' if gui is None else f':white_check_mark: `@{txt}`')
    #
    #                 if len(value):
    #                     embed.add_field(name=f'{module.title()}', value="\n".join(value))
    #             else:
    #                 embed.add_field(name=f'{module.title()}', value=f'Disabled')
    #
    #             embed.set_thumbnail(url=guild.icon_url)
    #             embed.set_footer(text=f'Server id {args[0]}')
    #         await ctx.send("", embed=embed)
    #     else:
    #         await ctx.send(f':x: no config corresponding to guild id `{args[0]}`')
    #
    # @commands.command()
    # @commands.has_any_role(679669933680230430, 669682126203125760)
    # async def contact(self, ctx, *args):
    #     """Admin tool for the bot owner"""
    #     logging.info(f'[admin/contact] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     contact_discord_id = int(args[0])
    #     contact_discord = self.bot.get_user(int(args[0]))
    #     if contact_discord is None:
    #         await ctx.send(f':x: User id {contact_discord_id} not found.')
    #         return
    #
    #     guild_found = []
    #     for guild, config in self.bot.configs.items():
    #         if config["admin"].get("contact_discord_id") == contact_discord_id:
    #             guild_found.append([guild, get(self.bot.guilds, id=int(guild))])
    #
    #     if len(guild_found):
    #         await ctx.send(f"List of guild found for user {contact_discord}".format())
    #         await ctx.send("\n".join([f'{b} [{a}]' for a, b in guild_found]))
    #     else:
    #         await ctx.send(f':x: no guild found for user {contact_discord}')
    #
    # @commands.command()
    # @commands.has_any_role(679669933680230430, 669682126203125760)
    # async def invite(self, ctx):
    #     """Admin tool for the bot owner"""
    #     logging.info(f'[admin/invite] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     if ctx.channel.name != "yata-admin":
    #         await ctx.send(":x: Use this command in `#yata-admin`")
    #         return
    #     # await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=469837840)))
    #     await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=8)))
    #
    # @commands.command()
    # @commands.has_any_role(679669933680230430, 669682126203125760)
    # async def talk(self, ctx, *args):
    #     """Admin tool for the bot owner"""
    #     logging.info(f'[admin/talk] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     if ctx.channel.name != "yata-admin":
    #         await ctx.send(":x: Use this command in `#yata-admin`")
    #         return
    #
    #     for k in args:
    #         logging.info("args:", k, is_mention(k, type="channel"))
    #
    #     if len(args) < 2:
    #         await ctx.send(":x: You need to enter a channel and a message```!talk #channel Hello there!```Error: number of arguments = {}".format(len(args)))
    #         return
    #
    #     channel_id = is_mention(args[0], type="channel")
    #     if not channel_id or not channel_id.isdigit():
    #         await ctx.send(":x: You need to enter a channel and a message```!talk #channel Hello there!```Error: channel id = {}".format(channel_id))
    #         return
    #
    #     channel = get(ctx.guild.channels, id=int(channel_id))
    #     if channel is None:
    #         await ctx.send(":x: You need to enter a channel and a message```!talk #channel Hello there!```Error: channel = {}".format(channel))
    #         return
    #
    #     msg = " ".join(args[1:])
    #     await channel.send(msg)
    #     await ctx.send(f"Message send to {channel.mention}```{msg}```")
    #
    # @commands.command()
    # @commands.has_any_role(679669933680230430, 669682126203125760)
    # async def assign(self, ctx, *args):
    #     """Admin tool for the bot owner"""
    #     logging.info(f'[admin/assign] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     if not len(args) or args[0].lower() not in ["host", "yata"]:
    #         logging.info(":x: `!assign host` or `!assign yata`")
    #         return
    #
    #     # Host
    #     if args[0].lower() == "host":
    #         r = get(ctx.guild.roles, name="Host")
    #         if r is None:
    #             await ctx.send(f":x: no role {args[0]}")
    #             return
    #
    #         msg = await ctx.send(f":clock1: Assigning {r}")
    #
    #         # now that we have discord id of contacts it's easier to use that to assign roles
    #
    #         # get all contacts
    #         contacts = []
    #         for k, v in self.bot.configs.items():
    #             contacts.append(v["admin"].get("contact_torn_id", 0))
    #
    #         # loop over member
    #         n = len(ctx.guild.members)
    #         for i, member in enumerate(ctx.guild.members):
    #             match = re.search('\[\d{1,7}\]', member.display_name)
    #             if match is None:
    #                 continue
    #
    #             tornId = int(match.group().replace("[", "").replace("]", ""))
    #             if tornId in contacts and r not in member.roles:
    #                 logging.info(f"[admin/assign] {member.display_name} add {r}")
    #                 await member.add_roles(r)
    #             elif tornId not in contacts and r in member.roles:
    #                 logging.info(f"[admin/assign] {member.display_name} remove {r}")
    #                 await member.remove_roles(r)
    #
    #             progress = int(100 * i / float(n))
    #             if not i % (1 + n // 4):
    #                 await msg.edit(content=f":clock{i%12 + 1}: Assigning {r} `{progress:>3}%`")
    #
    #         await msg.edit(content=f":white_check_mark: Assigning {r} `100%`")
    #
    #         return
    #
    #     if args[0].lower() == "yata":
    #         r = get(ctx.guild.roles, name="Yata")
    #         # loop over member
    #         if r is None:
    #             await ctx.send(f":x: no role {args[0]}")
    #         else:
    #             msg = await ctx.send(f":clock1: Assigning {r}")
    #
    #         n = len(ctx.guild.members)
    #         for i, member in enumerate(ctx.guild.members):
    #             if len(await get_yata_user_by_discord(member.id)) and r not in member.roles:
    #                 logging.info(f"[admin/assign] {member.display_name} add {r}")
    #                 await member.add_roles(r)
    #
    #             elif not len(await get_yata_user_by_discord(member.id)) and r in member.roles:
    #                 logging.info(f"[admin/assign] {member.display_name} remove {r}")
    #                 await member.remove_roles(r)
    #
    #             progress = int(100 * i / float(n))
    #             if not i % (1 + n // 25):
    #                 await msg.edit(content=f":clock{i%12 + 1}: Assigning {r} `{progress:>3}%`")
    #
    #         await msg.edit(content=f":white_check_mark: Assigning {r} `100%`")
    #
    #         return
    #
    # # helper functions
    # async def role_exists(self, ctx, guild, name):
    #     r = get(guild.roles, name=f"{name}")
    #     s = f":white_check_mark: {name} role present" if r is not None else f":x: no {name} role"
    #     await ctx.send(s)
    #
    # async def channel_exists(self, ctx, guild, name):
    #     r = get(guild.channels, name=f"{name}")
    #     s = f":white_check_mark: {name} channel present" if r is not None else f":x: no {name} channel"
    #     await ctx.send(s)
    #
    # @commands.command()
    # @commands.bot_has_permissions(manage_messages=True, send_messages=True, read_message_history=True)
    # @commands.has_permissions(manage_messages=True)
    # @commands.guild_only()
    # async def clear(self, ctx, *args):
    #     """Clear not pinned messages"""
    #     logging.info(f'[admin/clear] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     limit = (int(args[0]) + 1) if (len(args) and args[0].isdigit()) else 100
    #     async for m in ctx.channel.history(limit=limit):
    #         if not m.pinned:
    #             try:
    #                 await m.delete()
    #             except BaseException as e:
    #                 return
    #
    # @commands.command()
    # @commands.bot_has_permissions(manage_messages=True, send_messages=True, read_message_history=True)
    # @commands.has_permissions(manage_messages=True)
    # @commands.guild_only()
    # async def suppress(self, ctx, *args):
    #     """Clear not pinned messages"""
    #     logging.info(f'[admin/suppress] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     await ctx.message.delete()
    #     limit = (int(args[0]) + 1) if (len(args) and args[0].isdigit()) else 100
    #     async for m in ctx.channel.history(limit=limit):
    #         if not m.pinned:
    #             try:
    #                 await m.edit(suppress=True)
    #             except BaseException as e:
    #                 return
    #
    # @commands.command()
    # @commands.bot_has_permissions(send_messages=True, embed_links=True)
    # async def help(self, ctx):
    #     """help command"""
    #     logging.info(f'[admin/help] {ctx.guild}: {ctx.author.nick} / {ctx.author}')
    #
    #     embed = Embed(title="YATA bot help", description="If you need more information, ping an @helper in the YATA server", color=550000)
    #
    #     lst = ["[General information](https://yata.alwaysdata.net/bot/)",
    #            "[List of commands](https://yata.alwaysdata.net/bot/documentation/)",
    #            "[Host the bot](https://yata.alwaysdata.net/bot/host/)"]
    #     embed.add_field(name='About the bot', value='\n'.join(lst))
    #
    #     lst = ["[Official TORN verification](https://discordapp.com/api/oauth2/authorize?client_id=441210177971159041&redirect_uri=https%3A%2F%2Fwww.torn.com%2Fdiscord.php&response_type=code&scope=identify)",
    #            "[YATA discord](https://yata.alwaysdata.net/discord)",
    #            "[YATA website](https://yata.alwaysdata.net/)"]
    #     embed.add_field(name='Links', value='\n'.join(lst))
    #
    #     lst = ["[Forum tutorial](https://www.torn.com/forums.php#/p=threads&f=61&t=16121398)",
    #            "[Loot level timers](https://yata.alwaysdata.net/loot/)",
    #            "[Loot bot](https://discordapp.com/channels/581227228537421825/623906124428476427/629065571207479308)"]
    #     embed.add_field(name='How to loot', value='\n'.join(lst))
    #     await ctx.send("", embed=embed)
    #

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.guild_only()
    async def assign(self, ctx, *args):
        logging.info(f'[admin/assign] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # check argument
        logging.debug(f'[admin/assign] args: {args}')
        modules = ["revive", "rackets", "loot"]
        if len(args) and args[0] in modules:
            module = args[0]
        else:
            await ctx.send(f':x: Modules with self assignement roles: {", ".join(modules)}.')
            return

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, module)
        if not config:
            await ctx.send(f":x: {module} module not activated")
            return

        # # check if channel is allowed
        # allowed = await self.bot.check_channel_allowed(ctx, config)
        # if not allowed:
        #     return

        # get role
        role =  self.bot.get_module_role(ctx.guild.roles, config.get("roles_alerts", {}))

        if role is None:
            # not role
            msg = await ctx.send(":x: No roles has been attributed to the rackets module")

        elif role in ctx.author.roles:
            # remove
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **stop** receiving notifications for {module} (role @{html.unescape(role.name)}).")
        else:
            # assign
            await ctx.author.add_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **start** receiving notifications for {module} (role @{html.unescape(role.name)}).")

        # clean messages
        await asyncio.sleep(5)
        await msg.delete()
        await ctx.message.delete()


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

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

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get
from discord.utils import oauth_url
from discord import Embed

# import bot functions and classes
import includes.formating as fmt
from includes.checks import is_mention
from includes.yata_db import get_yata_user_by_discord


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def reload(self, ctx, *args):
        """Admin tool for the bot owner"""
        from includes.yata_db import load_configurations

        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return
        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return

        await ctx.send("```html\n<reload>```")
        _, c, a = load_configurations(self.bot.bot_id)
        self.bot.configs = json.loads(c)
        self.bot.administrators = json.loads(a)
        lst = []
        for i, (k, v) in enumerate(self.bot.administrators.items()):
            lst.append(f'Administartor {i+1}: Discord {k}, Torn {v}')
        await fmt.send_tt(ctx, lst)

        if len(args) and args[0].isdigit():
            guild = get(self.bot.guilds, id=int(args[0]))
            if guild is not None:
                await self.bot.rebuildGuild(guild, verbose=ctx)
            else:
                await ctx.send(f"```ERROR: guild id {args[0]} bot found```")
        else:
            await self.bot.rebuildGuilds(verbose=ctx)
        await ctx.send("```html\n</reload>```")

    @commands.command()
    async def check(self, ctx):
        """Admin tool for the bot owner"""
        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return
        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return

        # loop over guilds
        guildIds = []
        for guild in self.bot.guilds:
            if str(guild.id) in self.bot.configs:
                guildIds.append(str(guild.id))
                await ctx.send(f"```Guild {guild} owned by {guild.owner}: ok```")
            else:
                await ctx.send(f"```Guild {guild} owned by {guild.owner}: no config in the db```")

        for k, v in self.bot.configs.items():
            if k not in guildIds:
                await ctx.send(f'```Guild {v["admin"]["name"]} owned by {v["admin"]["owner"]}: no bot in the guild```')

    @commands.command()
    async def invite(self, ctx):
        """Admin tool for the bot owner"""
        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return
        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return
        # await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=469837840)))
        await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=8)))

    @commands.command()
    async def talk(self, ctx, *args):
        """Admin tool for the bot owner"""
        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return

        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return

        for k in args:
            print("args:", k, is_mention(k, type="channel"))

        if len(args) < 2:
            await ctx.send(":x: You need to enter a channel and a message```!talk #channel Hello there!```Error: number of arguments = {}".format(len(args)))
            return

        channel_id = is_mention(args[0], type="channel")
        if not channel_id or not channel_id.isdigit():
            await ctx.send(":x: You need to enter a channel and a message```!talk #channel Hello there!```Error: channel id = {}".format(channel_id))
            return

        channel = get(ctx.guild.channels, id=int(channel_id))
        if channel is None:
            await ctx.send(":x: You need to enter a channel and a message```!talk #channel Hello there!```Error: channel = {}".format(channel))
            return

        msg = " ".join(args[1:])
        await channel.send(msg)
        await ctx.send(f"Message send to {channel.mention}```{msg}```")

    @commands.command()
    async def assign(self, ctx, *args):
        """Admin tool for the bot owner"""
        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return
        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return

        if not len(args) or args[0].lower() not in ["host", "yata"]:
            print(":x: `!assign host` or `!assign yata`")
            return

        # Host
        if args[0].lower() == "host":
            r = get(ctx.guild.roles, name="Host")
            if r is None:
                await ctx.send(f":x: no role {args[0]}")
            else:
                await ctx.send(f"assigning {r}")

                # get all contacts
                contacts = []
                for k, v in self.bot.configs.items():
                    contacts.append(v["admin"].get("contact_id", 0))

                # loop over member
                for member in ctx.guild.members:
                    print(f"[BOT HOST BOT ROLE] {member} [{member.id}] -> {member.display_name}")
                    match = re.search('\[\d{1,7}\]', member.display_name)
                    if match is None:
                        continue
                    tornId = int(match.group().replace("[", "").replace("]", ""))
                    if tornId in contacts:
                        await member.add_roles(r)
                    else:
                        await member.remove_roles(r)
                await ctx.send(f"done")

            return

        if args[0].lower() == "yata":
            r = get(ctx.guild.roles, name="Yata")
            # loop over member
            if r is None:
                await ctx.send(f":x: no role {args[0]}")
            else:
                await ctx.send(f"assigning {r}")

                for member in ctx.guild.members:
                    print(f"[YATA ROLE] {member} [{member.id}]")
                    if len(await get_yata_user_by_discord(member.id)):
                        await member.add_roles(r)
                    else:
                        await member.remove_roles(r)

                await ctx.send(f"done")
            return


    # helper functions
    async def role_exists(self, ctx, guild, name):
        r = get(guild.roles, name=f"{name}")
        s = f":white_check_mark: {name} role present" if r is not None else f":x: no {name} role"
        await ctx.send(s)

    async def channel_exists(self, ctx, guild, name):
        r = get(guild.channels, name=f"{name}")
        s = f":white_check_mark: {name} channel present" if r is not None else f":x: no {name} channel"
        await ctx.send(s)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True)
    async def clear(self, ctx, *args):
        """Clear not pinned messages"""
        limit = (int(args[0]) + 1) if (len(args) and args[0].isdigit()) else 100
        async for m in ctx.channel.history(limit=limit):
            if not m.pinned:
                try:
                    await m.delete()
                except BaseException:
                    return

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True)
    async def suppress(self, ctx, *args):
        """Clear not pinned messages"""
        limit = (int(args[0]) + 1) if (len(args) and args[0].isdigit()) else 100
        async for m in ctx.channel.history(limit=limit):
            if not m.pinned:
                try:
                    await m.edit(suppress=True)
                except BaseException:
                    return

    @commands.command()
    async def help(self, ctx):
        """help command"""

        embed = Embed(title="YATA bot help", description="If you need more information, ping an @helper in the YATA server", color=550000)

        lst = ["[General information](https://yata.alwaysdata.net/bot/)",
               "[List of commands](https://yata.alwaysdata.net/bot/documentation/)",
               "[Host the bot](https://yata.alwaysdata.net/bot/host/)"]
        embed.add_field(name='About the bot', value='\n'.join(lst))

        lst = ["[Official TORN verification](https://discordapp.com/api/oauth2/authorize?client_id=441210177971159041&redirect_uri=https%3A%2F%2Fwww.torn.com%2Fdiscord.php&response_type=code&scope=identify)",
               "[YATA discord](https://yata.alwaysdata.net/discord)",
               "[YATA website](https://yata.alwaysdata.net/)"]
        embed.add_field(name='Links', value='\n'.join(lst))

        lst = ["[Forum tutorial](https://www.torn.com/forums.php#/p=threads&f=61&t=16121398)",
               "[Loot level timers](https://yata.alwaysdata.net/loot/)",
               "[Loot bot](https://discordapp.com/channels/581227228537421825/623906124428476427/629065571207479308)"]
        embed.add_field(name='How to loot', value='\n'.join(lst))
        await ctx.send("", embed=embed)

    # @commands.Cog.listener()
    # async def on_command_error(self, ctx, error):
    #     """The event triggered when an error is raised while invoking a command.
    #     ctx   : Context
    #     error : Exception"""
    #
    #     # This prevents any commands with local handlers being handled here in on_command_error.
    #     if hasattr(ctx.command, 'on_error'):
    #         return
    #
    #     print(type(error))
    #     ignored = (commands.CommandNotFound, commands.UserInputError)
    #
    #     # Allows us to check for original exceptions raised and sent to CommandInvokeError.
    #     # If nothing is found. We keep the exception passed to on_command_error.
    #     error = getattr(error, 'original', error)
    #
    #     # Anything in ignored will return and prevent anything happening.
    #     if isinstance(error, ignored):
    #         return
    #
    #     # All other Errors not returned come here... And we can just print the default TraceBack.
    #     print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
    #     traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    #
    #     errorMessage = f"{error}" if re.search('api.torn.com', f'{error}') is None else "API's broken.. #blamched"
    #
    #     lst = ["```YAML",
    #            f"Log:     Command error",
    #            f"Server:  {ctx.guild} [{ctx.guild.id}]",
    #            f"Channel: {ctx.message.channel.name}",
    #            f"Author:  {ctx.message.author.display_name} ({ctx.message.author})",
    #            f"Message: {ctx.message.content}",
    #            f"",
    #            f"{errorMessage}",
    #            f"```"]
    #     await self.bot.sendLogChannel("\n".join(lst))

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

        # classical errors

        # the user is missing permissions
        if isinstance(error, commands.MissingPermissions):
            logging.warning(f'[on_command_error] {error}')
            await self.bot.send_log(error, guild_id=ctx.guild.id, channel_id=ctx.channel.id, ctx=ctx)
            return

        # the bot is missing permissions
        if isinstance(error, commands.BotMissingPermissions):
            logging.warning(f'[on_command_error] {error}')
            await self.bot.send_log(error, guild_id=ctx.guild.id, channel_id=ctx.channel.id, ctx=ctx)
            return

        # bugs or fatal errors

        # headers
        headers = {
                    "guild": ctx.guild,
                    "channel": ctx.channel,
                    "author": ctx.author,
                    "command": ctx.command,
                    "message": ctx.message.content,
                    "error": f'{type(error)}'
                   }
        # traceback
        tb = "\n".join([line[:-2] for line in traceback.format_exception(type(error), error, error.__traceback__)])

        # the user is missing role
        if isinstance(error, commands.MissingRole):
            headers["error"] = 'MissingRole'
            await self.bot.send_log_main(error, headers=headers, traceback=tb)
            logging.error(error)
            return

        if isinstance(error, commands.CommandInvokeError):
            headers["error"] = 'CommandInvokeError'
            logging.error(error)
            await self.bot.send_log_main(error, headers=headers, traceback=tb)
            return

        await self.bot.send_log_main(error, headers=headers, traceback=tb)
        logging.error(error)

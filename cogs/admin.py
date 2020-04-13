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

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get
from discord.utils import oauth_url

# import bot functions and classes
import includes.formating as fmt


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
        if len(args) > 1 and args[0].isdigit():
            member = get(ctx.guild.members, id=int(args[0]))
            if member is None:
                await ctx.send(f":x: Member id `{args[0]}` not known on {ctx.guild}.")
            else:
                await member.send(" ".join(args[1:]))
        else:
            await ctx.send(f":x: You need to enter a discord user id and a message `!talk <userid> Hello there!`")

    @commands.command()
    async def messageHosts(self, ctx, *args):
        """Admin tool for the bot owner"""
        if not len(args):
            await ctx.send(":x: You need an argument")
            return

        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return
        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return

        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                guild = self.bot.get_guild(guild.id)
                if guild is None:
                    continue

                channel = get(guild.channels, name="yata-admin")
                if channel is None:
                    print(f'[sendMessage] {guild}: no yata-admin channel')
                    continue

                lst = [f"**Message send by {ctx.author.nick} ({ctx.author} [{ctx.author.id}]**",
                       f'```',
                       " ".join(args[0:]),
                       f'```']

                await channel.send("\n".join(lst))

            except BaseException as e:
                await self.bot.sendLogChannel(f":x: Could not send message to {guild}: {e}")


    @commands.command()
    async def yata(self, ctx):
        """Admin tool for the bot owner"""
        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return
        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return

        # loop over member
        for member in ctx.guild.members:
            print(f"[YATA ROLE] {member} [{member.id}]")
            status, id, key = await self.bot.get_master_key(ctx.guild)
            if status == -1:
                return
            status, _, _, _ = await self.bot.get_user_key(ctx, member, needPerm=False)
            if status == 0:
                await member.add_roles(get(ctx.guild.roles, name="YATA user"))

    @commands.command()
    async def hosts(self, ctx):
        """Admin tool for the bot owner"""
        if str(ctx.author.id) not in self.bot.administrators:
            await ctx.send(":x: This command is not for you")
            return
        if ctx.channel.name != "yata-admin":
            await ctx.send(":x: Use this command in `#yata-admin`")
            return

        # get all contacts
        contacts = []
        for k, v in self.bot.configs.items():
            contacts.append(v["admin"].get("contact_id", 0))

        r = get(ctx.guild.roles, name=f"Host")
        if r is None:
            print("No @Host")
            return

        # loop over member
        for member in ctx.guild.members:
            print(f"[BOT HOST BOT ROLE] {member} [{member.id}] -> {member.display_name}")
            match = re.search('\[\d{1,7}\]', member.display_name)
            if match is None:
                continue
            tornId = int(match.group().replace("[", "").replace("]", ""))
            if tornId in contacts:
                await ctx.send(f'`@{r}` given to **{member.display_name}**')
                await member.add_roles(r)

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
    async def clear(self, ctx, *args):
        """Clear not pinned messages"""
        limit = (int(args[0]) + 1) if (len(args) and args[0].isdigit()) else 100
        async for m in ctx.channel.history(limit=limit):
            if not m.pinned:
                await m.delete()

    @commands.command()
    async def help(self, ctx):
        """help command"""
        await ctx.send("https://yata.alwaysdata.net/bot/documentation/")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        print(type(error))
        ignored = (commands.CommandNotFound, commands.UserInputError)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        # All other Errors not returned come here... And we can just print the default TraceBack.
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

        errorMessage = f"{error}" if re.search('api.torn.com', f'{error}') is None else "API's broken.. #blamched"

        lst = ["```YAML",
               f"Log:     Command error",
               f"Server:  {ctx.guild} [{ctx.guild.id}]",
               f"Channel: {ctx.message.channel.name}",
               f"Author:  {ctx.message.author.display_name} ({ctx.message.author})",
               f"Message: {ctx.message.content}",
               f"",
               f"{errorMessage}",
               f"```"]
        await self.bot.sendLogChannel("\n".join(lst))

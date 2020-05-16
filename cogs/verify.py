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
import aiohttp
import asyncio
import html
import traceback

# import discord modules
from discord.ext import commands
from discord.abc import PrivateChannel
from discord.utils import get
from discord.ext import tasks

# import bot functions and classes
import includes.checks as checks
# import includes.verify as verify
from includes.yata_db import get_yata_user
import includes.formating as fmt


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dailyVerify.start()
        self.dailyCheck.start()
        self.weeklyVerify.start()
        self.weeklyCheck.start()

    def cog_unload(self):
        self.weeklyVerify.cancel()
        self.weeklyCheck.cancel()
        self.dailyVerify.cancel()
        self.dailyCheck.cancel()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Automatically verify member on join"""
        # return if verify not active
        if not self.bot.check_module(member.guild, "verify"):
            return

        # check if bot
        if member.bot:
            return

        # get key
        status, tornId, key = await self.bot.get_master_key(member.guild)
        if status == -1:
            # await ctx.send(":x: No master key given")
            return

        # verify member when he join
        role = get(member.guild.roles, name="Verified")
        message, success = await self._member(member, role, discordID=member.id, API_KEY=key, context=False)

        # get config
        c = self.bot.get_config(member.guild)
        for chName in c["verify"].get("channels", []):
            ch = get(member.guild.channels, name=chName)
            await ch.send(message)

        # if not Automatically verified send private message
        if not success and c["verify"].get("force", False):
            msg = [f'**Welcome to the {member.guild}\'s discord server {member} o/**']
            msg.append('This server requires that you verify your account in order to identify who you are in Torn.')
            msg.append('There is two ways to do that:')
            msg.append(f'1 - You can go to the official discord server and get verified there: https://torn.com/discord, then come back in the {member.guild} server and type `!verify` in #verify-id.')
            msg.append('Or you can directly use this link if you don\'t want to join the official discord: https://discordapp.com/api/oauth2/authorize?client_id=441210177971159041&redirect_uri=https%3A%2F%2Fwww.torn.com%2Fdiscord.php&response_type=code&scope=identify')
            msg.append('2 - Or you can type **in this channel**: `!verifyKey YOURAPIKEY` *(the api key is 16 random letters that can be found here: https://www.torn.com/preferences.php#tab=api)*')
            msg.append(f'Either way, this process changes your nickname to your Torn name, gives you the {role} role and a role corresponding to your faction and you will have access to the main channels of the server.')
            msg.append(f'If you change your name or faction you can repeat this verification whenever you want.')

            await member.send('\n'.join(msg))

    @commands.command()
    async def verify(self, ctx, *args):
        """Verify member based on discord ID"""
        # check if dm
        if isinstance(ctx.channel, PrivateChannel):
            await ctx.send(f'You have to do this on your server')
            return

        # return if verify not active
        if not self.bot.check_module(ctx.guild, "verify"):
            await ctx.send(":x: Verify module not activated")
            return

        # check role and channel
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "verify")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # get key
        status, tornId, key = await self.bot.get_master_key(ctx.guild)
        if status == -1:
            await ctx.send(":x: No master key given")
            return

        # Get Verified role
        role = get(ctx.guild.roles, name="Verified")
        if len(args) == 1:


            if args[0].isdigit():
                userID = int(args[0])
                message, _ = await self._member(ctx, role, userID=userID, API_KEY=key)

            # check if arg is a mention of a discord user ID
            elif re.match(r'<@!?\d+>', args[0]):
                discordID = re.findall(r'\d+', args[0])
                if len(discordID) and discordID[0].isdigit():
                    message, _ = await self._member(ctx, role, discordID=discordID, API_KEY=key)
                else:
                    message = f":x: could not find discord ID in mention {args[0]}... Either I'm stupid or somthing very wrong is going on."

            else:
                message = ":x: use `!verify tornId` or `!verify @Kivou [2000607]`"

        elif len(args) == 2:
            userID = args[0]
            discordID = args[1]
            message, _ = await self._member(ctx, role, userID=userID, discordID=discordID, API_KEY=key)
        else:
            message, _ = await self._member(ctx, role, API_KEY=key)

        await ctx.send(message)

    @commands.command(aliases=['addkey'])
    async def verifyKey(self, ctx, key):
        """Verify member with API key"""
        if not isinstance(ctx.channel, PrivateChannel):
            await ctx.message.delete()
            await ctx.send(f'{ctx.author.mention}, you have to type your API key in a private chat with me...')
            await ctx.author.send('Type your API key here!')
            return

        url = "https://api.torn.com/user/?selections=profile&key={}".format(key)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                user = await r.json()

        # deal with api error
        if "error" in user:
            await ctx.author.send(f'I\'m sorry but an error occured with your API key `{key}`: *{user["error"]["error"]}*')
            return

        # loop over bot guilds and lookup of the discord user
        for guild in self.bot.guilds:
            # continue if author not in the guild
            if ctx.author not in guild.members:
                continue

            await ctx.author.send(f'Verification for server **{guild}**')

            # return if verify not active
            if not self.bot.check_module(guild, "verify"):
                await ctx.author.send(":x: Verify module not activated")
                continue

            # get verified role
            role = get(guild.roles, name="Verified")

            # get member of server from author id
            member = guild.get_member(ctx.author.id)

            # skip verification if member not part of the guild
            if member is None:
                continue

            # get config
            config = self.bot.get_config(guild)

            # get verify channel and send message
            verify_channel = get(guild.channels, name=config["verify"].get("channels", ["verify-id"])[0])

            # try to modify the nickname
            try:
                nickname = "{} [{}]".format(user["name"], user["player_id"])
                await member.edit(nick=nickname)
                await ctx.author.send(f':white_check_mark: Your name as been changed to {member.display_name}')
            except BaseException:
                await ctx.author.send(f'*I don\'t have the permission to change your nickname.*')
                # continue

            # assign verified role
            try:
                await member.add_roles(role)
                await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {role.name}')
            except BaseException as e:
                await ctx.author.send(f':x: Something went wrong when assigning you the {role.name} role ({e}).')
                continue

            # Set Faction role
            fId = str(user['faction']['faction_id'])
            if fId in config["factions"]:
                faction_name = f'{config["factions"][fId]} [{fId}]' if config["verify"].get("id", False) else f'{config["factions"][fId]}'
            else:
                faction_name = "{faction_name} [{faction_id}]".format(**user["faction"]) if config["verify"].get("id", False) else "{faction_name}".format(**user["faction"])

            faction_role = get(guild.roles, name=faction_name)
            if faction_role is not None:
                # add faction role if role exists
                await member.add_roles(faction_role)
                await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {faction_role}')
                # add a common faction role
                common_role = get(guild.roles, name=config["verify"].get("common"))
                if common_role is not None and str(user['faction']['faction_id']) in config.get("factions"):
                    await member.add_roles(common_role)
                    if verify_channel is not None:
                        await verify_channel.send(f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}** from *{faction_name}* which is part of *{common_role}*. o7")
                    await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {common_role}')
                else:
                    if verify_channel is not None:
                        await verify_channel.send(f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}** from *{faction_name}*. o7")
            else:
                if verify_channel is not None:
                    await verify_channel.send(f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}**. o/")
                await ctx.author.send(f':grey_question: You haven\'t been assigned any faction role. If you think you should, ask the owner of this server if it\'s normal.')

            # final message to member
            await ctx.author.send(f':white_check_mark: All good for me!\n**Welcome to {guild}** o/')

    @commands.command(aliases=["verifyall"])
    async def verifyAll(self, ctx, *args):
        """Verify all members based on discord ID"""

        # return if verify not active
        if not self.bot.check_module(ctx.guild, "verify"):
            await ctx.send(":x: Verify module not activated")
            return

        # check role and channel
        ALLOWED_CHANNELS = ["yata-admin"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        force = True if len(args) and args[0] == "force" else False
        guild = ctx.guild
        channel = ctx.channel

        await self._loop_verify(guild, channel, ctx=ctx, force=force)

    @commands.command(aliases=["checkfactions"])
    async def checkFactions(self, ctx, *args):
        """ Check faction role of members

        """
        # return if verify not active
        if not self.bot.check_module(ctx.guild, "verify"):
            await ctx.send(":x: Verify module not activated")
            return

        # check role and channel
        ALLOWED_CHANNELS = ["yata-admin"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # look at args if we force remove role
        force = True if len(args) and args[0] == "force" else False
        guild = ctx.guild
        channel = ctx.channel

        await self._loop_check(guild, channel, ctx=ctx, force=force)

    async def _member(self, ctx, verified_role, userID=None, discordID=None, API_KEY="", context=True):
        """ Verifies one member
            Returns what the bot should say
        """
        try:

            # WARNING: ctx is most of the time a discord context
            # But when using this function inside on_member_join ctx is a discord member
            # Thus ctx.author will fail in this case

            # WARNING: if discordID corresponds to a userID it will be considered as a user ID

            # cast userID and discordID into int if not none
            discordID = int(discordID) if str(discordID).isdigit() else None
            userID = int(userID) if str(userID).isdigit() else None

            # check userID and discordID > 0 otherwise api call will be on the key owner
            if discordID is not None:
                discordID = None if discordID < 1 else discordID

            if userID is not None:
                userID = None if userID < 1 else userID

            # works for both ctx as a context and as a member
            guild = ctx.guild

            # boolean that check if the member is verifying himself with no id given
            author_verif = userID is None and discordID is None

            # case no userID and no discordID is given (author verify itself)
            if author_verif:
                author = ctx.author
                url = f"https://api.torn.com/user/{author.id}?selections=discord&key={API_KEY}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                if 'error' in req:
                    return ":x: There is a API key problem ({}). It's not your fault... Try later.".format(req['error']['error']), False
                userID = req['discord'].get("userID")
                if userID == '':
                    return f":x: **{author}** you have not been verified because you didn't register to the official Torn discord server: https://www.torn.com/discord", False

            # case discordID is given
            # if discordID is not None and userID is None:  # use this condition to skip API call if userID is given
            if discordID is not None:  # use this condition to force API call to check userID even if it is given
                url = f"https://api.torn.com/user/{discordID}?selections=discord&key={API_KEY}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                if 'error' in req:
                    return ":x: There is a API key problem ({}). It's not your fault... Try again later.".format(req['error']['error']), False
                if req['discord'].get("userID") == '':
                    return f":x: **{guild.get_member(discordID)}** has not been verified because they didn't register to the official Torn discord server: https://www.torn.com/discord", False
                else:
                    userID = int(req['discord'].get("userID"))

            print(f"[VERIFY] verifying userID = {userID}")

            # api call request
            url = f"https://api.torn.com/user/{userID}?selections=profile,discord&key={API_KEY}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # check api error
            if 'error' in req:
                if int(req['error']['code']) == 6:
                    return f":x: Torn ID `{userID}` is not known. Please check again.", False
                else:
                    return ":x: There is a API key problem ({}). It's not your fault... Try again later.".format(req['error']['error']), False

            # check != id shouldn't append or problem in torn API
            dis = req.get("discord")
            if int(dis.get("userID")) != userID:
                return ":x: That's odd... {} != {}.".format(userID, dis.get("userID")), False

            # check if registered in torn discord
            discordID = None if dis.get("discordID") in [''] else int(dis.get("discordID"))
            name = req.get("name", "???")
            nickname = f"{name} [{userID}]"

            if discordID is None:
                # the guy did not log into torn discord
                return f":x: **{nickname}** has not been verified because they didn't register to the official Torn discord server: https://www.torn.com/discord", False

            # the guy already log in torn discord
            if author_verif:
                author = ctx.author
                try:
                    await author.edit(nick=nickname)
                except BaseException:
                    if context:
                        # only send this message if ctx is a context (context=True)
                        await ctx.send(f"*I don't have the permission to change your nickname.*")
                await author.add_roles(verified_role)

                # set YATA role
                yata_role = get(ctx.guild.roles, name="YATA user")
                if yata_role is not None:
                    r = await get_yata_user(userID)
                    if len(r):
                        await author.add_roles(yata_role)

                # Set Faction role
                config = self.bot.get_config(ctx.guild)
                fId = str(req['faction']['faction_id'])
                if fId in config["factions"]:
                    faction_name = f'{config["factions"][fId]} [{fId}]' if config["verify"].get("id", False) else f'{config["factions"][fId]}'
                    faction_role = get(ctx.guild.roles, name=faction_name)
                else:
                    faction_name = ""
                    faction_role = None

                if faction_role is not None:
                    # add faction role if role exists
                    await author.add_roles(faction_role)
                    # add a common faction role
                    common_role = get(ctx.guild.roles, name=config["verify"].get("common"))
                    if common_role is not None and fId in config.get("factions"):
                        await author.add_roles(common_role)
                        return f":white_check_mark: **{author}**, you've been verified and are now known as **{author.mention}** from *{faction_name}* which is part of *{common_role}*. o7", True
                    else:
                        return f":white_check_mark: **{author}**, you've been verified and are now known as **{author.mention}** from *{faction_name}*. o7", True

                else:
                    return f":white_check_mark: **{author}**, you've been verified and are now known as **{author.mention}**. o/", True

            else:
                # loop over all members to check if the id exists
                for member in ctx.guild.members:
                    if int(member.id) == discordID:
                        try:
                            await member.edit(nick=nickname)
                        except BaseException:
                            if context:
                                # only send this message if ctx is a context (context=True)
                                await ctx.send(f"*I don't have the permission to change {member.nick}'s nickname.*")
                        await member.add_roles(verified_role)

                        # set YATA role
                        yata_role = get(ctx.guild.roles, name="YATA user")
                        if yata_role is not None:
                            r = await get_yata_user(userID)
                            if len(r):
                                await member.add_roles(yata_role)

                        # Set Faction role
                        config = self.bot.get_config(ctx.guild)
                        fId = str(req['faction']['faction_id'])
                        if fId in config["factions"]:
                            faction_name = f'{config["factions"][fId]} [{fId}]' if config["verify"].get("id", False) else f'{config["factions"][fId]}'
                            faction_role = get(ctx.guild.roles, name=faction_name)
                        else:
                            faction_name = ""
                            faction_role = None

                        if faction_role is not None:
                            # add faction role if role exists
                            await member.add_roles(faction_role)
                            # add a common faction role
                            common_role = get(ctx.guild.roles, name=config["verify"].get("common"))
                            if common_role is not None and str(req['faction']['faction_id']) in config.get("factions"):
                                await member.add_roles(common_role)
                                return f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}** from *{faction_name}* which is part of *{common_role}*. o7", True
                            else:
                                return f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}** from *{faction_name}*. o7", True
                        else:
                            return f":white_check_mark: **{member}**, has been verified and is now known as **{member.display_name}**. o/", True

                # if no match in this loop it means that the member is not in this server
                return f":x: You're trying to verify **{nickname}** but they didn't join this server... Maybe they are using a different discord account on the official Torn discord server.", False

        except BaseException as e:
            print(f'ERROR _member for {guild} [{guild.id}]: {e}')
            print(f'{traceback.format_exc()}')
            errorMessage = f"{e}" if re.search('api.torn.com', f'{e}') is None else "API's broken.. #blamched"
            return f":x: Error while doing the verification: `{errorMessage}`", False

        return ":x: Weird... I didn't do anything...", False

    async def _loop_verify(self, guild, channel, ctx=False, force=False):

        # get key
        status, tornId, key = await self.bot.get_master_key(guild)
        if status == -1:
            await channel.send(":x: No master key given")
            return

        # Get Verified role
        role = get(guild.roles, name="Verified")

        # loop over members
        members = guild.members
        for i, member in enumerate(members):
            if member.bot:
                # await channel.send(f":x: `{i+1:03d}/{len(members):03d} {member} is a bot`")
                continue

            if force:
                if ctx:
                    message, _ = await self._member(ctx, role, discordID=member.id, API_KEY=key)
                else:
                    message, _ = await self._member(member, role, discordID=member.id, API_KEY=key, context=False)
                msg = ":".join(message.split(":")[2:]).strip()
                emo = message.split(":")[1]

                if not _:
                    await channel.send(f"`{i+1:03d}/{len(members):03d} {member.nick}` {msg}")
                continue

            elif role in member.roles:
                pass
                # if member.nick is None:
                #     await channel.send(f":white_check_mark: `{i+1:03d}/{len(members):03d} {member} already verified but no nickname has been assigned. Current display name: {member.display_name}`.")
                # else:
                #     await channel.send(f":white_check_mark: `{i+1:03d}/{len(members):03d} {member} already verified as {member.nick}`")
            else:
                if ctx:
                    message, _ = await self._member(ctx, role, discordID=member.id, API_KEY=key)
                else:
                    message, _ = await self._member(member, role, discordID=member.id, API_KEY=key, context=False)
                msg = ":".join(message.split(":")[2:]).strip()
                emo = message.split(":")[1]

                await channel.send(f"`{i+1:03d}/{len(members):03d} {member.nick}` {msg}")

    async def _loop_check(self, guild, channel, ctx=False, force=False):

        # Get all members
        members = guild.members

        # loop over factions
        c = self.bot.get_config(guild)
        for faction_id, faction_name in c.get("factions", dict({})).items():

            # Get faction role
            faction_role_name = f'{faction_name} [{faction_id}]' if c['verify'].get('id', False) else f'{faction_name}'
            faction_role = get(guild.roles, name=faction_role_name)
            await channel.send(f'\n**Checking faction {html.unescape(faction_role.name)}**')

            # try to parse Torn faction ID
            # match = re.match(r'(.{1,}) \[(\d{1,7})\]', faction_role.name)
            # if match is not None:
            #     tornFacId = int(faction_role.name.split("[")[-1][:-1])
            # else:
            #     await channel.send(f":x: `{faction_role.name}` does not match `(.{1,}) \[(\d{1,7})\]`")
            #     return

            # api call with members list from torn
            status, tornIdForKey, key = await self.bot.get_master_key(guild)
            if status == -1:
                await channel.send(":x: No master key given")
                continue

            url = f'https://api.torn.com/faction/{faction_id}?selections=basic&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # deal with api error
            if "error" in req:
                await channel.send(f'API key error for master key [{tornIdForKey}]: *{req["error"]["error"]}*')
                return

            members_torn = req.get("members", dict({}))

            # loop over the members with this role
            members_with_role = [m for m in members if faction_role in m.roles]
            for i, m in enumerate(members_with_role):

                # try to parse Torn user ID
                regex = re.findall(r'\[(\d{1,7})\]', m.display_name)
                if len(regex) == 1 and regex[0].isdigit():
                    tornId = int(regex[0])
                else:
                    await channel.send(f"`{i+1:03d}/{len(members_with_role):03d}` **{m.display_name}** could not find torn ID within their display name. So I'm not checking them. :x:")
                    continue

                # check if member still in faction
                if str(tornId) in members_torn:
                    # await channel.send(f":white_check_mark: `{m.display_name} still in {faction_role.name}`")
                    continue
                else:
                    if force:
                        await m.remove_roles(faction_role)
                        common_role = get(guild.roles, name=c["verify"].get("common"))
                        if common_role is None:
                            await channel.send(f"`{i+1:03d}/{len(members_with_role):03d}` **{m.display_name}** not in @{faction_role.name} anymore, role has been removed :x:")
                        else:
                            await m.remove_roles(common_role)
                            await channel.send(f"`{i+1:03d}/{len(members_with_role):03d}` **{m.display_name}** not in @{faction_role.name} anymore, role has been removed along with @{common_role.name} :x:")

                        # verify him again see if he has a new faction on the server
                        vrole = get(guild.roles, name="Verified")
                        if ctx:
                            message, success = await self._member(ctx, vrole, discordID=m.id, API_KEY=key)
                        else:
                            message, success = await self._member(m, vrole, discordID=m.id, API_KEY=key, context=False)
                        await channel.send(message)

                    else:
                        await channel.send(f"`{i+1:03d}/{len(members_with_role):03d}` **{m.display_name}** not in @{faction_role.name} anymore :x:")

        await channel.send(f"Done checking")

    @tasks.loop(hours=24)
    async def dailyVerify(self):
        print("[dailyVerify] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                # ignore servers with no verify
                if not self.bot.check_module(guild, "verify"):
                    continue

                # ignore servers with no option daily check
                config = self.bot.get_config(guild)
                if not config["verify"].get("dailyverify", False):
                    continue

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                print(f"[dailyVerify] verifying all {guild}: start")
                # get channel
                channel = get(guild.channels, name="yata-admin")
                await channel.send("Daily verification of your members: **START**")
                await self._loop_verify(guild, channel, force=True)
                await channel.send("Daily verification of your members: **DONE**")
                print(f"[dailyVerify] verifying all {guild}: end")

            except BaseException as e:
                print(f"[dailyVerify] guild {guild}: verifyAll failed {e}.")

    @tasks.loop(hours=168)
    async def weeklyVerify(self):
        print("[weeklyVerify] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                # ignore servers with no verify
                if not self.bot.check_module(guild, "verify"):
                    continue

                # ignore servers with no option daily check
                config = self.bot.get_config(guild)
                if not config["verify"].get("weeklyverify", False):
                    continue

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                print(f"[weeklyVerify] verifying all {guild}: start")
                # get channel
                channel = get(guild.channels, name="yata-admin")
                await channel.send("Weekly verification of your members: **START**")
                await self._loop_verify(guild, channel, force=True)
                await channel.send("Weekly verification of your members: **DONE**")
                print(f"[weeklyVerify] verifying all {guild}: end")

            except BaseException as e:
                print(f"[weeklyVerify] guild {guild}: verifyAll failed {e}.")

    @tasks.loop(hours=24)
    async def dailyCheck(self):
        print("[dailyCheck] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                # ignore servers with no verify
                if not self.bot.check_module(guild, "verify"):
                    continue

                # ignore servers with no option daily check
                config = self.bot.get_config(guild)
                if not config["verify"].get("dailycheck", False):
                    continue

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                print(f"[dailyCheck] verifying all {guild}: start")
                # get channel
                channel = get(guild.channels, name="yata-admin")
                await channel.send("Daily check of your faction members: **START**")
                await self._loop_check(guild, channel, force=True)
                await channel.send("Daily check of your faction members: **DONE**")
                print(f"[dailyCheck] verifying all {guild}: end")

            except BaseException as e:
                print(f"[dailyCheck] guild {guild}: checkFactions failed {e}.")

    @tasks.loop(hours=168)
    async def weeklyCheck(self):
        print("[weeklyCheck] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                # ignore servers with no verify
                if not self.bot.check_module(guild, "verify"):
                    continue

                # ignore servers with no option daily check
                config = self.bot.get_config(guild)
                if not config["verify"].get("weeklyCheck", False):
                    continue

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                print(f"[weeklyCheck] weeklyCheck all {guild}: start")
                # get channel
                channel = get(guild.channels, name="yata-admin")
                await channel.send("Weekly check of your faction members: **START**")
                await self._loop_check(guild, channel, force=True)
                await channel.send("Weekly check of your faction members: **DONE**")
                print(f"[weeklyCheck] verifying all {guild}: end")

            except BaseException as e:
                print(f"[weeklyCheck] guild {guild}: checkFactions failed {e}.")

    @dailyVerify.before_loop
    async def before_dailyVerify(self):
        print('[dailyVerify] waiting...')
        await self.bot.wait_until_ready()

    @weeklyVerify.before_loop
    async def before_weeklyVerify(self):
        print('[weeklyVerify] waiting...')
        await self.bot.wait_until_ready()

    @dailyCheck.before_loop
    async def before_dailyCheck(self):
        print('[dailyCheck] waiting...')
        await self.bot.wait_until_ready()

    @weeklyCheck.before_loop
    async def before_weeklyCheck(self):
        print('[weeklyCheck] waiting...')
        await self.bot.wait_until_ready()

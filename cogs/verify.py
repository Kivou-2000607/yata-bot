# import standard modules
import re
import aiohttp

# import discord modules
from discord.ext import commands
from discord.abc import PrivateChannel
from discord.utils import get
from discord import Embed

# import bot functions and classes
import includes.checks as checks
# import includes.verify as verify
from includes.yata_db import get_yata_user


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        message, success = await self.member(member, role, discordID=member.id, API_KEY=key)

        # get system channel and send message
        welcome_channel = member.guild.system_channel

        if welcome_channel is None:
            pass
        else:
            # get readme channel
            readme_channel = get(member.guild.channels, name="readme")

            # send welcome messages
            if readme_channel is None:
                await welcome_channel.send(f"Welcome {member.mention}.")
            else:
                await welcome_channel.send(f"Welcome {member.mention}. Have a look at {readme_channel.mention} to see what this server is all about!")
            await welcome_channel.send(message)

        # if not Automatically verified send private message
        c = self.bot.get_config(member.guild)
        if not success and c["verify"].get("force", False):
            msg = [f'**Welcome to the {member.guild}\'s discord server {member} o/**']
            msg.append('This server requires that you verify your account in order to identify who you are in Torn.')
            msg.append('There is two ways to do that:')
            msg.append(f'1 - You can go to the official discord server and get verified there: https://torn.com/discord, then come back in the {member.guild} server and type `!verify` in #verify-id.')
            msg.append('2 - Or you can type **in this channel** `!verifyKey YOURAPIKEY (16 random letters)` *(key cant be found here: https://www.torn.com/preferences.php#tab=api)*')
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
        ALLOWED_CHANNELS = ["verify-id"]
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
            userID = args[0]
            message, _ = await self.member(ctx, role, userID=userID, API_KEY=key)
        elif len(args) == 2:
            userID = args[0]
            discordID = args[1]
            message, _ = await self.member(ctx, role, userID=userID, discordID=discordID, API_KEY=key)
        else:
            message, _ = await self.member(ctx, role, API_KEY=key)

        await ctx.send(message)

    @commands.command()
    async def verifyAll(self, ctx):
        """Verify all members based on discord ID"""
        # check if dm
        if isinstance(ctx.channel, PrivateChannel):
            await ctx.send(f'You have to do this on your server')
            return

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

        # get key
        status, tornId, key = await self.bot.get_master_key(ctx.guild)
        if status == -1:
            await ctx.send(":x: No master key given")
            return

        # Get Verified role
        role = get(ctx.guild.roles, name="Verified")

        # loop over members
        members = ctx.guild.members
        for i, member in enumerate(members):
            if member.bot:
                await ctx.send(f":x: `{i+1:03d}/{len(members):03d} {member} is a bot`")
            elif role in member.roles:
                if member.nick is None:
                    await ctx.send(f":x: `{i+1:03d}/{len(members):03d} {member} as been verified but no nickname has been assigned. Current display name: {member.display_name}`")
                else:
                    await ctx.send(f":white_check_mark: `{i+1:03d}/{len(members):03d} {member} already verified as {member.nick}`")
            else:
                message, _ = await self.member(ctx, role, discordID=member.id, API_KEY=key)
                msg = message.split(":")[2].replace("*", "")
                emo = message.split(":")[1]

                await ctx.send(f":{emo}: `{i+1:03d}/{len(members):03d} {msg}`")

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

            # get system channel and send message
            welcome_channel = guild.system_channel

            # try to modify the nickname
            try:
                nickname = "{} [{}]".format(user["name"], user["player_id"])
                await member.edit(nick=nickname)
                await ctx.author.send(f':white_check_mark: Your name as been changed to {member.display_name}')
            except BaseException:
                await ctx.author.send(f':x: I don\'t have the permission to change your nickname.')
                # continue

            # assign verified role
            try:
                await member.add_roles(role)
                await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {role.name}')
            except BaseException:
                await ctx.author.send(f':x: Something went wrong when assigning you the {role.name} role.')
                continue

            # Set Faction role

            # assign Faction
            faction_name = "{faction_name} [{faction_id}]".format(**user['faction'])
            faction_role = get(guild.roles, name=faction_name)
            config = self.bot.get_config(guild)
            if faction_role is not None:
                # add faction role if role exists
                await member.add_roles(faction_role)
                await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {faction_role}')
                # add a common faction role
                common_role = get(guild.roles, name=config["verify"].get("common"))
                if common_role is not None and str(user['faction']['faction_id']) in config.get("factions"):
                    await member.add_roles(common_role)
                    await welcome_channel.send(f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}** from *{faction_name}* which is part of *{common_role}*. o7")
                    await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {common_role}')
                else:
                    await welcome_channel.send(f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}** from *{faction_name}*. o7")
            else:
                await welcome_channel.send(f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}**. o/")
                await ctx.author.send(f':grey_question: You haven\'t been assigned any faction role. If you think you should, ask the owner of this server if it\'s normal.')

            # final message to member
            await ctx.author.send(f':white_check_mark: All good for me!\n**Welcome to {guild}** o/')

    @commands.command()
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

        # Get all members
        members = ctx.guild.members

        # look at args if we force remove role
        force = True if len(args) and args[0] == "force" else False

        # loop over factions
        c = self.bot.get_config(ctx.guild)
        for faction_id, faction_name in c.get("factions", dict({})).items():

            # Get faction role
            faction_role_name = f'{faction_name} [{faction_id}]'
            faction_role = get(ctx.guild.roles, name=faction_role_name)
            await ctx.send(f'\n**Checking faction {faction_role.name}**')

            # try to parse Torn faction ID
            match = re.match(r'(.{1,}) \[(\d{1,7})\]', faction_role.name)
            if match is not None:
                tornFacId = int(faction_role.name.split("[")[-1][:-1])
            else:
                await ctx.send(f":x: `{faction_role.name}` does not match `(.{1,}) \[(\d{1,7})\]`")
                return

            # api call with members list from torn
            status, tornIdForKey, key = await self.bot.get_master_key(ctx.guild)
            if status == -1:
                await ctx.send(":x: No master key given")
                continue

            url = f'https://api.torn.com/faction/{tornFacId}?selections=basic&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # deal with api error
            if "error" in req:
                await ctx.author.send(f'I\'m sorry but an error occured with your API key `{key}`: *{user["error"]["error"]}*')
                return

            members_torn = req.get("members", dict({}))

            # loop over the members with this role
            members_with_role = [m for m in members if faction_role in m.roles]
            for m in members_with_role:

                # try to parse Torn user ID
                regex = re.findall(r'\[(\d{1,7})\]', m.display_name)
                if len(regex) == 1 and regex[0].isdigit():
                    tornId = int(regex[0])
                else:
                    await ctx.send(f":x: `{m.display_name}` could not find torn ID within their display name. So I'm not checking them.")
                    continue

                # check if member still in faction
                if str(tornId) in members_torn:
                    await ctx.send(f":white_check_mark: `{m.display_name} still in {faction_role.name}`")
                else:
                    if force:
                        await m.remove_roles(faction_role)
                        common_role = get(ctx.guild.roles, name=c["verify"].get("common"))
                        if common_role is None:
                            await ctx.send(f":x: `{m.display_name} not in @{faction_role.name} anymore, role has been removed`")
                        else:
                            await m.remove_roles(common_role)
                            await ctx.send(f":x: `{m.display_name} not in @{faction_role.name} anymore, role has been removed along with @{common_role.name}`")
                    else:
                        await ctx.send(f":x: `{m.display_name} not in @{faction_role.name} anymore`")

        await ctx.send(f"Done checking")

    # @commands.command()
    # async def who(self, ctx, *args):
    #     """Gives verified discord user link"""
    #     # get configuration for guild
    #     c = self.bot.get_config(ctx.guild)
    #
    #     # return if verify not active
    #     if not c.get("verify"):
    #         await ctx.send(":x: Verify module not activated")
    #         return
    #
    #     # check role and channel
    #     ALLOWED_ROLES = ["Verified"]
    #     if await checks.roles(ctx, ALLOWED_ROLES):
    #         pass
    #     else:
    #         return
    #
    #     # init variables
    #     tornId = 0
    #     helpMsg = f":x: You have to mention a discord member `!who @Kivou [2000607]` or enter a Torn ID or `!who 2000607`"
    #
    #     # send error message if no arg (return)
    #     if not len(args):
    #         await ctx.send(helpMsg)
    #         return
    #
    #     # check if arg is int
    #     elif args[0].isdigit():
    #         tornId = int(args[0])
    #
    #     # check if arg is a mention of a discord user ID
    #     elif args[0][:2] == '<@':
    #         discordId = int(args[0][2:-1].replace("!", "").replace("&", ""))
    #         member = ctx.guild.get_member(discordId)
    #
    #         # check if member
    #         if member is None:
    #             await ctx.send(f":x: Couldn't find discord member ID {discordId}")
    #             return
    #
    #         # check if member verified
    #         role = get(member.guild.roles, name=self.verified_role)
    #         if role not in member.roles:
    #             await ctx.send(f":x: {member.display_name} is not verified.")
    #             return
    #
    #         # try to parse Torn ID
    #         match = re.match(r'([a-zA-Z0-9_-]{1,16}) \[(\d{1,7})\]', member.display_name)
    #         if match is not None:
    #             tornId = int(member.display_name.split("[")[-1][:-1])
    #         else:
    #             await ctx.send(f":x: `{member.display_name}` does not match `([a-zA-Z0-9_-]{1,16}) \[(\d{1,7})\]`")
    #             return
    #
    #     # other cases I didn't think of
    #     else:
    #         await ctx.send(helpMsg)
    #         return
    #
    #     # tornId should be a interger corresponding to a torn ID
    #
    #     # Torn API call
    #     url = f'https://api.torn.com/user/{tornId}?selections=profile,personalstats&key={self.bot.API_KEY}'
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url) as r:
    #             r = await r.json()
    #
    #     if 'error' in r:
    #         await ctx.send(f'Error code {r["error"]["code"]}: {r["error"]["error"]}')
    #         await ctx.send(f'https://www.torn.com/profiles.php?XID={tornId}')
    #         return
    #
    #     title = f'**{r.get("name")} [{r.get("player_id")}]** https://www.torn.com/profiles.php?XID={tornId}'
    #     msg = f'{r.get("rank")}  -  level {r.get("level")}  -  {r.get("age")} days old'
    #
    #     embed = Embed(title=title, description=msg, color=550000)
    #
    #     # Status
    #     status = ", ".join([s for s in r.get("status") if s is not ""])
    #     # status = r.get("status")[0]
    #     embed.add_field(name=f'Status', value=f'{status}')
    #
    #     # faction
    #     embed.add_field(name=f'{r["faction"].get("faction_name")} [{r["faction"].get("faction_id")}]', value=f'{r["faction"].get("position")} - {r["faction"].get("days_in_faction")} dif')
    #
    #     # social
    #     embed.add_field(name=f'Friends / enemies / karma', value=f'{r["friends"]} / {r["enemies"]} / {r["karma"]} ({100 * r["karma"] // r["forum_posts"]}%)')
    #
    #     # # Life
    #     # p = 100 * r['life']['current'] // r['life']['maximum']
    #     # i = int(p * 20 / 100)
    #     # embed.add_field(name=f'Life {r["life"]["current"]} / {r["life"]["maximum"]}', value=f'[{"+" * i}{"-" * (20 - i)}]')
    #
    #     embed.set_footer(text=f'Last action {r["last_action"]["relative"]}')
    #
    #     await ctx.send(embed=embed)

    async def member(self, ctx, verified_role, userID=None, discordID=None, API_KEY=""):
        """ Verifies one member
            Returns what the bot should say
        """

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
                return f":x: **{guild.get_member(discordID)}** has not been verified because he didn't register to the official Torn discord server: https://www.torn.com/discord", False
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
            return f":x: **{nickname}** has not been verified because he didn't register to the official Torn discord server: https://www.torn.com/discord", False

        # the guy already log in torn discord
        if author_verif:
            author = ctx.author
            try:
                await author.edit(nick=nickname)
            except BaseException:
                await ctx.send(f":x: **{author}**, I don't have the permission to change your nickname.")
            await author.add_roles(verified_role)

            # set YATA role
            yata_role = get(ctx.guild.roles, name="YATA user")
            if yata_role is not None:
                r = await get_yata_user(userID)
                if len(r):
                    await author.add_roles(yata_role)

            # Set Faction role
            faction_name = "{faction_name} [{faction_id}]".format(**req['faction'])
            faction_role = get(ctx.guild.roles, name=faction_name)
            config = self.bot.get_config(ctx.guild)
            if faction_role is not None:
                # add faction role if role exists
                await author.add_roles(faction_role)
                # add a common faction role
                common_role = get(ctx.guild.roles, name=config["verify"].get("common"))
                print("DEBUG guild", ctx.guild)
                print("DEBUG roles", [r.name for r in ctx.guild.roles])
                print("DEBUG common", common_role)
                if common_role is not None and str(req['faction']['faction_id']) in config.get("factions"):
                    await author.add_roles(common_role)
                    return f":white_check_mark: **{author}**, you've been verified and are now kown as **{author.mention}** from *{faction_name}* which is part of *{common_role}*. o7", True
                else:
                    return f":white_check_mark: **{author}**, you've been verified and are now kown as **{author.mention}** from *{faction_name}*. o7", True

            else:
                return f":white_check_mark: **{author}**, you've been verified and are now kown as **{author.mention}**. o/", True

        else:
            # loop over all members to check if the id exists
            for member in ctx.guild.members:
                if int(member.id) == discordID:
                    try:
                        await member.edit(nick=nickname)
                    except BaseException:
                        await ctx.send(f":x: I don't have the permission to change **{member}**'s nickname.")
                    await member.add_roles(verified_role)

                    # set YATA role
                    yata_role = get(ctx.guild.roles, name="YATA user")
                    if yata_role is not None:
                        r = await get_yata_user(userID)
                        if len(r):
                            await member.add_roles(yata_role)

                    # Set Faction role
                    faction_name = "{faction_name} [{faction_id}]".format(**req['faction'])
                    faction_role = get(ctx.guild.roles, name=faction_name)
                    config = self.bot.get_config(ctx.guild)
                    if faction_role is not None:
                        # add faction role if role exists
                        await member.add_roles(faction_role)
                        # add a common faction role
                        common_role = get(ctx.guild.roles, name=config["verify"].get("common"))
                        print("DEBUG guild", ctx.guild)
                        print("DEBUG roles", [r.name for n in ctx.guild.roles])
                        print("DEBUG common", common_role)
                        if common_role is not None and str(req['faction']['faction_id']) in config.get("factions"):
                            await member.add_roles(common_role)
                            return f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}** from *{faction_name}* which is part of *{common_role}*. o7", True
                        else:
                            return f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}** from *{faction_name}*. o7", True
                    else:
                        return f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}**. o/", True

            # if no match in this loop it means that the member is not in this server
            return f":x: You're trying to verify **{nickname}** but he didn't join this server... Maybe he is using a different discord account on the official Torn discord server.", False

        return ":x: Weird... I didn't do anything...", False

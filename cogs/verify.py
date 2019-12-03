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
import includes.verify as verify


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
        key = self.bot.key(member.guild)

        # verify member when he join
        role = get(member.guild.roles, name="Verified")
        message, success = await verify.member(member, role, discordID=member.id, API_KEY=key)

        # get system channel and send message
        welcome_channel = member.guild.system_channel

        # get readme channel
        readme_channel = get(member.guild.channels, name="readme")

        # send welcome message
        try:
            await welcome_channel.send(f"Welcome {member.mention}. Have a look at {readme_channel.mention} to see what this server is all about!")
        except BaseException:
            await welcome_channel.send(f"Welcome {member.mention}.")

        await welcome_channel.send(message)

        # if not Automatically verified send private message
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
        key = self.bot.key(ctx.guild)

        # Get Verified role
        role = get(ctx.guild.roles, name="Verified")
        if len(args) == 1:
            userID = args[0]
            message, _ = await verify.member(ctx, role, userID=userID, API_KEY=key)
        elif len(args) == 2:
            userID = args[0]
            discordID = args[1]
            message, _ = await verify.member(ctx, role, userID=userID, discordID=discordID, API_KEY=key)
        else:
            message, _ = await verify.member(ctx, role, API_KEY=key)

        await ctx.send(message)

    @commands.command()
    async def verifyAll(self, ctx):
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

        # get key
        key = self.bot.key(ctx.guild)

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
                message, _ = await verify.member(ctx, role, discordID=member.id, API_KEY=key)
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
            if not self.bot.check_module(ctx.guild, "verify"):
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
                continue

            # assign verified role
            try:
                await member.add_roles(role)
                await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {role.name}')
            except BaseException:
                await ctx.author.send(f':x: Something went wrong when assigning you the {role.name} role.')
                continue

            # assign Faction
            faction_name = "{faction_name} [{faction_id}]".format(**user['faction'])
            faction_role = get(guild.roles, name=faction_name)

            # check if role exists in the guild
            if faction_role is None:
                await ctx.author.send(f':grey_question: You haven\'t been assigned any faction role. If you think you should, ask the owner of this server if it\'s normal.')
                await welcome_channel.send(f':white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}**. o/')
            else:
                await member.add_roles(faction_role)
                await ctx.author.send(f':white_check_mark: You\'ve been assigned the role {faction_role}')
                await welcome_channel.send(f':white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}** from **{faction_role}**. o7')

            # final message ti member
            await ctx.author.send(f':white_check_mark: All good for me!\n**Welcome to {guild}** o/')

    @commands.command()
    async def checkFactions(self, ctx):
        """Check faction role of members"""
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

        # loop over factions
        for faction_id, faction_name in c.get("factions", dict({})).items():

            # Get faction role
            faction_role_name = f'{faction_name} [{faction_id}]'
            faction_role = get(ctx.guild.roles, name=faction_role_name)
            await ctx.send(f'\n**Checking faction {faction_role.name}**')

            # try to parse Torn faction ID
            match = re.match(r'(.{1,}) \[(\d{1,7})\]', faction_role.name)
            if match is not None:
                tornId = int(faction_role.name.split("[")[-1][:-1])
            else:
                await ctx.send(f":x: `{faction_role.name}` does not match `(.{1,}) \[(\d{1,7})\]`")
                return

            # api call with members list from torn
            key = self.bot.key(ctx.guild)
            url = f'https://api.torn.com/faction/{tornId}?selections=basic&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # deal with api error
            if "error" in req:
                await ctx.author.send(f'I\'m sorry but an error occured with your API key `{key}`: *{user["error"]["error"]}*')
                return

            members_torn = req.get("members", dict({}))
            # for k, v in members_torn.items():
            #    print(k, v)

            # loop over the members with this role
            members_with_role = [m for m in members if faction_role in m.roles]
            for m in members_with_role:

                # try to parse Torn user ID
                match = re.match(r'([a-zA-Z0-9_-]{1,16}) \[(\d{1,7})\]', m.display_name)
                if match is not None:
                    tornId = int(m.display_name.split("[")[-1][:-1])
                else:
                    await ctx.send(f":x: `{m.display_name}` does not match `([a-zA-Z0-9_-]{1,16}) \[(\d{1,7})\]`")

                # check if member still in faction
                if str(tornId) in members_torn:
                    await ctx.send(f":white_check_mark: `{m.display_name} still in {faction_role.name}`")
                else:
                    await ctx.send(f":x: `{m.display_name} not in {faction_role.name} anymore`")
                    await m.remove_roles(faction_role)

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

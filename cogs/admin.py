# import standard modules
import re
import json
import aiohttp

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get
from discord.utils import oauth_url


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def reload(self, ctx):
        """Admin tool for the bot owner"""
        from includes.yata_db import load_configurations
        from includes.yata_db import push_guild_name
        if ctx.author.id != 227470975317311488:
            await ctx.send(":x: This command is not for you")
            return
        _, c = load_configurations(self.bot.bot_id)
        self.bot.configs = json.loads(c)
        await self.bot.rebuild()
        await ctx.send(":white_check_mark: Reboot done")

    @commands.command()
    async def invite(self, ctx):
        """Admin tool for the bot owner"""
        if ctx.author.id != 227470975317311488:
            await ctx.send(":x: This command is not for you")
            return
        # await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=469837840)))
        await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=8)))

    @commands.command()
    async def yata(self, ctx):
        """Admin tool for the bot owner"""
        if ctx.author.id != 227470975317311488:
            await ctx.send(":x: This command is not for you")
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
        if ctx.author.id != 227470975317311488:
            await ctx.send(":x: This command is not for you")
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
    async def check(self, ctx):
        """Admin tool for the bot owner"""

        if ctx.author.id != 227470975317311488:
            await ctx.send(":x: This command is not for you")
            return

        # loop over guilds
        for guild in self.bot.guilds:
            await ctx.send(f"**Guild {guild} owned by {guild.owner} aka {guild.owner.display_name}**")
            config = self.bot.get_config(guild)

            await ctx.send("*general*")
            # check 0.1: test if config
            s = ":white_check_mark: configuration files" if len(config) else ":x: no configurations"
            await ctx.send(s)

            # check 0.2: test system channel
            s = ":white_check_mark: system channel" if guild.system_channel else ":x: no system channel"
            await ctx.send(s)

            # check 0.3: test readme channel
            await self.channel_exists(ctx, guild, "readme")

            # check 1: loot module
            if self.bot.check_module(guild, "loot"):
                await ctx.send("*loot*")

                # check 1.1: Looter role
                await self.role_exists(ctx, guild, "Looter")

                # check 1.2: #loot and #start-looting
                await self.channel_exists(ctx, guild, "loot")
                await self.channel_exists(ctx, guild, "start-looting")

            # check 2: verify module
            if self.bot.check_module(guild, "verify"):
                await ctx.send("*verify*")

                # check 1.1: Verified role
                await self.role_exists(ctx, guild, "Verified")

                # check 1.2: #verified-id
                await self.channel_exists(ctx, guild, "verify-id")
                for k, v in config.get("factions", dict({})).items():
                    await self.role_exists(ctx, guild, f"{v} [{k}]")

    @commands.command()
    async def banners(self, ctx, *args):
        """Gives missing honor banners or displays banner if id given"""

        # get yata's honor dict
        url = "https://yata.alwaysdata.net/awards/bannersId"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                honorBanners = await r.json()

        # display honor banners
        if len(args):
            for id in args:
                bannerId = honorBanners.get(id)
                if bannerId is None:
                    await ctx.send("Honor **#{}**: *honor not known*".format(id))
                elif int(bannerId) == 0:
                    await ctx.send("Honor **#{}**: *banner not known*".format(id))
                else:
                    await ctx.send("Honor **#{}**: https://awardimages.torn.com/{}.png".format(id, bannerId))

        # display missing banners
        else:
            # get configuration for guild
            status, tornId, key = await self.bot.get_master_key(ctx.guild)
            if status == -1:
                await ctx.send(":x: No master key given")
                return

            # get torn's honor dict
            url = "https://api.torn.com/torn/?selections=honors&key={}".format(key)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    tornHonors = await r.json()

            # handle API error
            if 'error' in tornHonors:
                await ctx.send(f':x: Master key problem: *{tornHonors["error"]["error"]}*')
                return

            # dirtiest way to deal with API error
            tornHonors = tornHonors.get('honors', dict({}))

            # select missing honors
            honors = []
            for k, v in honorBanners.items():
                if int(v) == 0:
                    honor = tornHonors.get(k, dict({}))
                    h = " #{} **{}** *{}*".format(k, honor.get('name', 'API'), honor.get('description', 'ERROR'))
                    honors.append(h)

            message = "Missing banners:\n{}".format("\n".join(honors))

            await ctx.send(message)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx):
        """Clear not pinned messages"""
        async for m in ctx.channel.history():
            if not m.pinned:
                await m.delete()

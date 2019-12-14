# import standard modules
import aiohttp

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx):
        """clear not pinned messages"""

        async for m in ctx.channel.history():
            if not m.pinned:
                await m.delete()

    @commands.command()
    async def banners(self, ctx, *args):
        """Gives missing honor banners or displays banner if id given"""

        # check role and channel
        ALLOWED_CHANNELS = ["honors"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

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
            key = self.bot.key(ctx.guild)

            # get torn's honor dict
            url = "https://api.torn.com/torn/?selections=honors&key={}".format(key)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    tornHonors = await r.json()

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

    # helper functions

    async def role_exists(self, ctx, name):
        r = get(ctx.guild.roles, name=f"{name}")
        s = f":white_check_mark: {name} role present" if r is not None else f":x: no {name} role"
        await ctx.send(s)

    async def channel_exists(self, ctx, name):
        r = get(ctx.guild.channels, name=f"{name}")
        s = f":white_check_mark: {name} channel present" if r is not None else f":x: no {name} channel"
        await ctx.send(s)

    @commands.command()
    async def c(self, ctx):
        """Admin tool for the bot owner"""

        if ctx.author.id != 227470975317311488:
            await ctx.send("This command is not for you")
            return

        # loop over guilds
        for guild in self.bot.guilds:
            await ctx.send(f"**Guild {guild}** owned by {guild.owner} aka {guild.owner.display_name}")
            config = self.bot.get_config(guild)

            # check 0.1: test if config
            s = ":white_check_mark: configuration files" if len(config) else ":x: no configurations"
            await ctx.send(s)

            # check 0.2: test system channel
            s = ":white_check_mark: system channel" if guild.system_channel else ":x: no system channel"
            await ctx.send(s)

            # check 1: loot module
            if self.bot.check_module(guild, "loot"):
                # check 1.1: looter role
                await self.role_exists(ctx, "Looter")

                # check 1.2: #loot and #start-looting
                await self.channel_exists(ctx, "loot")
                await self.channel_exists(ctx, "start-looting")

            # check 2: loot module
            if self.bot.check_module(guild, "loot"):
                # check 1.1: looter role
                await self.role_exists(ctx, "Looter")

                # check 1.2: #loot and #start-looting
                await self.channel_exists(ctx, "loot")
                await self.channel_exists(ctx, "start-looting")



    @commands.command()
    async def invite(self, ctx):
        """invite url"""
        if ctx.author.id != 227470975317311488:
            await ctx.send("This command is not for you")
            return
        await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=469837840)))

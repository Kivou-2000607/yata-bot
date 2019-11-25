# import standard modules
import aiohttp

# import discord modules
from discord.ext import commands

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
            # get torn's honor dict
            url = "https://api.torn.com/torn/?selections=honors&key={}".format(self.bot.API_KEY)
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

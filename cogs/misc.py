# import standard modules
import xkcd
import asyncio
import aiohttp

# import discord modules
from discord.ext import commands

# import bot functions and classes
# import includes.formating as fmt


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def xkcd(self, ctx):
        """gives random xkcd comic"""
        comic = xkcd.getRandomComic()
        await ctx.send(f"**{comic.getTitle()}** {comic.getImageLink()}")
        await asyncio.sleep(15)
        await ctx.send(f"*{comic.getAltText()}*")


    @commands.command()
    async def crimes2(self, ctx):
        """gives latest update on crimes 2.0"""
        await ctx.send("https://yata.alwaysdata.net/static/images/crimes2.gif")


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

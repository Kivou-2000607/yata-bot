# import standard modules
import xkcd

# import discord modules
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def xkcd(self, ctx):
        """gives random xkcd comic"""
        comic = xkcd.getRandomComic()
        message = [f"**{comic.getTitle()}**", comic.getImageLink(), f"*{comic.getAltText()}*"]
        await ctx.send("\n".join(message))

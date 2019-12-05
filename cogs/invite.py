# import discord modules
import discord
from discord.ext import commands
from discord.utils import oauth_url

# import bot functions and classes
import includes.checks as checks


class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def invite(self, ctx):
        """invite url"""
        print(self.bot)
        await ctx.send(oauth_url(self.bot.user.id, discord.Permissions(permissions=469837840)))

# import standard modules
import aiohttp
import json

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt


class Stocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_times(self, ctx, stock=""):

        # options for different stocks
        # [user api selection, stock id, n shares for BB]
        so = {"wssb": ["education", 25, 1000000], "tcb": ["money", 2, 1500000]}

        # return if stocks not active
        if not self.bot.check_module(ctx.guild, "stocks"):
            await ctx.send(":x: Stocks module not activated")
            return [], False

        # check role and channel
        channelName = self.bot.get_config(ctx.guild).get("stocks").get("channel", False)
        ALLOWED_CHANNELS = [channelName] if channelName else [stock]
        ALLOWED_ROLES = [stock]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return [], False

        # list all users
        stockOwners = []
        timeLeft = dict()
        role = get(ctx.guild.roles, name=stock)
        for member in role.members:
            print(f"[{stock.upper()}]: {member.display_name}")

            # get user key from YATA database
            status, id, name, key = await self.bot.get_user_key(ctx, member, needPerm=True)
            if status < 0:
                continue

            # get information from API key
            url = f'https://api.torn.com/user/?selections={so.get(stock)[0]},stocks,discord&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # deal with api error
            if "error" in req:
                await ctx.send(f':x: {member.mention} API key error: *{req["error"].get("error", "?")}*')
                continue

            # get stock owner
            user_stocks = req.get('stocks')
            if user_stocks is not None:
                for k, v in user_stocks.items():
                    if v['stock_id'] == so.get(stock)[1] and v['shares'] >= so.get(stock)[2]:
                        stockOwners.append(name)
                        # print("        stock {}: {}".format(k, v))

            # get time left
            if stock == "tcb":
                timeLeft[name] = req.get('city_bank', dict({})).get("time_left", 0)
            elif stock == "wssb":
                timeLeft[name] = req.get('education_timeleft', 0)

        return timeLeft, stockOwners

    @commands.command()
    async def wssb(self, ctx):
        """Display information for the WSSB sharing group"""
        print("[WSSB]")

        timeLeft, stockOwners = await self.get_times(ctx, stock="wssb")
        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "EDU TIME LEFT", "WSSB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of education time left and WSSB owners:\n```\n{lst}```")

    @commands.command()
    async def tcb(self, ctx):
        """Display information for the TCB sharing group"""
        print("[TCB]")

        timeLeft, stockOwners = await self.get_times(ctx, stock="tcb")
        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "INV TIME LEFT", "TCB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of investment time left and TCB owners:\n```\n{lst}```")

# import standard modules
import asyncio
import aiohttp
import json

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt


class Stocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

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

    # @tasks.loop(seconds=5)
    @tasks.loop(seconds=600)
    async def notify(self):
        print("[STOCK] start task")

        # YATA api
        url = "https://yata.alwaysdata.net/stock/alerts/"
        # req = requests.get(url).json()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # set alerts
        lst = []
        for k, v in req.items():
            alerts = v.get("alerts", dict({}))
            if not len(alerts):
                continue

            if alerts.get("below", False) and alerts.get("forecast", False) and v.get("shares"):
                lst.append(f'{k}: below average and forecast moved from bad to good ({v["shares"]:,.0f} shares at ${v["price"]})')

            # if alerts.get("below", False) and v.get("shares"):
            #     lst.append(f'{k}: below average ({v["shares"]:,.0f} shares at ${v["price"]})')

            # if alerts.get("new", False) and alerts.get("enough", False):
            #     lst.append(f'{k}: new shares available ({v["shares"]:,.0f} shares at ${v["price"]})')

            if alerts.get("injection", False):
                lst.append(f'{k}: new shares have been injected by the system ({v["shares"]:,.0f} shares at ${v["price"]})')

        # create message to send
        if len(lst):
            message = "{}".format("\n".join(lst))
        else:
            return

        # loop over guilds to send alerts
        async for guild in self.bot.fetch_guilds(limit=100):

            # check if module activated
            if not self.bot.check_module(guild, "stocks"):
                print(f"[STOCK] guild {guild}: ignore.")
                continue

            # get full guild (async iterator doesn't return channels)
            guild = self.bot.get_guild(guild.id)

            # get channel
            channel = get(guild.channels, name="wall-street")

            if channel is not None:
                await fmt.send_tt(channel, lst)

    @notify.before_loop
    async def before_notify(self):
        print('[STOCK] waiting...')
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

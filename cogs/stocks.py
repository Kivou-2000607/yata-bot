# import standard modules
import aiohttp
import json

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt
from includes.yata_db import get_member_key


class Stocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def wssb(self, ctx):
        """Display information for the WSSB sharing group."""
        # get configuration for guild
        c = self.bot.get_config(ctx.guild)

        # check role and channel
        ALLOWED_CHANNELS = ["wssb"]
        ALLOWED_ROLES = ["wssb"]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # return if stocks not active
        if not c.get("stocks"):
            await ctx.send(":x: Stocks module not activated")
            return

        # list all users
        stockOwners = []
        timeLeft = dict()
        role = get(ctx.guild.roles, name="wssb")
        for member in role.members:
            print("[WSSB]: {}".format(member.display_name))

            # get id
            tId, name, key = await get_member_key(member)

            if key is not None:
                url = f'https://api.torn.com/user/?selections=education,stocks&key={key}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                # deal with api error
                if "error" in req:
                    await ctx.send(f':x: An error occured with {member.display_name} API key: *{req["error"].get("error", "?")}*')
                    continue

                # get stock owner
                user_stocks = req.get('stocks')
                if user_stocks is not None:
                    for k, v in user_stocks.items():
                        if v['stock_id'] == 25 and v['shares'] == 1000000:
                            stockOwners.append(name)
                            # print("        stock {}: {}".format(k, v))

                # get time left
                timeLeft[name] = req.get('education_timeleft', 0)

            else:
                if tId == -1:
                    await ctx.send(f":x: could not parse {member} torn Id")
                elif tId == -2:
                    await ctx.send(f":x: {member} is not in YATA database")

        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "EDU TIME LEFT", "WSSB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of education time left and WSSB owners:\n```\n{lst}```")


    @commands.command()
    async def tcb(self, ctx):
        """Display information for the WSSB sharing group."""
        # get configuration for guild
        c = self.bot.get_config(ctx.guild)

        # check role and channel
        ALLOWED_CHANNELS = ["tcb"]
        ALLOWED_ROLES = ["tcb"]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # return if stocks not active
        if not c.get("stocks"):
            await ctx.send(":x: Stocks module not activated")
            return

        # list all users
        stockOwners = []
        timeLeft = dict()
        role = get(ctx.guild.roles, name="tcb")
        for member in role.members:
            print("[TCB]: {}".format(member.display_name))

            # get id
            tId, name, key = await get_member_key(member)

            if key is not None:
                url = f'https://api.torn.com/user/?selections=money,stocks&key={key}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                # deal with api error
                if "error" in req:
                    await ctx.send(f':x: An error occured with {member.display_name} API key: *{req["error"].get("error", "?")}*')
                    continue

                # get stock owner
                user_stocks = req.get('stocks')
                if user_stocks is not None:
                    for k, v in user_stocks.items():
                        if v['stock_id'] == 2 and v['shares'] == 1500000:
                            stockOwners.append(name)
                            # print("        stock {}: {}".format(k, v))

                # get time left
                timeLeft[name] = req.get('city_bank', dict({})).get("time_left", 0)

            else:
                if tId == -1:
                    await ctx.send(f":x: could not parse {member} torn Id")
                elif tId == -2:
                    await ctx.send(f":x: {member} is not in YATA database")

        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "INV TIME LEFT", "TCB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of investment time left and TCB owners:\n```\n{lst}```")

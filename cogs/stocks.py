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
            status, tId, name, key = await get_member_key(member=member)

            # if couldn't parse id from name
            if status == -1:
                # print(f"[{stock.upper()}] couldn't get user id, check with discord id")
                status, tornId, name, key = await self.bot.key(ctx.guild)
                if key is None:
                    await self.bot.send_key_error(ctx, status, tornId, name, key)
                    continue

                url = f'https://api.torn.com/user/{member.id}?selections=discord&key={key}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                # user verified on official torn server
                if "discord" in req and req["discord"].get("userID"):
                    tId = int(req["discord"].get("userID"))
                    # get user key from YATA database
                    status, tId, name, key = await get_member_key(tornId=tId)
                    # print(f"[{stock.upper()}] discord id found", tId, name, key)

                # API error
                elif "error" in req:
                    # print(f"[{stock.upper()}] error in api request")
                    await ctx.send(f':x: {member.mention} guild owner API key error *({req["error"].get("error", "?")})*')
                    continue

                # if not registered Torn
                else:
                    # print(f"[{stock.upper()}] member not registered")
                    await ctx.send(f':x: {member.mention} I couldn\'t parse their ID from their nickname and he is not verified on the official Torn discord server. Not much I can do to know who he is.')
                    continue

            # check if member on YATA
            if status == -2:
                await ctx.send(f":x: {member.mention}: Player {tId} is not in YATA database so I can't get their API key")
                continue

            # check if member gave perm to the bot to take API key
            if status == -3:
                await ctx.send(f":x: {member.mention}: {name} [{tId}] has to give permission to use their API key here: https://yata.alwaysdata.net/bot/")
                continue

            # at this point we have a torn Id, a discord id, a name and a key

            # get information from API key
            url = f'https://api.torn.com/user/?selections={so.get(stock)[0]},stocks,discord&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # deal with api error
            if "error" in req:
                await ctx.send(f':x: {member.mention} API key error: *{req["error"].get("error", "?")}*')
                continue

            # check if verified on Torn discord (mandatory for the next security check)
            elif not bool(req["discord"].get("discordID")):
                await ctx.send(f':x: {member.mention} not verified on the Torn discord server. It\'s mandatory for security reasons.')
                continue

            # very important security check if torn discord ID != member discord ID
            # the only reason I can think of this happening is a discord user changing his ID (in the nickname) to try pulling information of another member... Which is very very wrong.
            elif req["discord"].get("discordID") != str(member.id):
                await ctx.send(f':x: {member.mention} looks like nickname ID does not match discord ID. Maybe you\'re using a different account.')

                # send report to me
                my_creator = self.bot.get_user(227470975317311488)
                guild_owner = self.bot.get_user(ctx.guild.owner_id)
                report = [f'Guild name: {ctx.guild}']
                report.append(f'Guild owner: {guild_owner} aka {guild_owner.display_name}')
                report.append(f'Discord member display name: {member.display_name}')
                report.append(f'Discord member name: {member}')
                report.append(f'Discord member id: {member.id}')
                report.append(f'Yata member pulled: {name} [{tId}]')
                report.append(f'Discord id pulled from API: {req["discord"].get("discordID")}')
                await my_creator.send('**ALERT** {} stock function\n```ARM\n{}```'.format(stock.upper(), "\n".join(report)))
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
        """Display information for the WSSB sharing group."""
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
        """Display information for the TCB sharing group."""
        print("[TCB]")

        timeLeft, stockOwners = await self.get_times(ctx, stock="tcb")
        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "INV TIME LEFT", "TCB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of investment time left and TCB owners:\n```\n{lst}```")

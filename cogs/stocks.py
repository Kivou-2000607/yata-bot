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
from includes.yata_db import get_member_key_by_id


class Stocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def wssb(self, ctx):
        """Display information for the WSSB sharing group."""

        # return if stocks not active
        if not self.bot.check_module(ctx.guild, "stocks"):
            await ctx.send(":x: Stocks module not activated")
            return

        # check role and channel
        channelName = self.bot.get_config(ctx.guild).get("stocks").get("channel", False)
        ALLOWED_CHANNELS = [channelName] if channelName else ["wssb"]
        ALLOWED_ROLES = ["wssb"]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # list all users
        stockOwners = []
        timeLeft = dict()
        role = get(ctx.guild.roles, name="wssb")
        for member in role.members:
            print("[WSSB]: {}".format(member.display_name))

            # get user key from YATA database
            tId, name, key = await get_member_key(member)

            # if couldn't parse id from name
            if tId == -1:
                # print("[WSSB] couldn't get use id, check with discord id")
                guildKey = self.bot.key(member.guild)
                url = f'https://api.torn.com/user/{member.id}?selections=discord&key={guildKey}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                # user verified on official torn server
                if "discord" in req and req["discord"].get("userID"):
                    tId = int(req["discord"].get("userID"))
                    # get user key from YATA database
                    tId, name, key = await get_member_key_by_id(tId)
                    # print("[WSSB] discord id found", tId, name, key)

                # API error
                elif "error" in req:
                    # print("[WSSB] error in api request")
                    await ctx.send(f':x: An error occured guild owner API key: *{req["error"].get("error", "?")}*')
                    continue

                # if not registered Torn
                else:
                    # print("[WSSB] member not registered")
                    await ctx.send(f':x: An error occured with {member.display_name}: I couldn\'t parse his ID from his nickname and he is not verified on the official Torn discord server. Not much I can do to know who he is.')
                    continue

            if key is not None:
                url = f'https://api.torn.com/user/?selections=education,stocks,discord&key={key}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                # deal with api error
                if "error" in req:
                    await ctx.send(f':x: An error occured with {member.display_name} API key: *{req["error"].get("error", "?")}*')
                    continue

                # very important security check if torn discord ID == member discord ID
                # the difference can come from a discord user changing is ID to pull information of another member
                elif req["discord"].get("discordID") != str(member.id):
                        await ctx.send(f':x: An error occured with {member.display_name}: it seems to me he changed his nickname id to pull data from another player...')

                        my_creator = self.bot.get_user(227470975317311488)
                        guild_owner = self.bot.get_user(ctx.guild.owner_id)
                        report = [f'Guild name: {ctx.guild}']
                        report.append(f'Guild owner: {guild_owner} aka {guild_owner.display_name}')
                        report.append(f'Discord member display name: {member.display_name}')
                        report.append(f'Discord member name: {member}')
                        report.append(f'Discord member id: {member.id}')
                        report.append(f'Discord id pulled from API: {req["discord"].get("discordID")}')
                        await my_creator.send('**ALERT** WSSB stock function\n```ARM\n{}```'.format("\n".join(report)))
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
                else:
                    await ctx.send(f":x: {member}... don't know what happened with him")

        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "EDU TIME LEFT", "WSSB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of education time left and WSSB owners:\n```\n{lst}```")

    @commands.command()
    async def tcb(self, ctx):
        """Display information for the TCB sharing group."""

        # return if stocks not active
        if not self.bot.check_module(ctx.guild, "stocks"):
            await ctx.send(":x: Stocks module not activated")
            return

        # check role and channel
        channelName = self.bot.get_config(ctx.guild).get("stocks").get("channel", False)
        ALLOWED_CHANNELS = [channelName] if channelName else ["tcb"]
        ALLOWED_ROLES = ["tcb"]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # list all users
        stockOwners = []
        timeLeft = dict()
        role = get(ctx.guild.roles, name="tcb")
        for member in role.members:
            print("[TCB]: {}".format(member.display_name))

            # get user key from YATA database
            tId, name, key = await get_member_key(member)

            # if couldn't parse id from name
            if tId == -1:
                # print("[TCB] couldn't get use id, check with discord id")
                guildKey = self.bot.key(member.guild)
                url = f'https://api.torn.com/user/{member.id}?selections=discord&key={guildKey}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                # user verified on official torn server
                if "discord" in req and req["discord"].get("userID"):
                    tId = int(req["discord"].get("userID"))
                    # get user key from YATA database
                    tId, name, key = await get_member_key_by_id(tId)
                    # print("[TCB] discord id found", tId, name, key)

                # API error
                elif "error" in req:
                    # print("[TCB] error in api request")
                    await ctx.send(f':x: An error occured guild owner API key: *{req["error"].get("error", "?")}*')
                    continue

                # if not registered Torn
                else:
                    # print("[TCB] member not registered")
                    await ctx.send(f':x: An error occured with {member.display_name}: I couldn\'t parse his ID from his nickname and he is not verified on the official Torn discord server. Not much I can do to know who he is.')
                    continue

            if key is not None:
                url = f'https://api.torn.com/user/?selections=money,stocks,discord&key={key}'
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as r:
                        req = await r.json()

                # deal with api error
                if "error" in req:
                    await ctx.send(f':x: An error occured with {member.display_name} API key: *{req["error"].get("error", "?")}*')
                    continue

                # very important security check if torn discord ID == member discord ID
                # the difference can come from a discord user changing is ID to pull information of another member
                elif req["discord"].get("discordID") != str(member.id):
                        await ctx.send(f':x: An error occured with {member.display_name}: it seems to me he changed his nickname id to pull data from another player...')

                        my_creator = self.bot.get_user(227470975317311488)
                        guild_owner = self.bot.get_user(ctx.guild.owner_id)
                        report = [f'Guild name: {ctx.guild}']
                        report.append(f'Guild owner: {guild_owner} aka {guild_owner.display_name}')
                        report.append(f'Discord member display name: {member.display_name}')
                        report.append(f'Discord member name: {member}')
                        report.append(f'Discord member id: {member.id}')
                        report.append(f'Discord id pulled from API: {req["discord"].get("discordID")}')
                        await my_creator.send('**ALERT** TCB stock function\n```ARM\n{}```'.format("\n".join(report)))
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
                else:
                    await ctx.send(f":x: {member}... don't know what happened with him")

        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "INV TIME LEFT", "TCB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of investment time left and TCB owners:\n```\n{lst}```")

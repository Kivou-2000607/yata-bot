"""
Copyright 2020 kivou.2000607@gmail.com

This file is part of yata-bot.

    yata is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    yata is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with yata-bot. If not, see <https://www.gnu.org/licenses/>.
"""

# import standard modules
import asyncio
import aiohttp
import json
import datetime
import re
import logging
# import termplotlib as tpl

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get
from discord import Embed

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt
from inc.handy import *

#
# def plot_stocks(graph):
#     x = []
#     y = []
#     for _, price in graph:
#         x.append(_)
#         y.append(price)
#
#     fig = tpl.figure()
#     # fig.plot(x, y, width=80, height=15)
#     fig.plot(x, y, width=40, height=40)
#     lst = ["```"]
#     fig.save("tmp.png")
#     for l in fig.get_string().split("\n"):
#         lst.append(l)
#     lst.append("```")
#     # lst[-1] = " " * 33 + "14 days prices" + " " * 33
#     return lst

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
        ALLOWED_CHANNELS = [stock]
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
            # logging.debug(f"[stock/{stock.lower()}]: {member.display_name}")

            # get user key from YATA database
            status, id, name, key = await self.bot.get_user_key(ctx, member, needPerm=True)
            if status < 0:
                continue

            # get information from API key
            url = f'https://api.torn.com/user/?selections={so.get(stock)[0]},stocks,discord,timestamp&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # deal with api error
            if "error" in req:
                await ctx.send(f':x: {member.mention} API key error: *{req["error"].get("error", "?")}*')
                continue

            # send pull request to member
            info = 'bank investment' if stock == "tcb" else "education"
            lst = [f'Your **{info} time** has just been pulled.',
                   f'```YAML',
                   f'Command: {stock}',
                   f'Time: {fmt.ts_to_datetime(req["timestamp"], fmt="short")}',
                   f'Server: {ctx.guild} [{ctx.guild.id}]',
                   f'Channel: {ctx.channel}',
                   f'Author: {ctx.author.nick} ({ctx.author} [{ctx.author.id}])```']
            try:
                await member.send("\n".join(lst))
            except BaseException:
                await ctx.send(f":x: DM couldn't be sent to **{member.nick}** (most probably because they disable dms in privacy settings). For security reasons their information will not be shown.")
                continue

            # get stock owner
            user_stocks = req.get('stocks')
            if user_stocks is not None:
                for k, v in user_stocks.items():
                    if v['stock_id'] == so.get(stock)[1] and v['shares'] >= so.get(stock)[2]:
                        stockOwners.append(name)
                        # logging.info("        stock {}: {}".format(k, v))

            # get time left
            if stock == "tcb":
                timeLeft[name] = req.get('city_bank', dict({})).get("time_left", 0)
            elif stock == "wssb":
                timeLeft[name] = req.get('education_timeleft', 0)

        return timeLeft, stockOwners

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_role('wssb')
    async def wssb(self, ctx):
        """Display information for the WSSB sharing group"""
        logging.info(f'[stck/wssb] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        timeLeft, stockOwners = await self.get_times(ctx, stock="wssb")
        if len(timeLeft):
            lst = "{: <15} | {} | {} \n".format("NAME", "EDU TIME LEFT", "WSSB")
            lst += "-" * (len(lst) - 1) + "\n"

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst += "{: <15} | {} |  {}  \n".format(k, fmt.s_to_dhm(v), "x" if k in stockOwners else " ")

            await ctx.send(f"Here you go {ctx.author.display_name}, the list of education time left and WSSB owners:\n```\n{lst}```")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.has_role('tcb')
    async def tcb(self, ctx):
        """Display information for the TCB sharing group"""
        logging.info(f'[stck/tcb] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

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
        logging.debug(f"[stock/notify] start task")

        mentions = []
        try:
            stockInfo = {
                "TCSE": {"id": 0, "name": "Torn City Stock Exchange", "acronym": "TCSE", "director": "None", "benefit": {"requirement": 0, "description": "None"}},
                "TSBC": {"id": 1, "name": "Torn City and Shanghai Banking Corporation", "acronym": "TSBC", "director": "Mr. Gareth Davies", "benefit": {"requirement": 4000000, "description": "Entitled to receive occasional dividends"}},
                "TCB": {"id": 2, "name": "Torn City Investment Banking", "acronym": "TCB", "director": "Mr. Paul Davies", "benefit": {"requirement": 1500000, "description": "Entitled to receive improved interest rates"}},
                "SYS": {"id": 3, "name": "Syscore MFG", "acronym": "SYS", "director": "Mr. Stuart Bridgens", "benefit": {"requirement": 3000000, "description": "Entitled to receive supreme firewall software for you and your company"}},
                "SLAG": {"id": 4, "name": "Society and Legal Authorities Group", "acronym": "SLAG", "director": "Mr. Samuel Washington", "benefit": {"requirement": 1500000, "description": "Entitled to receive business cards from our lawyers"}},
                "IOU": {"id": 5, "name": "Insured On Us", "acronym": "IOU", "director": "Mr. Jordan Blake", "benefit": {"requirement": 3000000, "description": "Entitled to receive occasional dividends"}},
                "GRN": {"id": 6, "name": "Grain", "acronym": "GRN", "director": "Mr. Harry Abbott", "benefit": {"requirement": 500000, "description": "Entitled to receive occasional dividends"}},
                "TCHS": {"id": 7, "name": "Torn City Health Service", "acronym": "TCHS", "director": "Dr. Rick Lewis", "benefit": {"requirement": 150000, "description": "Entitled to receive occasional medical packs"}},
                "YAZ": {"id": 8, "name": "Yazoo", "acronym": "YAZ", "director": "Mr. Godfrey Cadberry", "benefit": {"requirement": 1000000, "description": "Entitled to receive free banner advertisement in the local newspaper"}},
                "TCT": {"id": 9, "name": "The Torn City Times", "acronym": "TCT", "director": "Mr. Micheal Cassinger", "benefit": {"requirement": 125000, "description": "Entitled to receive free personal placements in the newspaper"}},
                "CNC": {"id": 10, "name": "Crude & Co.", "acronym": "CNC", "director": "Mr. Bruce Hunter", "benefit": {"requirement": 5000000, "description": "Entitled to receive oil rig company sales boost"}},
                "MSG": {"id": 11, "name": "Messaging Inc.", "acronym": "MSG", "director": "Mr. Yazukini Chang", "benefit": {"requirement": 300000, "description": "Entitled to receive free advertisement placements in the newspaper"}},
                "TMI": {"id": 12, "name": "TC Music Industries", "acronym": "TMI", "director": "Mr. Benjamin Palmer", "benefit": {"requirement": 6000000, "description": "Entitled to receive occasional dividends"}},
                "TCP": {"id": 13, "name": "TC Media Productions", "acronym": "TCP", "director": "Mr. Richard Button", "benefit": {"requirement": 1000000, "description": "Entitled to receive support for your company (if you are the director) which should result in a 10% bonus to profits"}},
                "IIL": {"id": 14, "name": "I Industries Ltd.", "acronym": "IIL", "director": "Mr. Micheal Ibbs", "benefit": {"requirement": 100000, "description": "Entitled to receive software to improve coding time by 50%"}},
                "FHG": {"id": 15, "name": "Feathery Hotels Group", "acronym": "FHG", "director": "Mr. Jeremy Hedgemaster", "benefit": {"requirement": 2000000, "description": "Entitled to receive occasional coupons to stay in our hotels"}},
                "SYM": {"id": 16, "name": "Symbiotic Ltd.", "acronym": "SYM", "director": "Dr. Daniel Pieczko", "benefit": {"requirement": 500000, "description": "Entitled to receive occasional drug packs"}},
                "LSC": {"id": 17, "name": "Lucky Shots Casino", "acronym": "LSC", "director": "Mr. Martin Wong", "benefit": {"requirement": 100000, "description": "Entitled to receive occasional packs of 100x lottery tickets"}},
                "PRN": {"id": 18, "name": "Performance Ribaldry Network", "acronym": "PRN", "director": "Mr. Dylan 'Dick Ironhammer' Tansey", "benefit": {"requirement": 1500000, "description": "Entitled to receive occasional erotic DVDs"}},
                "EWM": {"id": 19, "name": "Eaglewood Mercenary", "acronym": "EWM", "director": "Mr. Jamie Frere Smith", "benefit": {"requirement": 2000000, "description": "Entitled to receive occasional grenade packs"}},
                "TCM": {"id": 20, "name": "Torn City Motors", "acronym": "TCM", "director": "Mr. George Blanksby", "benefit": {"requirement": 1000000, "description": "Entitled to receive a 25% discount when buying car parts"}},
                "ELBT": {"id": 21, "name": "The Empty Lunchbox Building Traders", "acronym": "ELBT", "director": "Mr. Jack Turner", "benefit": {"requirement": 5000000, "description": "Entitled to receive a 10% discount on all home upgrades (not including staff)"}},
                "HRG": {"id": 22, "name": "Home Retail Group", "acronym": "HRG", "director": "Mr. Owain Hughes", "benefit": {"requirement": 1500000, "description": "Entitled to receive occasional free properties"}},
                "TGP": {"id": 23, "name": "Tell Group Plc.", "acronym": "TGP", "director": "Mr. Jordan Urch", "benefit": {"requirement": 2500000, "description": "Entitled to receive a significant boost in company advertising (if you are the director)"}},
                "WSSB": {"id": 25, "name": "West Side South Bank University", "acronym": "WSSB", "director": "Mrs. Katherine Hamjoint", "benefit": {"requirement": 1000000, "description": "Entitled to receive a 10% time reduction for all newly started courses"}},
                "ISTC": {"id": 26, "name": "International School TC", "acronym": "ISTC", "director": "Miss. Mary Huff", "benefit": {"requirement": 100000, "description": "Entitled to receive free education"}},
                "BAG": {"id": 27, "name": "Big Al's Gun Shop", "acronym": "BAG", "director": "Mr. Jim Chapman", "benefit": {"requirement": 3000000, "description": "Entitled to receive occasional special ammunition packs"}},
                "EVL": {"id": 28, "name": "Evil Ducks Candy Corp", "acronym": "EVL", "director": "Mr. Adam French", "benefit": {"requirement": 1750000, "description": "Entitled to receive occasional happy boosts"}},
                "MCS": {"id": 29, "name": "Mc Smoogle Corp", "acronym": "MCS", "director": "Mr. Gofer Gloop", "benefit": {"requirement": 1750000, "description": "Entitled to receive occasional free meals"}},
                "WLT": {"id": 30, "name": "Wind Lines Travel", "acronym": "WLT", "director": "Sir. Fred Dunce", "benefit": {"requirement": 9000000, "description": "Entitled to receive access to our free private jet"}},
                "TCC": {"id": 31, "name": "Torn City Clothing", "acronym": "TCC", "director": "Mrs. Stella Patrick", "benefit": {"requirement": 350000, "description": "Entitled to receive occasional dividends"}}
                }

            # YATA api
            url = "https://yata.alwaysdata.net/stock/alerts/"
            # req = requests.get(url).json()
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # set alerts
            for k, v in req.items():
                if "graph" in v:
                    del v["graph"]
                alerts = v.get("alerts", dict({}))

                title = False
                # if alerts.get("below", False):
                if alerts.get("below", False) and alerts.get("forecast", False) and v.get("shares"):
                    title = f'{stockInfo[k]["name"]}'
                    description = f'Below average and forecast moved from bad to good'

                # if alerts.get("below", False):
                # if alerts.get("below", False) and v.get("shares"):
                # if alerts.get("new", False) and alerts.get("enough", False):

                if alerts.get("injection", False):
                    title = f'{stockInfo[k]["name"]}'
                    description = f'New shares have been injected by the system'

                if title:
                    # Title and description
                    embed = Embed(title=title, description=f"[{description}](https://www.torn.com/stockexchange.php)")

                    # stock price and shares
                    embed.add_field(name='Code', value=f'{k}')
                    embed.add_field(name='Shares', value=f'{v["shares"]:,.0f}')
                    embed.add_field(name='Share price', value=f'${v["price"]:,.2f}')

                    # Block
                    n = stockInfo[k]["benefit"]["requirement"]
                    price = n * float(v["price"])
                    embed.add_field(name='Block description', value=f'{stockInfo[k]["benefit"]["description"]}')
                    embed.add_field(name='Block requirement', value=f'{n:,.0f} shares')
                    embed.add_field(name='Block Price', value=f'${price:,.0f}')

                    # # graph
                    # lst = plot_stocks(v["graph"])
                    # embed.add_field(name="Prices", value="\n".join(lst))

                    # thumbnail
                    embed.set_thumbnail(url=f'https://yata.alwaysdata.net/static/stocks/{stockInfo[k]["id"]}.png')
                    mentions.append(embed)

            # create message to send
            if not len(mentions):
                logging.debug("[stock/notify] no alerts")
                return

        except BaseException as e:
            logging.error("[stock/notify] error on stock notification (YATA CALL)")
            headers = {"error": "error on stock notification (YATA CALL)"}
            await self.bot.send_log_main(e, headers=headers)
            return

        # loop over guilds to send alerts
        for guild in self.bot.get_guild_module("stocks"):
            try:
                # check if module activated
                config = self.bot.get_config(guild)
                if not config.get("stocks", dict({})).get("alerts", False):
                    # logging.info(f"[stock/notify] guild {guild}: ignore notifications")
                    continue

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)
                role = get(guild.roles, name="Trader")

                # loop over channels and role
                channelName = self.bot.get_allowed_channels(config, "stocks")[0]
                channel = get(guild.channels, name=channelName)
                if channel is not None:
                    s = "" if len(mentions) == 1 else "s"
                    txt = f"{len(mentions)} stock alert{s}!" if role is None else f"{role.mention}, {len(mentions)} stock alert{s}!"
                    await channel.send(txt, embed=mentions[0])
                    for embed in mentions[1:]:
                        await channel.send(embed=embed)

                else:
                    logging.error(f'[stock] {guild} [{guild.id}]: channel not found')
                    await self.bot.send_log("channel not found", guild_id=guild.id)
                    headers = {"guild": guild, "guild_id": guild.id, "error": "error on stock notification", "note": f"No channel {channelName}"}
                    await self.bot.send_log_main("channel not found", headers=headers)

            except BaseException as e:
                logging.error(f'[stock] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on stock notification"}
                await self.bot.send_log_main(e, headers=headers)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, manage_messages=True, manage_roles=True)
    @commands.guild_only()
    async def trader(self, ctx):
        """Add/remove @Trader role"""
        logging.info(f'[stock/trader] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # return if stocks not active
        if not self.bot.check_module(ctx.guild, "stocks"):
            await ctx.send(":x: Loot module not activated")
            return

        # Get Trader role
        role = get(ctx.guild.roles, name="Trader")

        if role in ctx.author.roles:
            # remove Trader
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **stop** receiving notifications for stocks.")
        else:
            # assign Trader
            await ctx.author.add_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **start** receiving notifications for stocks.")

        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()

    @notify.before_loop
    async def before_notify(self):
        logging.debug('[stock/notifications] waiting...')
        await self.bot.wait_until_ready()
        logging.debug('[stock/notifications] start loop')

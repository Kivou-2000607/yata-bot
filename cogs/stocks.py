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
from inc.yata_db import get_data
from inc.yata_db import push_data
from inc.handy import *


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

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "stocks", check_key=f"channels_{stock}")
        if not config:
            return [], None

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config, channel_key=f"channels_{stock}")
        if not allowed:
            return [], None

        # list all users
        stockOwners = []
        timeLeft = dict()
        role = self.bot.get_module_role(ctx.guild.roles, config.get(f"roles_{stock}", {}))
        if role is None:
            await self.bot.send_error_message(ctx, f'No roles attributed to {stock}')
            return [], None

        for member in role.members:
            # get user key from YATA database
            status, id, name, key = await self.bot.get_user_key(ctx, member, needPerm=True)
            if status < 0:
                continue

            # get information from API key
            url = f'https://api.torn.com/user/?selections={so.get(stock)[0]},stocks,discord,timestamp&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    try:
                        req = await r.json()
                    except BaseException:
                        req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

            if not isinstance(req, dict):
                req = {'error': {'error': 'API is talking shit... #blameched', 'code': -1}}

            # deal with api error
            if "error" in req:
                await self.bot.send_error_message(ctx, f'API key error: {req["error"].get("error", "?")}')
                continue

            # send pull request to member
            info = 'bank' if stock == "tcb" else "education"
            url = f'https://yata.alwaysdata.net/static/stocks/{2 if stock == "tcb" else 25}.png'
            description = [
                f'Your **{info}** information has just been pulled',
                f'__Author__: {ctx.author.nick} ({ctx.author} [{ctx.author.id}])',
                f'__Server__: {ctx.guild} [{ctx.guild.id}]',
            ]
            eb = Embed(title=f"Shared {stock.upper()} bonus block", description="\n\n".join(description), color=my_blue)
            eb.set_footer(text=ts_to_datetime(req["timestamp"], fmt="short"))
            eb.set_thumbnail(url=url)
            try:
                await member.send(embed=eb)
            except BaseException:
                await self.bot.send_error_message(ctx, f'DM couldn\'t be sent to {member.nick} (most probably because they disable dms in privacy settings). For security reasons their information will not be shown.')
                continue

            # get stock owner
            user_stocks = req.get('stocks')
            if user_stocks is not None:
                for k, v in user_stocks.items():
                    if v['stock_id'] == so.get(stock)[1] and v['shares'] >= so.get(stock)[2]:
                        stockOwners.append(name)

            # get time left
            if stock == "tcb":
                timeLeft[name] = req.get('city_bank', dict({})).get("time_left", 0)
            elif stock == "wssb":
                timeLeft[name] = req.get('education_timeleft', 0)

        return timeLeft, stockOwners

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def wssb(self, ctx):
        """Display information for the WSSB sharing group"""
        logging.info(f'[stock/wssb] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        timeLeft, stockOwners = await self.get_times(ctx, stock="wssb")
        lst = ["```md"]
        if len(timeLeft):
            # tmp = "{: <15} | {} | {}".format("NAME", "EDU TIME LEFT", "WSSB")
            # lst.append(tmp)
            # lst.append("-" * len(tmp))

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst.append("{: <15} | {} |  {}".format(k, s_to_dhm(v), "x" if k in stockOwners else " "))

            lst.append("```")
            eb = Embed(title="List of investment time left and WSSB owners", description="\n".join(lst), color=my_blue)
            eb.set_thumbnail(url="https://yata.alwaysdata.net/static/stocks/25.png")
            await ctx.send(embed=eb)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def tcb(self, ctx):
        """Display information for the TCB sharing group"""
        logging.info(f'[stock/tcb] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        timeLeft, stockOwners = await self.get_times(ctx, stock="tcb")
        lst = ["```md"]
        if len(timeLeft):
            # tmp = "{: <15} | {} | {}".format("NAME", "INV TIME LEFT", "TCB")
            # lst.append(tmp)
            # lst.append("-" * len(tmp))

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                lst.append("{: <15} | {} |  {}".format(k, s_to_dhm(v), "x" if k in stockOwners else " "))

            lst.append("```")
            eb = Embed(title="List of investment time left and TCB owners", description="\n".join(lst), color=my_blue)
            eb.set_thumbnail(url="https://yata.alwaysdata.net/static/stocks/2.png")
            await ctx.send(embed=eb)


    # @tasks.loop(seconds=5)
    @tasks.loop(seconds=600)
    async def notify(self):
        logging.debug(f"[stock/notify] start task")

        _, mentions_keys_prev = get_data(self.bot.bot_id, "stocks")
        mentions_keys = []
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

                v["key"] = k

                if v in mentions_keys_prev:
                    mentions_keys.append(v)
                    print("skip", k, v)
                    continue

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
                    mentions_keys.append(v)

            await push_data(self.bot.bot_id, ts_now(), mentions_keys, "stocks")

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
        for guild in self.bot.get_guilds_by_module("stocks"):
            # try:
            logging.debug(f"[loot/notifications] {guild}")

            config = self.bot.get_guild_configuration_by_module(guild, "stocks", check_key="channels_alerts")
            if not config:
                continue

            # get role & channel
            role = self.bot.get_module_role(guild.roles, config.get("roles_alerts", {}))
            channel = self.bot.get_module_channel(guild.channels, config.get("channels_alerts", {}))

            if channel is None:
                continue

            s = "" if len(mentions) == 1 else "s"
            txt = f"{len(mentions)} stock alert{s}!" if role is None else f"{role.mention}, {len(mentions)} stock alert{s}!"
            await channel.send(txt, embed=mentions[0])
            for embed in mentions[1:]:
                await channel.send(embed=embed)

            # except BaseException as e:
            #     logging.error(f'[stock] {guild} [{guild.id}]: {hide_key(e)}')
            #     await self.bot.send_log(e, guild_id=guild.id)
            #     headers = {"guild": guild, "guild_id": guild.id, "error": "error on stock notification"}
            #     await self.bot.send_log_main(e, headers=headers)

    @notify.before_loop
    async def before_notify(self):
        await self.bot.wait_until_ready()

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
from inc.handy import *


class Stocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

    async def get_times(self, ctx, stock=""):

        # options for different stocks
        so = {
            "wssb": {
                25: ["wssb", 1000000],
                26: ["istc", 100000],
            },
            "tcb": {
                2: ["tcb", 1500000],
            }
        }

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "stocks", check_key=f"channels_{stock}")
        if not config:
            return [], None

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config, channel_key=f"channels_{stock}")
        if not allowed:
            return [], None

        # list all users
        stockOwners = {}
        timeLeft = dict()
        role = self.bot.get_module_role(ctx.guild.roles, config.get(f"roles_{stock}", {}))
        if role is None:
            await self.bot.send_error_message(ctx, f'No roles attributed to {stock}')
            return [], None

        for member in role.members:
            # get user key from YATA database
            status, _, name, key = await self.bot.get_user_key(ctx, member, needPerm=True)
            if status < 0:
                continue

            # get information from API key
            info = 'money' if stock == "tcb" else "education"
            response, e = await self.bot.api_call("user", "", [info, "stocks", "discord", "timestamp"], key)
            if e and 'error' in response:
                await self.bot.send_error_message(ctx, f'API error for {member.nick}\'s key: {response["error"]["error"]}')
                continue

            # send pull request to member
            url = f'https://yata.yt/media/stocks/{2 if stock == "tcb" else 25}.png'
            description = [
                f'Your **{info}** information has just been pulled',
                f'__Author__: {ctx.author.nick} ({ctx.author} [{ctx.author.id}])',
                f'__Server__: {ctx.guild} [{ctx.guild.id}]',
            ]
            eb = Embed(title=f"Shared {stock.upper()} bonus block", description="\n\n".join(description), color=my_blue)
            eb.set_footer(text=ts_to_datetime(response["timestamp"], fmt="short"))
            eb.set_thumbnail(url=url)
            try:
                await send(member, embed=eb)
            except BaseException:
                await self.bot.send_error_message(ctx, f'DM couldn\'t be sent to {member.nick} (most probably because they disable dms in privacy settings). For security reasons their information will not be shown.')
                continue

            # get stock owner
            if response.get('stocks') is None:
                stockOwners[name] = []
            else:
                stockOwners[name] = list(set([so[stock][s["stock_id"]][0] for s in response.get('stocks', {}).values() if s["stock_id"] in so[stock] and s["shares"] >= so[stock][s["stock_id"]][1]]))
            # get time left
            if stock == "tcb":
                timeLeft[name] = response.get('city_bank', dict({})).get("time_left", 0)
            elif stock == "wssb":
                timeLeft[name] = response.get('education_timeleft', 0)

        return timeLeft, stockOwners

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def wssb(self, ctx):
        """Display information for the WSSB sharing group"""
        logging.info(f'[stocks/wssb] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        timeLeft, stockOwners = await self.get_times(ctx, stock="wssb")
        lst = ["```md"]
        if len(timeLeft):
            # tmp = "{: <15} | {} | {}".format("NAME", "EDU TIME LEFT", "WSSB")
            # lst.append(tmp)
            # lst.append("-" * len(tmp))

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                own = f'{", ".join(stockOwners[k])}' if k in stockOwners else " "
                lst.append(f'{k.replace("_", " "): <15} | {s_to_dhm(v)} |  {own}')

            lst.append("```")
            eb = Embed(title="List of education time left and WSSB/ISTC owners", description="\n".join(lst), color=my_blue)
            eb.set_thumbnail(url="https://yata.yt/media/stocks/25.png")
            await send(ctx, embed=eb)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def tcb(self, ctx):
        """Display information for the TCB sharing group"""
        logging.info(f'[stocks/tcb] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        timeLeft, stockOwners = await self.get_times(ctx, stock="tcb")
        lst = ["```md"]
        if len(timeLeft):
            # tmp = "{: <15} | {} | {}".format("NAME", "INV TIME LEFT", "TCB")
            # lst.append(tmp)
            # lst.append("-" * len(tmp))

            for k, v in sorted(timeLeft.items(), key=lambda x: x[1]):
                own = f'{", ".join(stockOwners[k])}' if k in stockOwners else " "
                lst.append(f'{k.replace("_", " "): <15} | {s_to_dhm(v)} |  {own}')

            lst.append("```")
            eb = Embed(title="List of investment time left and TCB owners", description="\n".join(lst), color=my_blue)
            eb.set_thumbnail(url="https://yata.yt/media/stocks/2.png")
            await send(ctx, embed=eb)


    # @tasks.loop(seconds=5)
    @tasks.loop(seconds=600)
    async def notify(self):
        logging.debug(f"[stocks/alerts] start task")

        _, mentions_keys_prev = self.bot.get_data("stocks")
        mentions_keys_prev = mentions_keys_prev if len(mentions_keys_prev) else []  # make sure it's a list if empty
        for k in mentions_keys_prev:
            logging.debug(f"[stocks/alerts] previous alerts: {k}")
        mentions_keys = []
        mentions = []
        try:
            stockInfo = {
                "0": {"id": 0, "acro": "TCSE", "name": "Torn City Stock Exchange", "acronym": "TCSE", "director": "None", "benefit": {"requirement": 0, "description": "None"}},
                "1": {"id": 1, "acro": "TSBC", "name": "Torn City and Shanghai Banking Corporation", "acronym": "TSBC", "director": "Mr. Gareth Davies", "benefit": {"requirement": 4000000, "description": "Entitled to receive occasional dividends"}},
                "2": {"id": 2, "acro": "TCB", "name": "Torn City Investment Banking", "acronym": "TCB", "director": "Mr. Paul Davies", "benefit": {"requirement": 1500000, "description": "Entitled to receive improved interest rates"}},
                "3": {"id": 3, "acro": "SYS", "name": "Syscore MFG", "acronym": "SYS", "director": "Mr. Stuart Bridgens", "benefit": {"requirement": 3000000, "description": "Entitled to receive supreme firewall software for you and your company"}},
                "4": {"id": 4, "acro": "SLAG", "name": "Society and Legal Authorities Group", "acronym": "SLAG", "director": "Mr. Samuel Washington", "benefit": {"requirement": 1500000, "description": "Entitled to receive business cards from our lawyers"}},
                "5": {"id": 5, "acro": "IOU", "name": "Insured On Us", "acronym": "IOU", "director": "Mr. Jordan Blake", "benefit": {"requirement": 3000000, "description": "Entitled to receive occasional dividends"}},
                "6": {"id": 6, "acro": "GRN", "name": "Grain", "acronym": "GRN", "director": "Mr. Harry Abbott", "benefit": {"requirement": 500000, "description": "Entitled to receive occasional dividends"}},
                "7": {"id": 7, "acro": "TCHS", "name": "Torn City Health Service", "acronym": "TCHS", "director": "Dr. Rick Lewis", "benefit": {"requirement": 150000, "description": "Entitled to receive occasional medical packs"}},
                "8": {"id": 8, "acro": "YAZ", "name": "Yazoo", "acronym": "YAZ", "director": "Mr. Godfrey Cadberry", "benefit": {"requirement": 1000000, "description": "Entitled to receive free banner advertisement in the local newspaper"}},
                "9": {"id": 9, "acro": "TCT", "name": "The Torn City Times", "acronym": "TCT", "director": "Mr. Micheal Cassinger", "benefit": {"requirement": 125000, "description": "Entitled to receive free personal placements in the newspaper"}},
                "10": {"id": 10, "acro": "CNC", "name": "Crude & Co.", "acronym": "CNC", "director": "Mr. Bruce Hunter", "benefit": {"requirement": 5000000, "description": "Entitled to receive oil rig company sales boost"}},
                "11": {"id": 11, "acro": "MSG", "name": "Messaging Inc.", "acronym": "MSG", "director": "Mr. Yazukini Chang", "benefit": {"requirement": 300000, "description": "Entitled to receive free advertisement placements in the newspaper"}},
                "12": {"id": 12, "acro": "TMI", "name": "TC Music Industries", "acronym": "TMI", "director": "Mr. Benjamin Palmer", "benefit": {"requirement": 6000000, "description": "Entitled to receive occasional dividends"}},
                "13": {"id": 13, "acro": "TCP", "name": "TC Media Productions", "acronym": "TCP", "director": "Mr. Richard Button", "benefit": {"requirement": 1000000, "description": "Entitled to receive support for your company (if you are the director) which should result in a 10% bonus to profits"}},
                "14": {"id": 14, "acro": "IIL", "name": "I Industries Ltd.", "acronym": "IIL", "director": "Mr. Micheal Ibbs", "benefit": {"requirement": 100000, "description": "Entitled to receive software to improve coding time by 50%"}},
                "15": {"id": 15, "acro": "FHG", "name": "Feathery Hotels Group", "acronym": "FHG", "director": "Mr. Jeremy Hedgemaster", "benefit": {"requirement": 2000000, "description": "Entitled to receive occasional coupons to stay in our hotels"}},
                "16": {"id": 16, "acro": "SYM", "name": "Symbiotic Ltd.", "acronym": "SYM", "director": "Dr. Daniel Pieczko", "benefit": {"requirement": 500000, "description": "Entitled to receive occasional drug packs"}},
                "17": {"id": 17, "acro": "LSC", "name": "Lucky Shots Casino", "acronym": "LSC", "director": "Mr. Martin Wong", "benefit": {"requirement": 100000, "description": "Entitled to receive occasional packs of 100x lottery tickets"}},
                "18": {"id": 18, "acro": "PRN", "name": "Performance Ribaldry Network", "acronym": "PRN", "director": "Mr. Dylan 'Dick Ironhammer' Tansey", "benefit": {"requirement": 1500000, "description": "Entitled to receive occasional erotic DVDs"}},
                "19": {"id": 19, "acro": "EWM", "name": "Eaglewood Mercenary", "acronym": "EWM", "director": "Mr. Jamie Frere Smith", "benefit": {"requirement": 2000000, "description": "Entitled to receive occasional grenade packs"}},
                "20": {"id": 20, "acro": "TCM", "name": "Torn City Motors", "acronym": "TCM", "director": "Mr. George Blanksby", "benefit": {"requirement": 1000000, "description": "Entitled to receive a 25% discount when buying car parts"}},
                "21": {"id": 21, "acro": "ELBT", "name": "The Empty Lunchbox Building Traders", "acronym": "ELBT", "director": "Mr. Jack Turner", "benefit": {"requirement": 5000000, "description": "Entitled to receive a 10% discount on all home upgrades (not including staff)"}},
                "22": {"id": 22, "acro": "HRG", "name": "Home Retail Group", "acronym": "HRG", "director": "Mr. Owain Hughes", "benefit": {"requirement": 1500000, "description": "Entitled to receive occasional free properties"}},
                "23": {"id": 23, "acro": "TGP", "name": "Tell Group Plc.", "acronym": "TGP", "director": "Mr. Jordan Urch", "benefit": {"requirement": 2500000, "description": "Entitled to receive a significant boost in company advertising (if you are the director)"}},
                "25": {"id": 25, "acro": "WSSB", "name": "West Side South Bank University", "acronym": "WSSB", "director": "Mrs. Katherine Hamjoint", "benefit": {"requirement": 1000000, "description": "Entitled to receive a 10% time reduction for all newly started courses"}},
                "26": {"id": 26, "acro": "ISTC", "name": "International School TC", "acronym": "ISTC", "director": "Miss. Mary Huff", "benefit": {"requirement": 100000, "description": "Entitled to receive free education"}},
                "27": {"id": 27, "acro": "BAG", "name": "Big Al's Gun Shop", "acronym": "BAG", "director": "Mr. Jim Chapman", "benefit": {"requirement": 3000000, "description": "Entitled to receive occasional special ammunition packs"}},
                "28": {"id": 28, "acro": "EVL", "name": "Evil Ducks Candy Corp", "acronym": "EVL", "director": "Mr. Adam French", "benefit": {"requirement": 1750000, "description": "Entitled to receive occasional happy boosts"}},
                "29": {"id": 29, "acro": "MCS", "name": "Mc Smoogle Corp", "acronym": "MCS", "director": "Mr. Gofer Gloop", "benefit": {"requirement": 1750000, "description": "Entitled to receive occasional free meals"}},
                "30": {"id": 30, "acro": "WLT", "name": "Wind Lines Travel", "acronym": "WLT", "director": "Sir. Fred Dunce", "benefit": {"requirement": 9000000, "description": "Entitled to receive access to our free private jet"}},
                "31": {"id": 31, "acro": "TCC", "name": "Torn City Clothing", "acronym": "TCC", "director": "Mrs. Stella Patrick", "benefit": {"requirement": 350000, "description": "Entitled to receive occasional dividends"}},
                "42": {"id": 42, "acro": "BUG", "name": "DEBUG", "benefit": {"requirement": 69, "description": "Entitled to a nice debug"}}
                }

            # YATA api
            # url = "http://127.0.0.1:8000/api/v1/stocks/alerts/?debug=true"
            url = "https://yata.yt/api/v1/stocks/alerts/"
            # req = requests.get(url).json()
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # set alerts
            for k, v in req.items():
                logging.debug(f"[stocks/alerts] {k}: {v}")

                v["id"] = k  # needed for unique key
                if v in mentions_keys_prev and k != "42":
                    mentions_keys.append(v)
                    logging.debug(f"[stocks/alerts] skip {k}: {v}")
                    continue

                alerts = v.get("alerts", dict({}))

                title = False
                if k == "42":
                    title = f'{stockInfo[k]["name"]}'
                    description = f'Debug alert'

                if alerts.get("below", False) and alerts.get("forecast", False) and v.get("shares"):
                    title = f'{stockInfo[k]["name"]}'
                    description = f'Below average and forecast moved from bad to good'

                if alerts.get("injection", False):
                    title = f'{stockInfo[k]["name"]}'
                    description = f'New shares have been injected by the system'

                if title:
                    # Title and description
                    embed = Embed(title=title, description=f"[{description}](https://www.torn.com/stockexchange.php)")

                    # stock price and shares
                    # embed.add_field(name='Code', value=f'{k}')
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
                    embed.set_thumbnail(url=f'https://yata.yt/media/stocks/{stockInfo[k]["id"]}.png')
                    mentions.append(embed)
                    if k != "42":
                        mentions_keys.append(v)

            await self.bot.push_data(ts_now(), mentions_keys, "stocks")

            # create message to send
            if not len(mentions):
                logging.debug("[stocks/alerts] no alerts")
                return

        except BaseException as e:
            logging.error("[stocks/alerts] error on stock notification (YATA CALL)")
            headers = {"error": "error on stock notification (YATA CALL)"}
            await self.bot.send_log_main(e, headers=headers)
            return

        # loop over guilds to send alerts
        for guild in self.bot.get_guilds_by_module("stocks"):
            try:
                logging.debug(f"[stocks/alerts] {guild}")

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
                await send(channel, txt, embed=mentions[0])
                for embed in mentions[1:]:
                    await send(channel, embed=embed)

            except BaseException as e:
                logging.error(f"[stocks/alerts] {guild} [{guild.id}]: {hide_key(e)}")
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on stock notification"}
                await self.bot.send_log_main(e, headers=headers)

    @notify.before_loop
    async def before_notify(self):
        await self.bot.wait_until_ready()

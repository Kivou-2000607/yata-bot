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
import pytz
import re
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import StrMethodFormatter
from matplotlib.colors import to_rgba

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get
from discord import Embed
from discord import File

# import bot functions and classes
from inc.handy import *

def dols(amount, n=0):
    return f'({"-" if amount < 0 else "+"}) ${abs(round(amount, n)):,}'

def dol(amount, n=0):
    if n:
        return f'${round(amount, n):,}'
    else:
        return f'${int(round(amount, n)):,}'

class Stocks(commands.Cog):
    def __init__(self, bot, stocks_history):
        self.bot = bot
        self.stocks_history = stocks_history
        self.stocks_status = {}
        self.stocks_acronym_to_id = {}
        self.stocks_id_to_acronym = {}
        self.stocks_generic_alerts = {}
        self.update_data.start()
        self.generic_alerts.start()
        self.personal_alerts.start()


    def cog_unload(self):
        self.update_data.cancel()
        self.generic_alerts.cancel()
        self.personal_alerts.cancel()

    def uds(self, fl, margin=0):
        """returns up/down/still emoji based on floaf fl"""
        if fl - abs(margin) > 0:
            # return self.emo_up
            return ""
        elif fl + abs(margin) < 0:
            # return self.emo_down
            return ""
        else:
            # return self.emo_still
            return ""

    async def _send_server_alerts(self, guild):
        """sends current alerts to a guild"""

        try:
            config = self.bot.get_guild_configuration_by_module(guild, "stocks")
            if not config:
                return

            role = self.bot.get_module_role(guild.roles, config.get("roles_alerts", {}))
            channel = self.bot.get_module_channel(guild.channels, config.get("channels_alerts", {}))

            if channel is None:
                return

            # loop over the alerts
            for alert_key, alert in self.stocks_generic_alerts.items():

                # check if alert already sent
                if guild.id in alert["sent"]:
                    continue

                acronym = get(guild.roles, name=alert.get("acronym"))

                content = alert["content"]
                if role:
                    content += f' {role.mention}'
                if acronym:
                    content += f' {acronym.mention}'
                if guild.id in [356137641814786052, 650701692853288991]:
                    await send(channel, content, file=alert["file"], embed=alert["embed"])
                else:
                    await send(channel, content, embed=alert["embed"])

                # append guild id to alert to send it only once
                alert["sent"].append(guild.id)


        except BaseException as e:
            logging.error(f"[stocks/generic_alerts] {guild} [{guild.id}]: {hide_key(e)}")
            await self.bot.send_log(e, guild_id=guild.id)
            headers = {"guild": guild, "guild_id": guild.id, "error": "error on stock generic_alerts"}
            await self.bot.send_log_main(e, headers=headers)

    def _fill_stocks_embed(self, embed, stock_id, stocks_data):
        # create embed

        embed.add_field(name='Current price', value=f'{dol(stocks_data["current_price"], 2)}')
        embed.add_field(name='Market cap', value=f'{dol(stocks_data["market_cap"]/1e9, 2)} b')
        embed.add_field(name='Shares', value=f'{stocks_data["total_shares"]/1e9:,.2f} b')

        embed.add_field(name=f'{self.uds(stocks_data["tendency_l_a"], 0.05)} Live price', value=f'{dols(stocks_data["tendency_l_a"], 2)}/h')
        embed.add_field(name=f'{self.uds(stocks_data["tendency_h_a"], 0.05)} Hour price', value=f'{dols(stocks_data["tendency_h_a"], 2)}/h')
        embed.add_field(name=f'{self.uds(stocks_data["tendency_d_a"], 0.05)} Day price', value=f'{dols(stocks_data["tendency_d_a"], 2)}/h')

        embed.add_field(name=f'{self.uds(stocks_data["tendency_l_c"], 0.05)} Live cap', value=f'{dols(stocks_data["tendency_l_c"]/1e9, 2)} b/h')
        embed.add_field(name=f'{self.uds(stocks_data["tendency_h_c"], 0.05)} Hour cap', value=f'{dols(stocks_data["tendency_h_c"]/1e9, 2)} b/h')
        embed.add_field(name=f'{self.uds(stocks_data["tendency_d_c"], 0.05)} Day cap', value=f'{dols(stocks_data["tendency_d_c"]/1e9, 2)} b/h')

        embed.set_footer(text=f'Last update: {ts_format(stocks_data["timestamp"], fmt="short")}')
        embed.timestamp = datetime.datetime.fromtimestamp(stocks_data["timestamp"], tz=pytz.UTC)

        embed.set_thumbnail(url=f'https://yata.yt/media/stocks/{stock_id}.png')

        data = [_ for _ in self.stocks_history[stock_id] if (int(time.time()) - _["timestamp"]) < (3600 * 24)]
        x = [datetime.datetime.fromtimestamp(int(_["timestamp"])) for _ in data]
        y1 = [float(_["current_price"]) for _ in data]
        y2 = [int(_["total_shares"] / 1e6) for _ in data]

        plt.style.use('dark_background')
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.plot(x, y1, zorder=1)
        ax2.plot(x, y2, zorder=2, linewidth=1, color='g', linestyle="--")
        ax1.grid(linewidth=1, alpha=0.1)

        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Hh'))
        ax1.yaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'))
        ax2.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))

        ax1.set_ylabel("Current price")
        ax2.set_ylabel("Total shares (b)")

        fig.tight_layout()
        fig.savefig(f'tmp/stocks-generic-alerts-{stock_id}.png', dpi=420, bbox_inches='tight', transparent=True)
        plt.close()
        file = File(f'tmp/stocks-generic-alerts-{stock_id}.png', filename=f'stocks-generic-alerts-{stock_id}.png')
        embed.set_image(url=f'attachment://stocks-generic-alerts-{stock_id}.png')

        embed.set_footer(text=f'Last update: {ts_format(stocks_data["timestamp"], fmt="short")}')
        embed.timestamp = datetime.datetime.fromtimestamp(stocks_data["timestamp"], tz=pytz.UTC)

        return embed, file


    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def alert(self, ctx, *args):
        logging.info(f'[stocks/alert] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "stocks")
        if not config:
            return

        if "personal_alerts" not in config:
            config["personal_alerts"] = {}
            for stock_id in self.stocks_status:
                config["personal_alerts"][stock_id] = {}

        # # check if channel is allowed
        # allowed = await self.bot.check_channel_allowed(ctx, config)
        # if not allowed:
        #     return

        doc = "\n".join([
            "Wrong arguments for this command",
            "`!alert THS 300 300.5 301 302 303` (sets limits to those #s for THS)",
            "`!alert THS off` (clears alert from THS stock)",
            "`!alert off` (clears all alerts from all stocks)"
            "`!alert list` (list all your current alerts)"
            ])

        # analyse arguments: no arguments
        if not len(args):
            await self.bot.send_error_message(ctx.channel, doc, title="Stocks personal alerts error")
            return

        # analyse arguments: !alert off
        if args[0] == "off":
            stocks_removed = []
            for stock_id, members in config["personal_alerts"].items():
                if str(ctx.author.id) in members:
                    stocks_removed.append(self.stocks_status.get(stock_id, {}).get("acronym"))
                    del self.bot.configurations[ctx.guild.id]["stocks"]["personal_alerts"][stock_id][str(ctx.author.id)]

            await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            embed = Embed(
                title="Stocks personal alerts",
                description=f'{ctx.author.mention}: All stocks alerts removed ({", ".join(stocks_removed)}).',
                url=f'https://www.torn.com/page.php?sid=stocks',
                color=my_blue
            )
            await send(ctx.channel, embed=embed)
            return

        if args[0] == "list":
            alerts_listed = {}
            for stock_id, members in config["personal_alerts"].items():
                if str(ctx.author.id) in members:
                    alerts_listed[self.stocks_id_to_acronym[stock_id]] = ", ".join([f'${_:.1f}' for _ in members[str(ctx.author.id)]])

            if len(alerts_listed):
                description = [f'{ctx.author.mention}: alert listed', '']
                for k, v in alerts_listed.items():
                    description.append(f'**{k}** {v}')
            else:
                description = [f'{ctx.author.mention}: None.']
            embed = Embed(
                title="Stocks personal alerts",
                description="\n".join(description),
                url=f'https://www.torn.com/page.php?sid=stocks',
                color=my_blue
            )
            await send(ctx.channel, embed=embed)
            return

        if len(args) < 2:
            await self.bot.send_error_message(ctx.channel, doc, title="Stocks personal alerts error")
            return

        if args[0].upper() not in self.stocks_acronym_to_id:
            await self.bot.send_error_message(ctx.channel, f"Unknown stocks acronym {args[0].upper()}.", title="Stocks personal alerts error")
            return

        acronym = args[0].upper()
        stock_id = self.stocks_acronym_to_id[acronym]

        if args[1] == "off":
            if str(ctx.author.id) in config["personal_alerts"][stock_id]:
                del self.bot.configurations[ctx.guild.id]["stocks"]["personal_alerts"][stock_id][str(ctx.author.id)]
            embed = Embed(
                title="Stocks personal alerts",
                description=f'{ctx.author.mention}: {acronym} stocks alerts removed.',
                url=f'https://www.torn.com/page.php?sid=stocks&stockID={stock_id}&tab=owned',
                color=my_blue
            )
            await send(ctx.channel, embed=embed)
            await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            return

        alerts_values = [float(_) for _ in args[1:] if _.replace(".", "", 1).isdigit() and float(_) > 0]
        if len(alerts_values):
            alerts_values_string = "\n".join([f"- ${_:.1f}" for _ in alerts_values])
            embed = Embed(
                title="Stocks personal alerts",
                description=f'Alerts sets for **{acronym}**\n\n{alerts_values_string}',
                url=f'https://www.torn.com/page.php?sid=stocks&stockID={stock_id}&tab=owned',
                color=my_blue
            )
            embed.set_thumbnail(url=f'https://yata.yt/media/stocks/{stock_id}.png')
            await send(ctx.channel, embed=embed)
            self.bot.configurations[ctx.guild.id]["stocks"]["personal_alerts"][stock_id][str(ctx.author.id)] = alerts_values
            await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
        else:
            await self.bot.send_error_message(ctx.channel, f"No valid values found for alerts.", title="Stocks personal alerts error")


    @tasks.loop(seconds=60)
    async def generic_alerts(self):
        logging.debug(f"[stocks/generic_alerts] start task")

        for stock_id, stocks_data in self.stocks_status.items():
            # logging.debug(f"[stocks/generic_alerts] stock id {stock_id}")

            # market cap
            alert_key = f"market_cap_{stock_id}"
            diff = stocks_data["market_cap"] - stocks_data["previous_market_cap"]
            if abs(diff) > 99e9 and int(time.time()) - self.stocks_generic_alerts.get(alert_key, {"timestamp": 0})["timestamp"] > 3600:
                logging.info(f"[stocks/generic_alerts] stock id {stock_id} alert market cap")

                description = f'The market cap went {"up" if diff > 0 else "down"} by {dol(abs(diff) / 1e9, 2)}b ({"+" if diff > 0 else "-"}{100 * (abs(diff) / float(stocks_data["market_cap"])):,.1f}%)'
                embed = Embed(
                    title=f'Large amount of {stocks_data["acronym"]} has been {"bought" if diff > 0 else "sold"}',
                    url=f'https://www.torn.com/page.php?sid=stocks&stockID={stock_id}&tab=owned',
                    color=my_blue,
                    description=description
                )

                embed, file = self._fill_stocks_embed(embed, stock_id, stocks_data)

                self.stocks_generic_alerts[alert_key] = {
                    "timestamp": int(time.time()),
                    "embed": embed,
                    "file": file,
                    "content": description,
                    "acronym": stocks_data["acronym"],
                    "sent": []
                }

            # price
            # alert_key = f"price_{stock_id}"
            # p = stocks_data["tendency_h_a"] / stocks_data["current_price"]
            # if p > 0.05 and int(time.time()) - self.stocks_generic_alerts.get(alert_key, {"timestamp": 0})["timestamp"] > 3600:
            #     logging.info(f"[stocks/generic_alerts] stock id {stock_id} alert price")
            #
            #     embed = Embed(
            #         title=f'Important price fluctuation on {stocks_data["acronym"]}',
            #         url=f'https://www.torn.com/page.php?sid=stocks&stockID={stock_id}&tab=owned',
            #         color=my_blue,
            #         description=f'Last hour, the share price went {"up" if p > 0 else "down"} by {100 * p:,.1f}% to {dol(stocks_data["current_price"], 2)}'
            #     )
            #
            #     embed, file = fill_stocks_embed(embed, stock_id, stocks_data)
            #
            #     self.stocks_generic_alerts[alert_key] = {
            #         "timestamp": int(time.time()),
            #         "embed": embed,
            #         "file": file,
            #         "content": f'{stocks_data["acronym"]} price went {"up" if p > 0 else "down"} by {100 * p:,.1f}%',
            #         "sent": []
            #     }


        await asyncio.gather(*map(self._send_server_alerts, self.bot.get_guilds_by_module("stocks")))

        logging.debug(f"[stocks/generic_alerts] end task")


    @tasks.loop(seconds=60)
    async def personal_alerts(self):
        logging.debug(f"[stocks/personal_alerts] start task")

        # get personal alerts from all servers
        personal_alerts = {}
        for guild in self.bot.get_guilds_by_module("stocks"):
            for stock_id, members_alerts in self.bot.get_guild_configuration_by_module(guild, "stocks").get("personal_alerts", {}).items():
                if stock_id not in personal_alerts:
                    personal_alerts[stock_id] = {}
                for member, alerts in members_alerts.items():
                    personal_alerts[stock_id][member] = list(set(personal_alerts[stock_id].get(member, []) + alerts))

        for stock_id, stocks_data in self.stocks_status.items():
            # logging.debug(f"[stocks/personal_alerts] stock id {stock_id}")

            current_price = stocks_data["current_price"]
            previous_price = stocks_data["previous_price"]
            up = current_price > previous_price

            for member_id, alerts in personal_alerts.get(stock_id, {}).items():
                member = get(guild.members, id=int(member_id))
                if member is None:
                    continue

                logging.debug(f"[stocks/personal_alerts] stock id {stock_id}: member {member} -> {alerts}")
                # print(stocks_data)
                for alert_price in alerts:
                    logging.debug(f"[stocks/personal_alerts] stock id {stock_id}: member {member} -> {alert_price} ({previous_price}, {current_price})")
                    sign_PB = previous_price > alert_price
                    sign_CB = current_price > alert_price
                    if sign_CB != sign_PB:
                        logging.debug(f"[stocks/personal_alerts] stock id {stock_id}: member {member} -> {alerts} ALERT")

                        content = f'{stocks_data["acronym"]} at {dol(current_price, 2)} ({"above" if up else "below"} your personal threshold of {dol(alert_price, 2)})'
                        description = f'{stocks_data["acronym"]} {"above" if up else "below"} your personal threshold of {dol(alert_price, 2)}'
                        embed = Embed(
                            title=f'{stocks_data["acronym"]} personal threshold reached',
                            url=f'https://www.torn.com/page.php?sid=stocks&stockID={stock_id}&tab=owned',
                            color=my_blue,
                            description=description
                        )

                        embed, file = self._fill_stocks_embed(embed, stock_id, stocks_data)

                        await send(member, description, embed=embed, file=file)
                        break

        logging.debug(f"[stocks/personal_alerts] end task")


    @tasks.loop(seconds=60)
    async def update_data(self):
        try:
            logging.debug(f"[stocks/update_data] start")

            response, e = await self.bot.yata_api_call("stocks/get")

            if e or "error" in response:
                return

            for k, v in response["stocks"].items():
                self.stocks_status[str(k)] = v
                self.stocks_history[str(k)].append(
                    {
                        "timestamp": v["timestamp"],
                        "current_price": v["current_price"],
                        "total_shares": v["total_shares"],
                        "market_cap": v["market_cap"]
                    }
                )
                self.stocks_acronym_to_id[v["acronym"]] = str(k)
                self.stocks_id_to_acronym[str(k)] = v["acronym"]

            logging.debug(f"[stocks/update_data] end")

        except BaseException as e:
            await self.bot.send_log_main(e)

    @update_data.before_loop
    async def before_update_data(self):
        logging.info(f"[stocks/update_data] waiting...")
        await self.bot.wait_until_ready()

    @generic_alerts.before_loop
    async def before_generic_alerts(self):
        logging.info(f"[stocks/generic_alerts] waiting...")
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    @personal_alerts.before_loop
    async def before_personal_alerts(self):
        logging.info(f"[stocks/personal_alerts] waiting...")
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

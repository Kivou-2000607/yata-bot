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
import time
import datetime
import json
import re
import logging
import html

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get
from discord import Embed

# import bot functions and classes
from inc.handy import *
from inc.yata_db import get_loots
from inc.yata_db import get_scheduled
from inc.yata_db import get_npc


class Loot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify_4.start()
        self.notify_5.start()
        self.scheduled.start()

        self.lvl_roman = {0: "Hospitalized", 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}
        self.roman_lvl = {"Hospitalized": 0, "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
        self.lvl_dt = {0: 0, 1: 0, 2: 30 * 60, 3: 90 * 60, 4: 210 * 60, 5: 450 * 60}
        self.lvl_to_display = [4, 5]

    def cog_unload(self):
        self.notify_4.cancel()
        self.notify_5.cancel()
        self.scheduled.cancel()

    # def botMessages(self, message):
    #     return message.author.id == self.bot.user.id and message.content[:6] == "```ARM"

    @commands.command(aliases=['duke', 'Duke', 'leslie', 'Leslie', 'Loot'])
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.guild_only()
    async def loot(self, ctx):
        """Gives loot timing for each NPC"""
        logging.info(f'[loot/loot] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "loot")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        now = ts_now()

        # get npc timings from YATA db
        loots_raw = await get_loots()
        loots = {}

        for loot in loots_raw:
            name = loot.get("name")
            hosp = loot.get("hospitalTS")

            # get current loot level
            lvlc = 0  # current level
            for lv, dt in self.lvl_dt.items():
                lvlc = lv if now > hosp + dt else lvlc

            loots[loot.get("tId")] = {'name': name, 'hosp': hosp, 'lvlc': lvlc, 'timings': []}

            # get all loot level timings
            for i in self.lvl_to_display:
                timing = {"due": hosp + self.lvl_dt[i] - now, "time": hosp + self.lvl_dt[i], "lvl": i}
                loots[loot.get("tId")]["timings"].append(timing)

        # get NPC from the database and loop
        for id, npc in loots.items():
            description_list = []
            name = npc["name"]
            hosp = npc["hosp"]
            lvlc = npc["lvlc"]
            for timing in npc["timings"]:
                lvl = timing["lvl"]
                due = timing["due"]
                time = timing["time"]

                if due < 0:  # level already reached
                    description_list.append(f'*Level {self.lvl_roman[lvl]} since {s_to_hms(abs(due))} at {ts_to_datetime(time).strftime("%H:%M:%S")}*')
                else:
                    delta_lvl_time = self.lvl_dt[lvl] - self.lvl_dt[lvl - 1] if lvl > 1 else 30 * 60
                    delta_due_time = delta_lvl_time - due
                    advance = 100 * (delta_lvl_time - due) // delta_lvl_time
                    description_list.append(f'{"**" if lvl == lvlc + 1 else ""}Level {self.lvl_roman[lvl]} in {s_to_hms(abs(due))} at {ts_to_datetime(time).strftime("%H:%M:%S")}{f" ({advance}%)" if advance > 0 else ""}{"**" if lvl == lvlc + 1 else ""}')

            eb = Embed(description="\n".join(description_list),color=my_blue)
            eb.set_author(name=f'{npc["name"]} [{id}]', url=f'https://www.torn.com/loader.php?sid=attack&user2ID={id}', icon_url=f'https://yata.yt/media/loot/npc_{id}.png')
            eb.set_thumbnail(url=f'https://yata.yt/media/loot/loot_lvl_{lvlc}.png')
            await ctx.send(embed=eb)

        # clean messages
        # await ctx.message.delete()

        # async for m in ctx.channel.history(limit=10, before=ctx.message).filter(self.botMessages):
        #     await m.delete()

    async def notify(self, level):
        logging.debug(f"[loot/notifications_{level}] start task")

        # get npc timings from YATA db
        loots_raw = await get_loots()
        loots = {}
        for loot in loots_raw:
            name = loot.get("name")
            ts = loot.get("hospitalTS") + self.lvl_dt[level]
            due = ts - ts_now()
            loots[loot.get("tId")] = { 'name': name, 'due': due, 'ts':  ts }

        # loop over NPCs
        mentions = []
        embeds = []
        nextDue = []
        for npc_id, npc in loots.items():
            due = npc["due"]
            ts = npc["ts"]

            if due > -60 and due < 10 * 60:
                notification = "{} {}".format(npc["name"], "in " + s_to_ms(due) if due > 0 else "now")
                mentions.append(notification)

                # author field
                author = f'{npc["name"]} [{npc_id}]'
                author_icon = f"https://yata.yt/media/loot/npc_{npc_id}.png"
                author_url = f'https://www.torn.com/loader.php?sid=attack&user2ID={npc_id}'

                # description field
                description = f'Loot {self.lvl_roman[level]} {"since" if due < 0 else "in"} {s_to_time(abs(due))}'
                embed = Embed(description=description, color=my_blue)
                embed.set_author(name=author, url=author_url, icon_url=author_icon)
                embed = append_update(embed, ts, text="At ")

                embeds.append(embed)
                logging.debug(f'[loot/notifications_{level}] {npc["name"]}: notify (due {due})')
            elif due > 0:
                # used for computing sleeping time
                nextDue.append(due)
                logging.debug(f'[loot/notifications_{level}] {npc["name"]}: ignore (due {due})')
            else:
                logging.debug(f'[loot/notifications_{level}] {npc["name"]}: ignore (due {due})')

        # get the sleeping time (15 minutes all dues < 0 or 5 minutes before next due)
        nextDue = sorted(nextDue, reverse=False) if len(nextDue) else [15 * 60]
        s = nextDue[0] - 7 * 60 - 5  # next due - 7 minutes - 5 seconds of the task ticker
        logging.debug(f"[loot/notifications_{level}] end task... sleeping for {s_to_hms(s)} minutes.")

        # iteration over all guilds
        for guild in self.bot.get_guilds_by_module("loot"):
            try:
                logging.debug(f"[loot/notifications_{level}] {guild}")

                config = self.bot.get_guild_configuration_by_module(guild, "loot", check_key="channels_alerts")
                if not config:
                    continue

                # get role & channel
                role = self.bot.get_module_role(guild.roles, config.get("roles_alerts", {}))
                channel = self.bot.get_module_channel(guild.channels, config.get("channels_alerts", {}))

                if channel is None:
                    continue

                # loop of npcs to mentions
                for m, e in zip(mentions, embeds):
                    logging.debug(f"[LOOT] guild {guild}: mention {m}.")
                    msg = f'{m} {"" if role is None else role.mention}'
                    await channel.send(msg, embed=e)

            except BaseException as e:
                logging.error(f'[loot/notifications_{level}] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(f'Error during a loot alert: {e}', guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on loot notifications"}
                await self.bot.send_log_main(e, headers=headers, full=True)

        # sleeps
        logging.debug(f"[loot/notifications_{level}] sleep for {s} seconds")
        await asyncio.sleep(s)

    @tasks.loop(seconds=5)
    async def notify_4(self):
        await self.notify(4)

    @tasks.loop(seconds=5)
    async def notify_5(self):
        await self.notify(5)

    @tasks.loop(minutes=10)
    async def scheduled(self):
        logging.debug("[loot/scheduled] start task")

        loots_raw = await get_scheduled()

        mentions = []
        embeds = []
        for loot in loots_raw:
            if loot.get("vote") < 25:
                continue

            due = loot.get("timestamp") - ts_now()
            # if True:
            if due < 10 * 60:
                # get NPC
                npc = await get_npc(loot.get("npc_id"))
                if not len(npc):
                    continue

                npc = npc[0]
                notification = "{} {}".format(npc["name"], "in " + s_to_ms(due) if due > 0 else "now")
                mentions.append(notification)

                # author field
                author = f'{npc["name"]} [{npc["tId"]}]'
                author_icon = f'https://yata.yt/media/loot/npc_{npc["tId"]}.png'
                author_url = f'https://www.torn.com/loader.php?sid=attack&user2ID={npc["tId"]}'

                # description field
                description = f'Scheduled attack by {loot.get("vote")} players in {s_to_time(abs(due))}'
                embed = Embed(description=description, color=my_blue)
                embed.set_author(name=author, url=author_url, icon_url=author_icon)
                embed = append_update(embed, loot["timestamp"], text="At ")

                embeds.append(embed)

        if not len(mentions):
            return

        # iteration over all guilds
        for guild in self.bot.get_guilds_by_module("loot"):
            try:
                logging.debug(f"[loot/notifications] {guild}")

                config = self.bot.get_guild_configuration_by_module(guild, "loot", check_key="channels_alerts")
                if not config:
                    continue

                # get role & channel
                role = self.bot.get_module_role(guild.roles, config.get("roles_alerts", {}))
                channel = self.bot.get_module_channel(guild.channels, config.get("channels_alerts", {}))

                if channel is None:
                    continue

                # loop of npcs to mentions
                for m, e in zip(mentions, embeds):
                    logging.debug(f"[LOOT] guild {guild}: mention {m}.")
                    msg = f'{m} {"" if role is None else role.mention}'
                    await channel.send(msg, embed=e)

            except BaseException as e:
                logging.error(f'[loot/notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(f'Error during a loot alert: {e}', guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on loot notifications"}
                await self.bot.send_log_main(e, headers=headers, full=True)

    @notify_4.before_loop
    async def before_notify_4(self):
        await self.bot.wait_until_ready()

    @notify_5.before_loop
    async def before_notify_5(self):
        await self.bot.wait_until_ready()

    @scheduled.before_loop
    async def before_scheduled(self):
        await self.bot.wait_until_ready()

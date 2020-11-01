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


class Loot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

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

        # get npc timings from YATA db
        loots_raw = await get_loots()
        loots = {}
        for loot in loots_raw:
            name = loot.get("name")
            hospout = loot.get("hospitalTS")
            ts = hospout + (210 * 60)
            due = ts - ts_now()
            level = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}.get(loot.get("status").split(" ")[-1], 0)
            loots[loot.get("id")] = {'name': name, 'due': due, 'ts':  ts, 'hospout': hospout, 'level': level}

        # get NPC from the database and loop
        for id, npc in loots.items():
            due = npc["due"]
            ts = npc["ts"]
            advance = max(100 * (ts - npc["hospout"] - max(0, due)) // (ts - npc["hospout"]), 0)
            ll = {0: "hospitalized", 1: "level I", 2: "level II", 3: "level III", 4: "level IV", 5: " level V"}
            lvl = npc["level"]
            eb = Embed(description=f'**Level IV** {"since" if due < 0 else "in"} {s_to_hms(abs(due))} at {ts_to_datetime(ts).strftime("%H:%M:%S")} ({str(advance): >3}%)',color=my_blue)
            eb.set_author(name=f'{npc["name"]} is {ll[lvl]}', url=f'https://www.torn.com/loader.php?sid=attack&user2ID={id}', icon_url=f'https://yata.alwaysdata.net/media/images/loot/npc_{id}.png')
            eb.set_thumbnail(url=f'https://yata.alwaysdata.net/media/images/loot/loot{lvl}.png')

            await ctx.send(embed=eb)

        # clean messages
        # await ctx.message.delete()

        # async for m in ctx.channel.history(limit=10, before=ctx.message).filter(self.botMessages):
        #     await m.delete()

    @tasks.loop(seconds=5)
    async def notify(self):
        logging.debug("[loot/notifications] start task")

        # images and items
        thumbs = {
            '4': "https://yata.alwaysdata.net/media/images/loot/npc_4.png",
            '7': "https://yata.alwaysdata.net/media/images/loot/npc_7.png",
            '10': "https://yata.alwaysdata.net/media/images/loot/npc_10.png",
            '15': "https://yata.alwaysdata.net/media/images/loot/npc_15.png",
            '19': "https://yata.alwaysdata.net/media/images/loot/npc_19.png"}

        # get npc timings from YATA db
        loots_raw = await get_loots()
        loots = {}
        for loot in loots_raw:
            name = loot.get("name")
            ts = loot.get("hospitalTS") + (210 * 60)
            due = ts - ts_now()
            loots[loot.get("id")] = { 'name': name, 'due': due, 'ts':  ts }

        # loop over NPCs
        mentions = []
        embeds = []
        nextDue = []
        for id, npc in loots.items():
            due = npc["due"]
            ts = npc["ts"]

            if due > -60 and due < 10 * 60:
                notification = "{} {}".format(npc["name"], "in " + s_to_ms(due) if due > 0 else "now")
                mentions.append(notification)

                # author field
                author = f'{npc["name"]} [{id}]'
                author_icon = thumbs.get(id, "?")
                author_url = f'https://www.torn.com/loader.php?sid=attack&user2ID={id}'

                # description field
                description = f'Loot level IV {"since" if due < 0 else "in"} {s_to_time(abs(due))}'
                embed = Embed(description=description, color=my_blue)
                embed.set_author(name=author, url=author_url, icon_url=author_icon)
                embed = append_update(embed, ts, text="At ")

                embeds.append(embed)
                logging.debug(f'[loot/notifications] {npc["name"]}: notify (due {due})')
            elif due > 0:
                # used for computing sleeping time
                nextDue.append(due)
                logging.debug(f'[loot/notifications] {npc["name"]}: ignore (due {due})')
            else:
                logging.debug(f'[loot/notifications] {npc["name"]}: ignore (due {due})')

        # get the sleeping time (15 minutes all dues < 0 or 5 minutes before next due)
        nextDue = sorted(nextDue, reverse=False) if len(nextDue) else [15 * 60]
        s = nextDue[0] - 7 * 60 - 5  # next due - 7 minutes - 5 seconds of the task ticker
        logging.debug(f"[loot/notifications] end task... sleeping for {s_to_hms(s)} minutes.")

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

        # sleeps
        logging.debug(f"[loot/notifications] sleep for {s} seconds")
        await asyncio.sleep(s)

    @notify.before_loop
    async def before_notify(self):
        await self.bot.wait_until_ready()

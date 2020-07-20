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


class Loot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

    def botMessages(self, message):
        return message.author.id == self.bot.user.id and message.content[:6] == "```ARM"

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

        # compute current time
        now = int(time.time())
        msg = [f'NPC report of {ts_to_datetime(now).strftime("%y/%m/%d %H:%M:%S")} TCT for {ctx.author.display_name}\n']

        # YATA api
        url = "https://yata.alwaysdata.net/loot/timings/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                try:
                    req = await r.json()
                except:
                    req = {'error': {'error': 'YATA\'s API is talking shit... #blamekivou', 'code': -1}}

        if 'error' in req:
            await ctx.send("```ARM\nError code {}\n{}```Have a look a the timings here: https://yata.alwaysdata.net/loot/".format(req['error']['code'], req['error']['error']))
            return

        # get NPC from the database and loop
        for id, npc in req.items():
            due = npc["timings"]["4"]["due"]
            ts = npc["timings"]["4"]["ts"]
            advance = max(100 * (ts - npc["hospout"] - max(0, due)) // (ts - npc["hospout"]), 0)
            n = 20
            i = int(advance * n / 100)

            line = [f'{npc["name"]: <7}:']
            line.append(f'[{"=" * i}{" " * (n - i)}] ({str(advance): >3}%)')
            line.append(f'{s_to_hms(abs(due))} {"since" if due < 0 else "to"} loot level IV')
            line.append(f'[{ts_to_datetime(ts).strftime("%H:%M:%S")} TCT]')

            msg.append(" ".join(line))

        await ctx.send("```ARM\n{}```".format("\n".join(msg)))

        # clean messages
        await ctx.message.delete()

        async for m in ctx.channel.history(limit=10, before=ctx.message).filter(self.botMessages):
            await m.delete()

    @tasks.loop(seconds=5)
    async def notify(self):
        logging.debug("[loot/notifications] start task")

        # images and items
        thumbs = {
            '4': "https://yata.alwaysdata.net/static/images/loot/npc_4.png",
            '7': "https://yata.alwaysdata.net/static/images/loot/npc_7.png",
            '10': "https://yata.alwaysdata.net/static/images/loot/npc_10.png",
            '15': "https://yata.alwaysdata.net/static/images/loot/npc_15.png",
            '19': "https://yata.alwaysdata.net/static/images/loot/npc_19.png"}
        items = {
            '4': ["Rheinmetall MG", "Homemade Pocket Shotgun", "Madball", "Nail Bomb"],
            '10': ["Snow Cannon", "Diamond Icicle", "Snowball"],
            '15': ["Nock Gun", "Beretta Pico", "Riding Crop", "Sand"],
            '19': ["Bread Knife"]}

        # YATA api
        url = "https://yata.alwaysdata.net/loot/timings/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # loop over NPCs
        mentions = []
        embeds = []
        nextDue = []
        for id, npc in req.items():
            lvl = npc["levels"]["current"]
            due = npc["timings"]["4"]["due"]
            ts = npc["timings"]["4"]["ts"]

            ll = {0: "hospitalized", 1: "level I", 2: "level II", 3: "level III", 4: "level IV", 5: " level V"}
            if due > -60 and due < 10 * 60:
                notification = "{} {}".format(npc["name"], "in " + s_to_ms(due) if due > 0 else "**NOW**")
                mentions.append(notification)

                title = "**{}** is currently {}".format(npc["name"], ll[lvl])
                msg = "{}".format("https://www.torn.com/profiles.php?XID={}".format(id))
                embed = Embed(title=title, description=msg, color=550000)

                if due < 0:
                    embed.add_field(name='Loot level IV since', value='{}'.format(s_to_ms(abs(due))))
                    embed.add_field(name='Date', value='{} TCT'.format(ts_to_datetime(npc["timings"]["4"]["ts"]).strftime("%y/%m/%d %H:%M:%S")))
                else:
                    embed.add_field(name='Loot {} in'.format(ll[lvl + 1]), value='{}'.format(s_to_ms(due)))
                    embed.add_field(name='At', value='{} TCT'.format(ts_to_datetime(ts).strftime("%H:%M:%S")))

                url = thumbs.get(id, "?")
                embed.set_thumbnail(url=url)
                embed.set_footer(text='Items to loot: {}'.format(', '.join(items.get(id, ["Nice things"]))))
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
                    msg = f'Go for {m}' if role is None else f'{role.mention}, go for {m}'
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

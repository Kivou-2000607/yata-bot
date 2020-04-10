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
import json

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get
from discord import Embed

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt


class Loot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

    @commands.command(aliases=['duke', 'Duke', 'leslie', 'Leslie', 'Loot'])
    async def loot(self, ctx):
        """Gives loot timing for each NPC"""
        # return if verify not active
        if not self.bot.check_module(ctx.guild, "loot"):
            await ctx.send(":x: Loot module not activated")
            return

        # check role and channel
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "loot")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # compute current time
        now = int(time.time())
        # msg = ["Latest NPC report of {} TCT, asked by {}".format(fmt.ts_to_datetime(now).strftime("%y/%m/%d %H:%M:%S"), ctx.author.mention)]
        msg = [f'NPC report of {fmt.ts_to_datetime(now).strftime("%y/%m/%d %H:%M:%S")} TCT for {ctx.author.display_name}\n']
        # msg = []

        # YATA api
        url = "https://yata.alwaysdata.net/loot/timings/"
        # req = requests.get(url).json()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

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

            keyword = "since" if due < 0 else "to"

            line = []
            line.append(f'{npc["name"]: <7}:')
            line.append(f'[{"=" * i}{" " * (n - i)}] ({str(advance): >3}%)')

            line.append(f'{fmt.s_to_hms(abs(due))} {keyword} loot level IV')
            # line.append(f'({fmt.ts_to_datetime(ts).strftime("%y/%m/%d %H:%M:%S")} TCT)')
            line.append(f'[{fmt.ts_to_datetime(ts).strftime("%H:%M:%S")} TCT]')

            # line.append(f'https://www.torn.com/profiles.php?XID={id}')
            msg.append(" ".join(line))

        await ctx.send("```ARM\n{}```".format("\n".join(msg)))

        # clean messages
        await ctx.message.delete()

        def botMessages(message):
            return message.author.id == self.bot.user.id and message.content[:6] == "```ARM"
        async for m in ctx.channel.history(limit=10, before=ctx.message).filter(botMessages):
            await m.delete()

    @commands.command()
    async def looter(self, ctx):
        """Add/remove @Looter role"""
        # return if loot not active
        if not self.bot.check_module(ctx.guild, "loot"):
            await ctx.send(":x: Loot module not activated")
            return

        # Get Looter role
        role = get(ctx.guild.roles, name="Looter")

        if role in ctx.author.roles:
            # remove Looter
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **stop** receiving notifications for loot.")
        else:
            # assign Looter
            await ctx.author.add_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **start** receiving notifications for loot.")

        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()

    @tasks.loop(seconds=5)
    async def notify(self):
        print("[LOOT] start task")

        # images and items
        thumbs = {
            '4': "https://yata.alwaysdata.net/static/images/loot/npc_4.png",
            '10': "https://yata.alwaysdata.net/static/images/loot/npc_10.png",
            '15': "https://yata.alwaysdata.net/static/images/loot/npc_15.png"}
        items = {
            '4': ["Rheinmetall MG", "Homemade Pocket Shotgun", "Madball", "Nail Bomb"],
            '10': ["Snow Cannon", "Diamond Icicle", "Snowball"],
            '15': ["Nock Gun", "Beretta Pico", "Riding Crop", "Sand"]}

        # YATA api
        url = "https://yata.alwaysdata.net/loot/timings/"
        # req = requests.get(url).json()
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
                notification = "{} {}".format(npc["name"], "in " + fmt.s_to_ms(due) if due > 0 else "**NOW**")
                mentions.append(notification)

                title = "**{}** is currently {}".format(npc["name"], ll[lvl])
                msg = "{}".format("https://www.torn.com/profiles.php?XID={}".format(id))
                embed = Embed(title=title, description=msg, color=550000)

                if due < 0:
                    embed.add_field(name='Loot level IV since', value='{}'.format(fmt.s_to_ms(abs(due))))
                    embed.add_field(name='Date', value='{} TCT'.format(fmt.ts_to_datetime(npc["timings"]["4"]["ts"]).strftime("%y/%m/%d %H:%M:%S")))
                else:
                    embed.add_field(name='Loot {} in'.format(ll[lvl + 1]), value='{}'.format(fmt.s_to_ms(due)))
                    embed.add_field(name='At', value='{} TCT'.format(fmt.ts_to_datetime(ts).strftime("%H:%M:%S")))

                url = thumbs.get(id, "?")
                embed.set_thumbnail(url=url)
                embed.set_footer(text='Items to loot: {}'.format(', '.join(items.get(id, ["Nice things"]))))
                embeds.append(embed)
                print(f'[LOOT] {npc["name"]}: notify (due {due})')
            elif due > 0:
                # used for computing sleeping time
                nextDue.append(due)
                print(f'[LOOT] {npc["name"]}: ignore (due {due})')
            else:
                print(f'[LOOT] {npc["name"]}: ignore (due {due})')

        # get the sleeping time (15 minutes all dues < 0 or 5 minutes before next due)
        nextDue = sorted(nextDue, reverse=False) if len(nextDue) else [15 * 60]
        s = nextDue[0] - 5 * 60 - 5  # next due - 5 minutes - 5 seconds of the task ticker
        print(f"[LOOT] end task... sleeping for {fmt.s_to_hms(s)} minutes.")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                # ignore non loot servers
                if not self.bot.check_module(guild, "loot"):
                    # print(f"[LOOT] guild {guild}: ignore.")
                    continue
                # print(f"[LOOT] guild {guild}: notify.")

                # get full guild (async iterator doesn't return channels)
                guild = self.bot.get_guild(guild.id)

                # get channel
                config = self.bot.get_config(guild)
                channel_name = self.bot.get_allowed_channels(config, "loot")[0]
                channel = get(guild.channels, name=channel_name)

                # get role
                role = get(guild.roles, name="Looter")

                # loop of npcs to mentions
                for m, e in zip(mentions, embeds):
                    print(f"[LOOT] guild {guild}: mention {m}.")
                    # await channel.send(f'{role.mention}, go for {m} equip Tear Gas or Smoke Grenade', embed=e)
                    await channel.send(f'{role.mention}, go for {m}', embed=e)

            except BaseException as e:
                lst = ["```YAML",
                       f"Log:     Loot notification error",
                       f"Server:  {guild} [{guild.id}]",
                       f"Channel: {channel.name}",
                       f"",
                       f"{e}",
                       f"```"]
                await self.bot.sendLogChannel("\n".join(lst))
                print(f"[LOOT] guild {guild}: mention failed {e}.")

            # await get(guild.channels, name="admin").send(f"<debug>sleeping for {fmt.s_to_hms(s)} minutes</debug>")

        # sleeps
        await asyncio.sleep(s)

    @notify.before_loop
    async def before_notify(self):
        print('[LOOT] waiting...')
        await self.bot.wait_until_ready()

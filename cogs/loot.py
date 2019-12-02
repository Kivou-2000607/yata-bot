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
        # get configuration for guild
        c = self.bot.get_config(ctx.guild)

        # return if verify not active
        if not c.get("loot"):
            await ctx.send(":x: Loot module not activated")
            return

        # check role and channel
        ALLOWED_CHANNELS = ["loot"]
        ALLOWED_ROLES = ["Looter"]
        if await checks.roles(ctx, ALLOWED_ROLES) and await checks.channels(ctx, ALLOWED_CHANNELS):
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
            return message.author.id == self.bot.user.id
        async for m in ctx.channel.history(limit=10, before=ctx.message).filter(botMessages):
            await m.delete()

    @commands.command()
    async def looter(self, ctx):
        """Add/remove @Looter role"""
        # get configuration for guild
        c = self.bot.get_config(ctx.guild)

        # return if loot not active
        if not c.get("loot"):
            await ctx.send(":x: Loot module not activated")
            return

        # check role and channel
        ALLOWED_CHANNELS = ["start-looting", "loot"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # Get Looter role
        role = get(ctx.guild.roles, name="Looter")

        if role in ctx.author.roles:
            # remove Looter
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll stop receiving notifications.")
        else:
            # assign Looter
            await ctx.author.add_roles(role)
            channel = get(ctx.guild.channels, name="loot")
            msg = await ctx.send(f"**{ctx.author.display_name}**, you're a looter now. You'll receive a notification in {channel.mention} when a NPC is about to reach level IV.")

        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()

    @tasks.loop(minutes=10)
    async def notify(self):
        print("notify...")

        # images and items
        thumbs = {
            '4': "https://yata.alwaysdata.net/static/images/loot/npc_4.png",
            '10': "https://yata.alwaysdata.net/static/images/loot/npc_10.png",
            '15': "https://yata.alwaysdata.net/static/images/loot/npc_15.png"}
        thumbd = "https://cdn.discordapp.com/app-icons/547341843788988416/32772ee397ec7c5d9cb85fd530c8f58e.png"
        items = {
            '4': ["Rheinmetall MG", "Homemade Pocket Shotgun", "Madball", "Nail Bomb"],
            '10': ["Snow Cannon", "Diamond Icicle"],
            '15': ["Nock Gun", "Beretta Pico", "Riding Crop", "Sand"]}
        itemd = "Nice item"

        # YATA api
        url = "https://yata.alwaysdata.net/loot/timings/"
        # req = requests.get(url).json()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # loop over NPCs
        mentions = []
        embeds = []
        nextDue = 999999999
        allOut = True
        for id, npc in req.items():
            lvl = npc["levels"]["current"]
            due = npc["timings"]["4"]["due"]
            ts = npc["timings"]["4"]["ts"]

            # used for computing time
            nextDue = min(due, nextDue)
            if lvl == 0:
                allOut = False

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

                url = thumbs.get(id, thumbd)
                embed.set_thumbnail(url=url)
                embed.set_footer(text='Items to loot: {}'.format(', '.join(items.get(id, ["Nice things"]))))
                embeds.append(embed)

        # iteration over all guilds
        # for guildId in [int(k) for k, v in self.bot.configs.items() if v.get('loot') is not None]:
        async for guild in self.bot.fetch_guilds(limit=5):
            c = self.bot.get_config(guild)

            # ignore non loot servers
            if c.get('loot') is None:
                continue

            # get full guild (iterator doesn't return channels)
            guild = self.bot.get_guild(guild.id)

            # get channel
            channel = get(guild.channels, name="loot")

            # get role
            role = get(guild.roles, name="Looter")

            # loop of npcs to mentions
            for m, e in zip(mentions, embeds):
                await channel.send(f'{role.mention}, go for {m} equip Tear Gas or Smike Grenade', embed=e)

        # get the sleeping time
        # if all npc out -> next notification 5 minutes before next due
        # if allOut:
        s = nextDue - 5 * 60
        print(f"sleeping for {s/60} minutes.")
        await asyncio.sleep(s)

    @notify.before_loop
    async def before_notify(self):
        print('waiting...')
        await self.bot.wait_until_ready()

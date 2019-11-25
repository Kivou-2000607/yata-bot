# import standard modules
import asyncio
import aiohttp
import time

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt


class Loot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['duke', 'Duke', 'leslie', 'Leslie', 'Loot'])
    async def loot(self, ctx):
        """Gives loot timing for each NPC"""

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

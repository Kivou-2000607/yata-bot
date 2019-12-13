# import standard modules
import asyncio
import aiohttp
import datetime
import json

# import discord modules
from discord.ext import commands

# import bot functions and classes
import includes.checks as checks


class Chain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def chain(self, ctx, *args):
        """Toggle chain timeout notifications"""

        # default values of the arguments
        deltaW=90  # warning timeout in seconds
        deltaN=600  # breathing messages every in second
        faction=""  # use faction from key

        for arg in args:
            splt = arg.split("=")
            if arg.isdigit():
                faction=int(arg)
                continue
            elif len(splt) != 2:
                await ctx.send(f":chains: argument {arg} ignored")
                continue
            if splt[0] == 'f' and splt[1].isdigit():
                faction=int(splt[1])
            elif splt[0] == 'w' and splt[1].isdigit():
                deltaW=int(splt[1])
            elif splt[0] == 'n' and splt[1].isdigit():
                deltaN=int(splt[1])
            else:
                await ctx.send(f":chains: key/value pair {arg} ignored")


        # return if chain not active
        if not self.bot.check_module(ctx.guild, "chain"):
            await ctx.send(":x: Chain module not activated")
            return

        # check role and channel
        channelName = self.bot.get_config(ctx.guild).get("chain").get("channel", False)
        ALLOWED_CHANNELS = [channelName] if channelName else ["chain"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # Inital call to get faction name
        key = self.bot.key(ctx.guild)
        url = f'https://api.torn.com/faction/{faction}?selections=basic&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle no faction
        if req["ID"] is None:
            await ctx.send(f':x: No faction with id {faction}')
            return

        # handle API error
        if 'error' in req:
            await ctx.send(f':x: There is a API key problem ({req["error"]["error"]})')
            return

        factionName = f'`{req.get("name")} [{req.get("ID")}]`'

        await ctx.send(f":chains: {factionName} Start watching: will notify if timeout < {deltaW}s and give status every {deltaN/60:.1f}min")
        lastNotified = datetime.datetime(1970, 1, 1, 0, 0, 0)
        while True:

            # times needed
            now = datetime.datetime.utcnow()
            epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)

            # check if needs to notify still watching

            # check last 10 messages for a stop --- had to do it not async to catch only 1 stop
            history = await ctx.channel.history(limit=10).flatten()
            for m in history:
                if m.content == "!stop":
                    await m.delete()
                    await ctx.send(f":x: {factionName} Stop watching")
                    return

            # chain api call
            key = self.bot.key(ctx.guild)
            url = f'https://api.torn.com/faction/{faction}?selections=chain,timestamp&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # handle API error
            if 'error' in req:
                await ctx.send(f':x: {factionName} API key problem ({req["error"]["error"]})')
                return

            # get timings
            timeout = req.get("chain", dict({})).get("timeout", 0)
            cooldown = req.get("chain", dict({})).get("cooldown", 0)
            current = req.get("chain", dict({})).get("current", 0)
            timeout = 0
            cooldown = 0
            current = 0

            # get delay
            nowts = (now - epoch).total_seconds()
            apits = req.get("timestamp")

            delay = int(abs(nowts - apits))
            txtDelay = f"   ---   *API caching delay of {delay}s*" if delay else ""
            deltaLastNotified = (now - lastNotified).total_seconds()

            # add delay to
            # timeout -= delay

            # if cooldown
            if cooldown > 0:
                await ctx.send(f':x: {factionName} Chain at **{current}** in cooldown for {cooldown/60:.1f}min :cold_face:')
                return

            # if no chain
            elif current == 0 :
                await ctx.send(f':x: {factionName} No chains on the horizon :partying_face:')
                return

            # if timeout
            elif timeout == 0:
                await ctx.send(f':x: {factionName} Chain timed out at **{current}** :rage:')
                return

            # if warning
            elif timeout < deltaW:
                await ctx.send(f':chains: {factionName} Chain at **{current}** and timeout in **{timeout}s**{txtDelay} {ctx.guild.default_role} :scream:')

            # if long enough for a notification
            elif deltaLastNotified > deltaN:
                lastNotified = now
                await ctx.send(f':chains: {factionName} Chain at **{current}** (timeout in {timeout/60:.1f}min) {txtDelay}')

            # sleeps
            sleep = max(30, timeout - deltaW)
            # print(f"[CHAIN] {ctx.guild} API delay of {delay} seconds, timeout of {timeout}: sleeping for {sleep} seconds")
            notify = False
            await asyncio.sleep(sleep)

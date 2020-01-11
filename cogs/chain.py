# import standard modules
import asyncio
import aiohttp
import datetime
import json

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks


class Chain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def retal(self, ctx):
        """ Mention faction role if retal
        """

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

        # Initial call to get faction name
        status, tornId, Name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        url = f'https://api.torn.com/faction/?selections=basic&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if 'error' in req:
            await ctx.send(f':x: Problem with {name} [{tornId}]\'s key: *{req["error"]["error"]}*')
            return

        # handle no faction
        if req["ID"] is None:
            await ctx.send(f':x: No faction with id {req["ID"]}')
            return

        # faction name and role
        faction = req.get("ID")
        factionName = f'{req.get("name")} [{req.get("ID")}]'
        factionRole = get(ctx.guild.roles, name=factionName)

        await ctx.send(f":rage: `{factionName}` Start watching for retal")
        past_mentions = []
        while True:
            # check last 50 messages for a stop --- had to do it not async to catch only 1 stop
            history = await ctx.channel.history(limit=50).flatten()
            for m in history:
                if m.content == "!stopretal":
                    await m.delete()
                    await ctx.send(f":x: `{factionName}` Stop watching retals")
                    return

            url = f'https://api.torn.com/faction/?selections=attacks&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # handle API error
            if 'error' in req:
                await ctx.send(f':x: Problem with {name} [{tornId}]\'s key: *{req["error"]["error"]}*')
                return

            now = datetime.datetime.utcnow()
            epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
            nowts = (now - epoch).total_seconds()
            for k, v in req["attacks"].items():
                delay = int(nowts - v["timestamp_ended"]) / float(60)
                if v["defender_faction"] == int(faction) and v["attacker_id"] and k not in past_mentions and delay < 5:
                    if v["attacker_faction"]:
                        await ctx.send(f':rage: {factionRole.mention}: retal on **{v["attacker_name"]} [{v["attacker_id"]}]** from **{v["attacker_factionname"]} [{v["attacker_faction"]}]** https://www.torn.com/profiles.php?XID={v["attacker_id"]} ({delay:.1f} minutes)')
                    else:
                        await ctx.send(f':rage: {factionRole.mention}: retal on **{v["attacker_name"]} [{v["attacker_id"]}]** https://www.torn.com/profiles.php?XID={v["attacker_id"]} ({delay:.1f} minutes)')
                    past_mentions.append(k)

            await asyncio.sleep(60)

    @commands.command()
    async def chain(self, ctx, *args):
        """ Watch the chain status of a factions and gives notifications
            Use: !chain <factionId> <w=warningTime> <n=notificationTime>
                 factionId: torn id of the faction (by default the author's faction)
                 warningTime: time in seconds before timeout in second for a ping @faction (default 90s)
                 notificationTime: time in seconds between each notifications default (600s)
        """

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

        # default values of the arguments
        deltaW = 90  # warning timeout in seconds
        deltaN = 600  # breathing messages every in second
        faction = ""  # use faction from key

        for arg in args:
            splt = arg.split("=")
            if arg.isdigit():
                faction = int(arg)
                continue
            elif len(splt) != 2:
                await ctx.send(f":chains: argument {arg} ignored")
                continue
            if splt[0] == 'f' and splt[1].isdigit():
                faction = int(splt[1])
            elif splt[0] == 'w' and splt[1].isdigit():
                deltaW = int(splt[1])
            elif splt[0] == 'n' and splt[1].isdigit():
                deltaN = int(splt[1])
            else:
                await ctx.send(f":chains: key/value pair {arg} ignored")

        # Initial call to get faction name
        status, tornId, Name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        url = f'https://api.torn.com/faction/{faction}?selections=basic,chain&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if 'error' in req:
            await ctx.send(f':x: Problem with {name} [{tornId}]\'s key: *{req["error"]["error"]}*')
            return

        # handle no faction
        if req["ID"] is None:
            await ctx.send(f':x: No faction with id {faction}')
            return

        # faction name and role
        factionName = f'{req.get("name")} [{req.get("ID")}]'
        factionRole = get(ctx.guild.roles, name=factionName)

        # if no chain
        if req.get("chain", dict({})).get("current", 0) == 0:
            await ctx.send(f':x: `{factionName}` No chains on the horizon')
            return

        await ctx.send(f":chains: `{factionName}` Start watching: will notify if timeout < {deltaW}s and give status every {deltaN/60:.1f}min")
        lastNotified = datetime.datetime(1970, 1, 1, 0, 0, 0)
        while True:

            # times needed
            now = datetime.datetime.utcnow()
            epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)

            # check if needs to notify still watching

            # check last 50 messages for a stop --- had to do it not async to catch only 1 stop
            history = await ctx.channel.history(limit=50).flatten()
            for m in history:
                if m.content in ["!stopchain", "!stop"]:
                    await m.delete()
                    await ctx.send(f":x: `{factionName}` Stop watching chain")
                    return

            # Initial call to get faction name
            status, tornId, Name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
            if status < 0:
                return

            url = f'https://api.torn.com/faction/{faction}?selections=chain,timestamp&key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # handle API error
            if 'error' in req:
                await ctx.send(f':x: `{factionName}` Master key problem: *{req["error"]["error"]}*')
                return

            # get timings
            timeout = req.get("chain", dict({})).get("timeout", 0)
            cooldown = req.get("chain", dict({})).get("cooldown", 0)
            current = req.get("chain", dict({})).get("current", 0)
            # timeout = 7
            # cooldown = 0
            # current = 10

            # get delay
            nowts = (now - epoch).total_seconds()
            apits = req.get("timestamp")

            delay = int(nowts - apits)
            txtDelay = f"   *API caching delay of {delay}s*" if delay else ""
            deltaLastNotified = int((now - lastNotified).total_seconds())

            # add delay to
            # timeout -= delay

            # if cooldown
            if cooldown > 0:
                await ctx.send(f':x: `{factionName}` Chain at **{current}** in cooldown for {cooldown/60:.1f}min   :cold_face:')
                return

            # if timeout
            elif timeout == 0:
                await ctx.send(f':x: `{factionName}` Chain timed out   :rage:')
                return

            # if warning
            elif timeout < deltaW:
                if factionRole is None:
                    await ctx.send(f':chains: `{factionName}` Chain at **{current}** and timeout in **{timeout}s**{txtDelay}')
                else:
                    await ctx.send(f':chains: {factionRole.mention} Chain at **{current}** and timeout in **{timeout}s**{txtDelay}')

            # if long enough for a notification
            elif deltaLastNotified > deltaN:
                lastNotified = now
                await ctx.send(f':chains: `{factionName}` Chain at **{current}** and timeout in **{timeout}s**{txtDelay}')

            # sleeps
            # print(timeout, deltaW, delay, 30 - delay)
            sleep = max(30, timeout - deltaW)
            print(f"[CHAIN] {ctx.guild} API delay of {delay} seconds, timeout of {timeout}: sleeping for {sleep} seconds")
            await asyncio.sleep(sleep)

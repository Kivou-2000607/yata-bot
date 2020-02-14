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
import includes.formating as fmt


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

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "chain")
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
            await ctx.send(f':x: Problem with {Name} [{tornId}]\'s key: *{req["error"]["error"]}*')
            return

        # handle no faction
        if req["ID"] is None:
            await ctx.send(f':x: No faction with id {req["ID"]}')
            return

        # Set Faction role
        fId = str(req['ID'])
        if fId in config.get("factions", []):
            factionName = f'{config["factions"][fId]} [{fId}]' if config.get("verify", dict({})).get("id", False) else f'{config["factions"][fId]}'
        else:
            factionName = "{name} [{ID}]".format(**req) if config.get("verify", dict({})).get("id", False) else "{name}".format(**req)
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
                await ctx.send(f':x: Problem with {Name} [{tornId}]\'s key: *{req["error"]["error"]}*')
                return

            now = datetime.datetime.utcnow()
            epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
            nowts = (now - epoch).total_seconds()
            for k, v in req["attacks"].items():
                delay = int(nowts - v["timestamp_ended"]) / float(60)
                if k in past_mentions:
                    continue

                if v["defender_faction"] == int(fId) and v["attacker_id"] and float(v["respect_gain"]) > 0 and delay < 5:
                    tleft = 5 - delay
                    if v["attacker_faction"]:
                        await ctx.send(f':rage: {factionRole.mention} {tleft:.1f} minutes left to retal on **{v["attacker_name"]} [{v["attacker_id"]}]** from **{v["attacker_factionname"]} [{v["attacker_faction"]}]** https://www.torn.com/profiles.php?XID={v["attacker_id"]}')
                    else:
                        await ctx.send(f':rage: {factionRole.mention} {tleft:.1f} minutes left to retal on **{v["attacker_name"]} [{v["attacker_id"]}]** https://www.torn.com/profiles.php?XID={v["attacker_id"]}')
                    past_mentions.append(k)

                elif v["attacker_faction"] == int(fId) and float(v["modifiers"]["retaliation"]) > 1 and delay < 5:
                    await ctx.send(f':rage: `{factionRole}` **{v["attacker_name"]} [{v["attacker_id"]}]** retaled on **{v["defender_name"]} [{v["defender_id"]}]** {delay:.1f} minutes ago')
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

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "chain")
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
            await ctx.send(f':x: Problem with {Name} [{tornId}]\'s key: *{req["error"]["error"]}*')
            return

        # handle no faction
        if req["ID"] is None:
            await ctx.send(f':x: No faction with id {faction}')
            return

        # Set Faction role
        fId = str(req['ID'])
        if fId in config.get("factions", []):
            factionName = f'{config["factions"][fId]} [{fId}]' if config.get("verify", dict({})).get("id", False) else f'{config["factions"][fId]}'
        else:
            factionName = "{name} [{ID}]".format(**req) if config.get("verify", dict({})).get("id", False) else "{name}".format(**req)
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

            url = f'https://api.torn.com/faction/{fId}?selections=chain,timestamp&key={key}'
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

    @commands.command()
    async def stopchain(self, ctx):
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "chain"):
            await ctx.send(":x: Chain module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "chain")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        msg = await ctx.send("Gotcha! Just be patient, I'll stop watching on the next notification.")
        await asyncio.sleep(10)
        await msg.delete()

    @commands.command()
    async def stopretal(self, ctx):
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "chain"):
            await ctx.send(":x: Chain module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "chain")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        msg = await ctx.send("Gotcha! Just be patient, I'll stop watching retals on the next notification.")
        await asyncio.sleep(10)
        await msg.delete()

    @commands.command()
    async def fly(self, ctx, *args):
        """Gives faction members flying"""

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "chain")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # send error message if no arg (return)
        if not len(args):
            factionId = None

        # check if arg is int
        elif args[0].isdigit():
            factionId = int(args[0])

        else:
            await ctx.send(":x: Either enter nothing or a faction `!fly <factionId>`.")
            return

        # get configuration for guild
        status, _, _, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        if status in [-1, -2]:
            return

        # Torn API call
        url = f'https://api.torn.com/faction/{factionId}?selections=basic&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                r = await r.json()

        if 'error' in r:
            await ctx.send(f'Error code {r["error"]["code"]}: {r["error"]["error"]}')
            return

        travels = {"Traveling": dict({}), "In": dict({}), "Returning": dict({})}
        for k, v in r.get("members", dict({})).items():
            if v["status"]["state"] in ["Traveling", "Abroad"]:
                type = v["status"]["description"].split(" ")[0]
                dest = v["status"]["description"].split(" ")[-1]
                if dest in travels[type]:
                    travels[type][dest].append(f'{v["name"]+":": <17} {v["status"]["description"]}')
                else:
                    travels[type][dest] = [f'{v["name"]+":": <17} {v["status"]["description"]}']

        dest = ["Mexico", "Islands", "Canada", "Hawaii", "Kingdom", "Argentina", "Switzerland", "Japan", "China", "UAE", "Africa"]
        lst = [f'# {r["name"]} [{r["ID"]}]\n']
        type = ["Returning", "In", "Traveling"]
        for t in type:
            for d in dest:
                for m in travels[t].get(d, []):
                    lst.append(m)
            if len(travels[t]) and t != "Traveling":
                lst.append("---")

        await fmt.send_tt(ctx, lst)

    @commands.command()
    async def hosp(self, ctx, *args):
        """Gives faction members hospitalized"""

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "chain")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # send error message if no arg (return)
        if not len(args):
            factionId = None

        # check if arg is int
        elif args[0].isdigit():
            factionId = int(args[0])

        else:
            await ctx.send(":x: Either enter nothing or a faction `!hosp <factionId>`.")
            return

        # get configuration for guild
        status, _, _, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        if status in [-1, -2]:
            return

        # Torn API call
        url = f'https://api.torn.com/faction/{factionId}?selections=basic&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                r = await r.json()

        if 'error' in r:
            await ctx.send(f':x: Error code {r["error"]["code"]}: {r["error"]["error"]}')
            return

        if r["name"] is None:
            await ctx.send(f':x: No faction with ID {factionId}')
            return

        hosps = {}
        for k, v in r.get("members", dict({})).items():
            if v["status"]["state"] in ["Hospital"]:
                s = v["status"]
                a = v["last_action"]
                hosps[k] = [v["name"], s["description"], fmt.cleanhtml(s["details"]), a["relative"], int(a["timestamp"])]

        lst = [f'Members of **{r["name"]} [{r["ID"]}]** hospitalized: {len(hosps)}']
        for k, v in sorted(hosps.items(), key=lambda x: -x[1][4]):
            # line = f'**{v[0]}**: {v[1]} *{v[2]}* (last action {v[3]}) https://www.torn.com/profiles.php?XID={k}'
            line = f'**{v[0]}**: {v[1]}, *last action {v[3]}*, https://www.torn.com/profiles.php?XID={k}'
            lst.append(line)

        await fmt.send_tt(ctx, lst, tt=False)

    @commands.command(aliases=['ok'])
    async def okay(self, ctx, *args):
        """Gives faction members that are okay"""

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "chain")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # send error message if no arg (return)
        if not len(args):
            factionId = None

        # check if arg is int
        elif args[0].isdigit():
            factionId = int(args[0])

        else:
            await ctx.send(":x: Either enter nothing or a faction `!okay <factionId>`.")
            return

        # get configuration for guild
        status, _, _, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        if status in [-1, -2]:
            return

        # Torn API call
        url = f'https://api.torn.com/faction/{factionId}?selections=basic&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                r = await r.json()

        if 'error' in r:
            await ctx.send(f':x: Error code {r["error"]["code"]}: {r["error"]["error"]}')
            return

        if r["name"] is None:
            await ctx.send(f':x: No faction with ID {factionId}')
            return

        hosps = {}
        for k, v in r.get("members", dict({})).items():
            if v["status"]["state"] in ["Okay"]:
                s = v["status"]
                a = v["last_action"]
                hosps[k] = [v["name"], s["description"], fmt.cleanhtml(s["details"]), a["relative"], int(a["timestamp"])]

        lst = [f'Members of **{r["name"]} [{r["ID"]}]** that are Okay: {len(hosps)}']
        for k, v in sorted(hosps.items(), key=lambda x: -x[1][4]):
            # line = f'**{v[0]}**: {v[1]} *{v[2]}* (last action {v[3]}) https://www.torn.com/profiles.php?XID={k}'
            line = f'**{v[0]}**: {v[1]}, *last action {v[3]}*, https://www.torn.com/profiles.php?XID={k}'
            lst.append(line)

        await fmt.send_tt(ctx, lst, tt=False)

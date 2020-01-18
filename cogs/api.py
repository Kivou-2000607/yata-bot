# import standard modules
import aiohttp
import asyncio
import asyncpg
import json
import re
import os

# import discord modules
import discord
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt


class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

    @commands.command(aliases=['we'])
    async def weaponexp(self, ctx, *args):
        """DM weaponexp to author"""

        # check role and channel
        ALLOWED_CHANNELS = self.bot.get_config(ctx.guild)["admin"].get("channels", ["*"])
        ALLOWED_ROLES = self.bot.get_config(ctx.guild)["admin"].get("roles", ["*"])
        if await checks.channels(ctx, ALLOWED_CHANNELS) and await checks.roles(ctx, ALLOWED_ROLES):
            pass
        else:
            return

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            print(f"[WEAPON EXP] error {status}")
            return

        # make api call
        url = f"https://api.torn.com/user/?selections=discord,weaponexp&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if "error" in req:
            await ctx.author.send(f':x: You asked for your weapons experience but an error occured with your API key: *{req["error"]["error"]}*')
            return

        # if no weapon exp
        if not len(req.get("weaponexp", [])):
            await ctx.author.send(f"no weapon exp")
            return

        # send list
        maxed = []
        tomax = []
        for w in req.get("weaponexp", []):
            if w["exp"] == 100:
                maxed.append(w)
            elif w["exp"] > 4:
                tomax.append(w)

        lst = [f"# {name} [{id}]: weapon experience\n"]

        if len(maxed):
            lst.append("# weapon maxed")
        for i, w in enumerate(maxed):
            lst.append(f'{i+1: >2}: {w["name"]} ({w["exp"]}%)')

        if len(tomax):
            lst.append("# experience > 5%")
        for i, w in enumerate(tomax):
            lst.append(f'{i+1: >2}: {w["name"]} ({w["exp"]}%)')

        await fmt.send_tt(ctx.author, lst)
        return

    @commands.command(aliases=['net'])
    async def networth(self, ctx, *args):
        """DM your networth breakdown (in case you're flying)"""

        # check role and channel
        ALLOWED_CHANNELS = self.bot.get_config(ctx.guild)["admin"].get("channels", ["*"])
        ALLOWED_ROLES = self.bot.get_config(ctx.guild)["admin"].get("roles", ["*"])
        if await checks.channels(ctx, ALLOWED_CHANNELS) and await checks.roles(ctx, ALLOWED_ROLES):
            pass
        else:
            return

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            print(f"[NETWORTH] error {status}")
            return

        # make api call
        url = f"https://api.torn.com/user/?selections=discord,networth&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if "error" in req:
            await ctx.author.send(f':x: You asked for your networth but an error occured with your API key: *{req["error"]["error"]}*')
            return

        # send list
        lst = [f"# {name} [{id}]: Networth breakdown\n"]
        for k, v in req.get("networth", dict({})).items():
            if k in ['total']:
                lst.append('---')
            if int(v):
                a = f"{k}:"
                b = f"${v:,.0f}"
                lst.append(f'{a: <13}{b: >16}')

        await fmt.send_tt(ctx.author, lst)
        return

    @commands.command(aliases=['profile'])
    async def who(self, ctx, *args):
        """Gives information on a user"""

        # check role and channel
        ALLOWED_CHANNELS = self.bot.get_config(ctx.guild)["admin"].get("channels", ["*"])
        ALLOWED_ROLES = self.bot.get_config(ctx.guild)["admin"].get("roles", ["*"])
        if await checks.channels(ctx, ALLOWED_CHANNELS) and await checks.roles(ctx, ALLOWED_ROLES):
            pass
        else:
            return

        # init variables
        helpMsg = f":x: You have to mention a member `!who @Kivou [2000607]` or enter a Torn ID or `!who 2000607`."

        # send error message if no arg (return)
        if not len(args):
            await ctx.send(helpMsg)
            return

        # check if arg is int
        elif args[0].isdigit():
            tornId = int(args[0])

        # check if arg is a mention of a discord user ID
        elif args[0][:2] == '<@':
            discordId = int(args[0][2:-1].replace("!", "").replace("&", ""))
            member = ctx.guild.get_member(discordId)

            # check if member
            if member is None:
                await ctx.send(f":x: Couldn't find discord member: {discordId}. Try `!who <torn ID>`.")
                return

            # try to parse Torn user ID
            regex = re.findall(r'\[(\d{1,7})\]', member.display_name)
            if len(regex) == 1 and regex[0].isdigit():
                tornId = int(regex[0])
            else:
                await ctx.send(f":x: `{member.display_name}` could not find Torn ID within their display name. Try `!who <Torn ID>`.")
                return

        # other cases I didn't think of
        else:
            await ctx.send(helpMsg)
            return

        # at this point tornId should be a interger corresponding to a torn ID

        # get configuration for guild
        status, _, key = await self.bot.get_master_key(ctx.guild)
        if status == -1:
            await ctx.send(":x: No master key given")
            return

        # Torn API call
        url = f'https://api.torn.com/user/{tornId}?selections=profile,personalstats&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                r = await r.json()

        if 'error' in r:
            await ctx.send(f'Error code {r["error"]["code"]}: {r["error"]["error"]}')
            await ctx.send(f'Check the profile by yourself https://www.torn.com/profiles.php?XID={tornId}')
            return

        links = {}
        linki = 1
        lst = []

        # status
        lst.append(f'Name: {r["name"]} [{r["player_id"]}]    <{linki}>')
        links[linki] = f'https://www.torn.com/profiles.php?XID={tornId}'
        linki += 1
        lst.append(f'Action: {r["last_action"]["relative"]}')
        s = r["status"]
        # lst.append(f'State: {s["state"]}')
        lst.append(f'Status: {s["description"]}')
        if s["details"]:
            lst.append(f'Details: {fmt.cleanhtml(s["details"])}')
        p = 100 * r['life']['current'] // r['life']['maximum']
        i = int(p * 20 / 100)
        lst.append(f'Life: {r["life"]["current"]:,d}/{r["life"]["maximum"]:,d} [{"+" * i}{"-" * (20 - i)}]')
        lst.append('---')

        # levels
        lst.append(f'Level: {r["level"]}')
        lst.append(f'Rank: {r["rank"]}')
        lst.append(f'Age: {r["age"]:,d} days old')
        lst.append(f'Networth: ${r["personalstats"]["networth"]:,d}')
        lst.append(f'X-R-SE: {r["personalstats"].get("xantaken", 0):,d} {r["personalstats"].get("refills", 0):,d} {r["personalstats"].get("statenhancersused", 0):,d}')
        lst.append('---')

        # faction
        if int(r["faction"]["faction_id"]):
            f = r["faction"]
            lst.append(f'Faction: {f["faction_name"]} [{f["faction_id"]}]    <{linki}>')
            links[linki] = f'https://www.torn.com/factions.php?&ID={f["faction_id"]}'
            linki += 1
            lst.append(f'Position: {f["position"]} since {f["days_in_faction"]} days')
            lst.append('---')

        # company
        if int(r["job"]["company_id"]):
            j = r["job"]
            lst.append(f'Company: {j["position"]} at {j["company_name"]} [{j["company_id"]}]    <{linki}>')
            links[linki] = f'https://www.torn.com/joblist.php?#!p=corpinfo&ID={j["company_id"]}'
            linki += 1
            lst.append('---')

        # social
        lst.append(f'Friends: {r["friends"]:,d}')
        lst.append(f'Enemies: {r["enemies"]:,d}')
        if r["forum_posts"]:
            lst.append(f'Karma: {r["karma"]:,d} ({100 * r["karma"] // r["forum_posts"]}%)')
        else:
            lst.append(f'Karma: No forum post')

        s = r["married"]
        if s["spouse_id"]:
            lst.append(f'Married: {s["spouse_name"]} [{s["spouse_id"]}] for {s["duration"]:,d} days    <{linki}>')
            links[linki] = f'https://www.torn.com/profiles.php?&XID={s["spouse_id"]}'
            linki += 1

        await fmt.send_tt(ctx, lst)
        for k, v in links.items():
            await ctx.send(f'<{k}> {v}')

    @commands.command()
    async def fly(self, ctx, *args):
        """Gives faction members flying"""

        # check role and channel
        ALLOWED_CHANNELS = self.bot.get_config(ctx.guild)["admin"].get("channels", ["*"])
        ALLOWED_ROLES = self.bot.get_config(ctx.guild)["admin"].get("roles", ["*"])
        if await checks.channels(ctx, ALLOWED_CHANNELS) and await checks.roles(ctx, ALLOWED_ROLES):
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
        status, _, key = await self.bot.get_master_key(ctx.guild)
        if status == -1:
            await ctx.send(":x: No master key given")
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

        # check role and channel
        ALLOWED_CHANNELS = self.bot.get_config(ctx.guild)["admin"].get("channels", ["*"])
        ALLOWED_ROLES = self.bot.get_config(ctx.guild)["admin"].get("roles", ["*"])
        if await checks.channels(ctx, ALLOWED_CHANNELS) and await checks.roles(ctx, ALLOWED_ROLES):
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
        status, _, key = await self.bot.get_master_key(ctx.guild)
        if status == -1:
            await ctx.send(":x: No master key given")
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

        # check role and channel
        ALLOWED_CHANNELS = self.bot.get_config(ctx.guild)["admin"].get("channels", ["*"])
        ALLOWED_ROLES = self.bot.get_config(ctx.guild)["admin"].get("roles", ["*"])
        if await checks.channels(ctx, ALLOWED_CHANNELS) and await checks.roles(ctx, ALLOWED_ROLES):
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
        status, _, key = await self.bot.get_master_key(ctx.guild)
        if status == -1:
            await ctx.send(":x: No master key given")
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

    @tasks.loop(minutes=1)
    async def notify(self):
        print("[NOTIFICATIONS] start task")

        # YATA guild
        # guild = get(self.bot.guilds, id=432226682506575893)  # nub navy guild
        guild = get(self.bot.guilds, id=581227228537421825)  # yata guild

        # connect to YATA database of notifiers
        db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
        dbname = db_cred["dbname"]
        del db_cred["dbname"]
        sql = 'SELECT "tId", "dId", "notifications", "apikey" FROM player_player WHERE "activateNotifications" = True;'
        con = await asyncpg.connect(database=dbname, **db_cred)

        # async loop over notifiers
        async with con.transaction():
            async for record in con.cursor(sql, prefetch=50, timeout=2):
                # get corresponding discord member
                member = get(guild.members, id=record["dId"])
                if member is None:
                    print(f'[NOTIFICATIONS] ignore member Discord: `{record["dId"]}` Torn: `{record["tId"]}`')
                    continue

                try:

                    # get notifications preferences
                    notifications = json.loads(record["notifications"])

                    # get selections for Torn API call
                    keys = []
                    if "event" in notifications:
                        keys.append("events")
                        keys.append("notifications")
                    if "message" in notifications:
                        keys.append("messages")
                        keys.append("notifications")
                    if "award" in notifications:
                        keys.append("notifications")
                    if "energy" in notifications:
                        keys.append("bars")
                    if "nerve" in notifications:
                        keys.append("bars")
                    if "chain" in notifications:
                        keys.append("bars")
                    if "education" in notifications:
                        keys.append("education")
                    if "bank" in notifications:
                        keys.append("money")
                    if "drug" in notifications:
                        keys.append("cooldowns")
                    if "medical" in notifications:
                        keys.append("cooldowns")
                    if "booster" in notifications:
                        keys.append("cooldowns")
                    if "travel" in notifications:
                        keys.append("travel")

                    # make Torn API call
                    url = f'https://api.torn.com/user/?selections={",".join(list(set(keys)))}&key={record["key"]}'
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as r:
                            req = await r.json()

                    # notify event
                    if "event" in notifications:
                        if not req["notifications"]["events"]:
                            notifications["event"] = dict({})
                        else:
                            # loop over events
                            for k, v in req["events"].items():
                                # if new event not notified -> notify
                                if not v["seen"] and k not in notifications["event"]:
                                    await member.send(fmt.cleanhtml(v["event"]).replace(" [View]", ""))
                                    notifications["event"][k] = True

                                # if seen even already notified -> clean table
                                elif v["seen"] and k in notifications["event"]:
                                    del notifications["event"][k]

                    # notify message
                    if "message" in notifications:
                        if not req["notifications"]["messages"]:
                            notifications["messages"] = dict({})
                        else:
                            # loop over messages
                            for k, v in req["messages"].items():
                                # if new event not notified -> notify
                                if not v["seen"] and k not in notifications["message"]:
                                    await member.send(f'New message from {v["name"]}: {v["title"]}')
                                    notifications["message"][k] = True

                                # if seen even already notified -> clean table
                                elif v["seen"] and k in notifications["message"]:
                                    del notifications["message"][k]

                    # notify awards
                    if "award" in notifications:
                        if req["notifications"]["awards"]:
                            # if new award or different number of awards
                            if not notifications["award"].get("notified", False) or notifications["award"].get("notified") != req["notifications"]["awards"]:
                                s = "s" if req["notifications"]["awards"] > 1 else ""
                                await member.send(f'You have {req["notifications"]["awards"]} new award{s}')
                                notifications["award"]["notified"] = req["notifications"]["awards"]

                        else:
                            notifications["award"] = dict({})

                    # notify energy
                    if "energy" in notifications:
                        if req["energy"]["fulltime"] < 90:
                            if not notifications["energy"].get("notified", False):
                                await member.send(f'Energy at {req["energy"]["current"]} / {req["energy"]["maximum"]}')
                            notifications["energy"]["notified"] = True

                        else:
                            notifications["energy"] = dict({})

                    # notify nerve
                    if "nerve" in notifications:
                        if req["nerve"]["fulltime"] < 90:
                            if not notifications["nerve"].get("notified", False):
                                await member.send(f'Nerve at {req["nerve"]["current"]} / {req["nerve"]["maximum"]}')
                            notifications["nerve"]["notified"] = True

                        else:
                            notifications["nerve"] = dict({})

                    # notify chain
                    if "chain" in notifications:
                        if req["chain"]["timeout"] < 90 and req["chain"]["current"] > 10:
                            if not notifications["chain"].get("notified", False):
                                await member.send(f'Chain timeout in {req["chain"]["timeout"]} seconds')
                            notifications["chain"]["notified"] = True

                        else:
                            notifications["chain"] = dict({})

                    # notify education
                    if "education" in notifications:
                        if req["education_timeleft"] < 90:
                            if not notifications["education"].get("notified", False):
                                await member.send(f'Education ends in {req["education_timeleft"]} seconds')
                            notifications["education"]["notified"] = True

                        else:
                            notifications["education"] = dict({})

                    # notify bank
                    if "bank" in notifications:
                        if req["city_bank"]["time_left"] < 90:
                            if not notifications["bank"].get("notified", False):
                                await member.send(f'Bank investment ends in {req["city_bank"]["time_left"]} seconds (${req["city_bank"]["amount"]:,.0f})')
                            notifications["bank"]["notified"] = True

                        else:
                            notifications["bank"] = dict({})

                    # notify drug
                    if "drug" in notifications:
                        if req["cooldowns"]["drug"] < 90:
                            if not notifications["drug"].get("notified", False):
                                await member.send(f'Drug cooldown ends in {req["cooldowns"]["drug"]} seconds')
                            notifications["drug"]["notified"] = True

                        else:
                            notifications["drug"] = dict({})

                    # notify medical
                    if "medical" in notifications:
                        if req["cooldowns"]["medical"] < 90:
                            if not notifications["medical"].get("notified", False):
                                await member.send(f'Medical cooldown ends in {req["cooldowns"]["medical"]} seconds')
                            notifications["medical"]["notified"] = True

                        else:
                            notifications["medical"] = dict({})

                    # notify booster
                    if "booster" in notifications:
                        if req["cooldowns"]["booster"] < 90:
                            if not notifications["booster"].get("notified", False):
                                await member.send(f'Booster cooldown ends in {req["cooldowns"]["booster"]} seconds')
                            notifications["booster"]["notified"] = True

                        else:
                            notifications["booster"] = dict({})

                    # notify travel
                    if "travel" in notifications:
                        if req["travel"]["time_left"] < 90:
                            if not notifications["travel"].get("destination", False):
                                await member.send(f'Landing in {req["travel"]["destination"]} in {req["travel"]["time_left"]} seconds')
                            notifications["travel"] = req["travel"]

                        else:
                            notifications["travel"] = dict({})

                    # update notifications in YATA's database
                    await con.execute('UPDATE player_player SET "notifications"=$1 WHERE "dId"=$2', json.dumps(notifications), member.id)

                except BaseException as e:
                    print(f"[NOTIFICATIONS] Error {member}: {e}")

        await con.close()

    @notify.before_loop
    async def before_notify(self):
        print('[NOTIFICATIONS] waiting...')
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

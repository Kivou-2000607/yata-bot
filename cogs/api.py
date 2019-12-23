# import standard modules
import aiohttp
import re

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt


class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['we'])
    async def weaponexp(self, ctx, *args):
        """DM weaponexp to author"""

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

    @commands.command()
    async def who(self, ctx, *args):
        """Gives information on a user"""
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
        lst.append(f'Married: {s["spouse_name"]} [{s["spouse_id"]}] for {s["duration"]:,d} days    <{linki}>')
        links[linki] = f'https://www.torn.com/profiles.php?&XID={s["spouse_id"]}'
        linki += 1

        await fmt.send_tt(ctx, lst)
        for k, v in links.items():
            await ctx.send(f'<{k}> {v}')

    @commands.command()
    async def fly(self, ctx, *args):
        """Gives faction members flying"""

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

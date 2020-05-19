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
import datetime
import json
import re
import logging

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks
from discord import Embed

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt
from includes.yata_db import push_configurations


class Chain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.retalTask.start()

    def cog_unload(self):
        self.retalTask.cancel()

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def chain(self, ctx, *args):
        """ Watch the chain status of a factions and gives notifications
            Use: !chain <factionId> <@Role>
                 factionId: torn id of the faction (by default the author's faction)
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
        role = None

        for arg in args:
            match = re.match(r'<@&([0-9])+>', arg)
            if match is not None:
                role = match.string
                logging.info(f"role = {role}")
            elif arg.isdigit():
                faction = int(arg)
                logging.info(f"factionId = {faction}")
                continue
            else:
                await ctx.send(f":x: ignore argument {arg}. syntax is ```!chain <factionId> <@Role>```")

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
        factionName = "{name} [{ID}]".format(**req)

        # if no chain
        if req.get("chain", dict({})).get("current", 0) == 0:
            await ctx.send(f':x: `{factionName}` No chains on the horizon')
            return

        if role is None:
            await ctx.send(f":chains: `{factionName}` Start watching")
        else:
            await ctx.send(f":chains: `{factionName}` Start watching. Will notify {role} on timeout.")
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
                if role is None:
                    await ctx.send(f':chains: `{factionName}` Chain at **{current}** and timeout in **{timeout}s**{txtDelay}')
                else:
                    await ctx.send(f':chains: `{factionName}` {role} Chain at **{current}** and timeout in **{timeout}s**{txtDelay}')

            # if long enough for a notification
            elif deltaLastNotified > deltaN:
                lastNotified = now
                await ctx.send(f':chains: `{factionName}` Chain at **{current}** and timeout in **{timeout}s**{txtDelay}')

            # sleeps
            # logging.info(timeout, deltaW, delay, 30 - delay)
            sleep = max(30, timeout - deltaW)
            logging.info(f"[CHAIN] {ctx.guild} API delay of {delay} seconds, timeout of {timeout}: sleeping for {sleep} seconds")
            await asyncio.sleep(sleep)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
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
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
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
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
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
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
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

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def vault(self, ctx, *args):
        """ For AA users: gives the vault balance of a user
        """
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "chain"):
            await ctx.send(":x: Chain module not activated")
            return

        if len(args) and args[0].isdigit():
            checkVaultId = str(args[0])
        else:
            await ctx.send(":x: Enter a torn id `!vault <tornId>`")
            return

        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)

        if status != 0:
            return

        url = f'https://api.torn.com/faction/?selections=basic,donations&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        if 'error' in req:
            await ctx.send(f':x: Error code {req["error"]["code"]}: {req["error"]["error"]}')
            return

        factionName = f'{req["name"]} [{req["ID"]}]'
        members = req["members"]
        donations = req["donations"]
        lst = [f'Faction: {factionName}']
        if checkVaultId in members:
            member = members[checkVaultId]
            lst.append(f'User: {member["name"]} [{checkVaultId}]')
            lst.append(f'Action: {member["last_action"]["relative"]}')
        else:
            lst.append(f'User: Member [{checkVaultId}]')
            lst.append(f'Action: Not in faction')

        if checkVaultId in donations:
            member = donations[checkVaultId]
            lst.append(f'Money: ${member["money_balance"]:,d}')
            lst.append(f'Points: {member["points_balance"]:,d}')
        else:
            lst.append(f'Money: No vault records')
            lst.append(f'Points: No vault records')

        await fmt.send_tt(ctx, lst)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def retals(self, ctx):
        """ list all current retal watching
        """
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "chain"):
            await ctx.send(":x: Chain module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = ["yata-admin"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        retals = config["chain"].get("retal")
        if retals is None or not len(retals):
            await ctx.send("You're not watching any retals.")
        for v in retals.values():
            channel = get(ctx.guild.channels, id=v["channelId"])
            admin = get(ctx.guild.channels, name="yata-admin")
            notify = 'nobody' if v["roleId"] is None else f'<@&{v["roleId"]}>'
            lst = [f'{v["name"]} [{v["tornId"]}] is notifying {notify} for retals in #{channel}.',
                   f'It can be stopped either by them typing `!retal` in #{channel} or anyone typing `!stopretal {v["tornId"]}` in #{admin}.']
            await ctx.send("\n".join(lst))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def stopretal(self, ctx, *args):
        """ force stop a retal watching (for admin)
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

        if len(args) and args[0].isdigit():
            tornId = str(args[0])
        else:
            admin = get(ctx.guild.channels, name="yata-admin")
            lst = ["If you want to stop watching retals you started simply type `!retal` in the channel you started it.",
                   f"If you want to stop watching retals someone else started you need to enter a user Id in {admin.mention}.",
                   f"Type `!retals` in {admin.mention} for more detals."]
            await ctx.send("\n".join(lst))
            return

        retals = config["chain"].get("retal")
        if retals is None:
            await ctx.send("You're not watching any retals.")
        elif str(tornId) not in retals:
            await ctx.send(f"Player {tornId} was not watching any retals.")
        else:
            v = config["chain"]["retal"][str(tornId)]
            name = v.get("name")
            channel = get(ctx.guild.channels, id=v["channelId"])
            del config["chain"]["retal"][str(tornId)]
            if channel is not None:
                await channel.send(f':x: **{name} [{tornId}]**: Stop watching retals on behalf of {ctx.author.nick}.')

            self.bot.configs[str(ctx.guild.id)] = config
            await push_configurations(self.bot.bot_id, self.bot.configs)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def retal(self, ctx, *args):
        """ start / stop watching for retals
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

        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, delError=True)

        # just to be sure
        tornId = str(tornId)

        if config["chain"].get("retal") is None:
            config["chain"]["retal"] = dict({})

        if status == 0:

            if len(args) and args[0].replace("<@&", "").replace(">", "").isdigit():
                roleId = int(args[0].replace("<@&", "").replace(">", ""))
            else:
                roleId = None

            if str(tornId) in config["chain"].get("retal"):
                del config["chain"]["retal"][str(tornId)]
                await ctx.send(f':x: **{name} [{tornId}]**: Stop watching retals.')
            else:
                retal = {"name": name,
                         "tornId": str(tornId),
                         "key": key,
                         "roleId": roleId,
                         "channelId": ctx.channel.id}
                config["chain"]["retal"][str(tornId)] = retal

                notified = "Nobody" if roleId is None else f"<@&{roleId}>"
                await ctx.send(f':white_check_mark: **{name} [{tornId}]** Start watching retals for their faction in {ctx.channel.mention}. {notified} will be notified.')

        else:
            if str(tornId) in config["chain"].get("retal"):
                del config["chain"]["retal"][str(tornId)]
                await ctx.send(f':x: **{name} [{tornId}]**: Stop watching retals.')

        self.bot.configs[str(ctx.guild.id)] = config
        await push_configurations(self.bot.bot_id, self.bot.configs)

    async def _retal(self, guild, retal):

        key = retal.get("key")
        tornId = str(retal.get("tornId"))
        name = retal.get("name")
        roleId = retal.get("roleId")
        channelId = retal.get("channelId")

        channel = get(guild.channels, id=channelId)
        notified = " " if roleId is None else f" <@&{roleId}> "
        if channel is None:
            return False

        url = f'https://api.torn.com/faction/?selections=basic,attacks&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if 'error' in req:
            await channel.send(f':x: `{name} [{tornId}]` Problem with their key for retal: *{req["error"]["error"]}*')
            if req["error"]["code"] in [7]:
                await channel.send("It means that you don't have the required AA permission (AA for API access) for this API request. This is an in-game permission that faction leader and co-leader can grant to their members.")

            if req["error"]["code"] in [1, 2, 6, 7, 10]:
                await channel.send(f':x: `{name} [{tornId}]` retal stopped...')
                return False
            else:
                return True

        if not int(req["ID"]):
            await channel.send(f':x: `{name} [{tornId}]` No factions found... retal stopped...')
            return False

        fId = req["ID"]
        fName = req["name"]

        now = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        nowts = (now - epoch).total_seconds()
        if "mentions" not in retal:
            retal["mentions"] = []
        for k, v in req["attacks"].items():
            delay = int(nowts - v["timestamp_ended"]) / float(60)
            if str(k) in retal["mentions"]:
                continue

            if v["defender_faction"] == int(fId) and v["attacker_id"] and not float(v["modifiers"]["overseas"]) > 1 and float(v["respect_gain"]) > 0 and delay < 5:
                tleft = 5 - delay
                timeout = fmt.ts_to_datetime(int(v["timestamp_ended"]) + 5 * 60, fmt="time")


                embed = Embed(title=f'{fName} have {tleft:.1f} minutes to retal',
                              description=f'Target: [{v["attacker_name"]} [{v["attacker_id"]}]](https://www.torn.com/profiles.php?XID={v["attacker_id"]})',
                              color=550000)

                embed.add_field(name='Timeout', value=f'{timeout} TCT')
                message = f':rage:{notified}{fName} can retal on **{v["attacker_name"]} [{v["attacker_id"]}]**'
                if v["attacker_faction"]:
                    message += f' from **{v["attacker_factionname"]} [{v["attacker_faction"]}]**'
                    embed.add_field(name='Faction', value=f'[{v["attacker_factionname"]} [{v["attacker_faction"]}]](https://www.torn.com/factions.php?step=profile&ID={v["attacker_faction"]})')
                else:
                    embed.add_field(name='Faction', value=f'None')

                embed.add_field(name='Defender', value=f'[{v["defender_name"]} [{v["defender_id"]}]](https://www.torn.com/profiles.php?XID={v["defender_id"]})')
                embed.add_field(name='Chain Bonus', value=f'{v["chain"]} (x {v["modifiers"]["chainBonus"]})')
                embed.add_field(name='Respect', value=f'{v["respect_gain"]:.2f}')
                embed.add_field(name=f'Log', value=f'[{v["result"]}](https://www.torn.com/loader.php?sid=attackLog&ID={v["code"]})')

                await channel.send(message, embed=embed)
                retal["mentions"].append(str(k))

            elif v["attacker_faction"] == int(fId) and float(v["modifiers"]["retaliation"]) > 1 and delay < 5:
                attack_time = fmt.ts_to_datetime(int(v["timestamp_ended"]), fmt="time")
                await channel.send(f':middle_finger: {v["attacker_name"]} retaled on **{v["defender_name"]} [{v["defender_id"]}]** {delay:.1f} minutes ago at {attack_time} TCT')
                retal["mentions"].append(str(k))

        # clean mentions
        cleanedMentions = []
        for k in retal["mentions"]:
            if str(k) in req["attacks"]:
                cleanedMentions.append(str(k))

        retal["mentions"] = cleanedMentions

        # delete old messages
        # fminutes = now - datetime.timedelta(minutes=5)
        # async for message in channel.history(limit=50, before=fminutes):
        #     if message.author.bot:
        #         await message.delete()

        return True

    @tasks.loop(seconds=60)
    async def retalTask(self):
        # logging.info("[retalTask] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=150):
            try:
                # ignore servers with no verify
                if not self.bot.check_module(guild, "chain"):
                    continue

                # ignore servers with no option daily check
                config = self.bot.get_config(guild)
                if not config["chain"].get("retal", False):
                    continue

                # logging.info(f"[retalTask] retal {guild}: start")

                # iteration over all members asking for retal watch
                guild = self.bot.get_guild(guild.id)
                todel = []
                for tornId, retal in config["chain"]["retal"].items():
                    # logging.info(f"[retalTask] retal {guild}: {tornId}: {retal}")

                    # call retal faction
                    status = await self._retal(guild, retal)

                    # update metionned messages (but don't save in database, will remention in case of reboot)
                    if status:
                        self.bot.configs[str(guild.id)]["chain"]["retal"][str(tornId)] = retal
                    else:
                        todel.append(str(tornId))

                for d in todel:
                    del self.bot.configs[str(guild.id)]["chain"]["retal"][d]
                    await push_configurations(self.bot.bot_id, self.bot.configs)

                # logging.info(f"[retalTask] retal {guild}: end")

            except BaseException as e:
                logging.error(f'[retalTask] {guild} [{guild.id}]: {e}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on retal task"}
                await self.bot.send_log_main(e, headers=headers)

    @retalTask.before_loop
    async def before_retalTask(self):
        logging.info('[retalTask] waiting...')
        await self.bot.wait_until_ready()

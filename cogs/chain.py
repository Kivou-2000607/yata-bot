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
import html

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks
from discord import Embed

# import bot functions and classes
from inc.yata_db import set_configuration
from inc.handy import *


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
        logging.info(f'[chain/chain] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
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
                logging.debug(f"[chain/chain] role = {role}")
            elif arg.isdigit():
                faction = int(arg)
                logging.debug(f"[chain/chain] factionId = {faction}")
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
            logging.debug(f"[chain/chain] {ctx.guild} API delay of {delay} seconds, timeout of {timeout}: sleeping for {sleep} seconds")
            await asyncio.sleep(sleep)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    @commands.guild_only()
    async def stopchain(self, ctx):
        logging.info(f'[chain/stopchain] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        msg = await ctx.send("Gotcha! Just be patient, I'll stop watching on the next notification.")
        await asyncio.sleep(10)
        await msg.delete()

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def fly(self, ctx, *args):
        """Gives faction members flying"""
        logging.info(f'[chain/fly] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
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

        await send_tt(ctx, lst)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def hosp(self, ctx, *args):
        """Gives faction members hospitalized"""
        logging.info(f'[chain/hosp] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
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
                hosps[k] = [v["name"], s["description"], cleanhtml(s["details"]), a["relative"], int(a["timestamp"])]

        lst = [f'Members of **{r["name"]} [{r["ID"]}]** hospitalized: {len(hosps)}']
        for k, v in sorted(hosps.items(), key=lambda x: -x[1][4]):
            # line = f'**{v[0]}**: {v[1]} *{v[2]}* (last action {v[3]}) https://www.torn.com/profiles.php?XID={k}'
            line = f'**{v[0]}**: {v[1]}, *last action {v[3]}*, https://www.torn.com/profiles.php?XID={k}'
            lst.append(line)

        await send_tt(ctx, lst, tt=False)

    @commands.command(aliases=['ok'])
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def okay(self, ctx, *args):
        """Gives faction members that are okay"""
        logging.info(f'[chain/okay] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
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
                hosps[k] = [v["name"], s["description"], cleanhtml(s["details"]), a["relative"], int(a["timestamp"])]

        lst = [f'Members of **{r["name"]} [{r["ID"]}]** that are Okay: {len(hosps)}']
        for k, v in sorted(hosps.items(), key=lambda x: -x[1][4]):
            # line = f'**{v[0]}**: {v[1]} *{v[2]}* (last action {v[3]}) https://www.torn.com/profiles.php?XID={k}'
            line = f'**{v[0]}**: {v[1]}, *last action {v[3]}*, https://www.torn.com/profiles.php?XID={k}'
            lst.append(line)

        await send_tt(ctx, lst, tt=False)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def vault(self, ctx, *args):
        """ For AA users: gives the vault balance of a user
        """
        logging.info(f'[chain/vault] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
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

        await send_tt(ctx, lst)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def retal(self, ctx, *args):
        """ start / stop watching for retals
        """
        logging.info(f'[chain/retal] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        # init currents
        if "currents" not in self.bot.configurations[ctx.guild.id]["chain"]:
            self.bot.configurations[ctx.guild.id]["chain"]["currents"] = {}

        currents = config.get("currents", {})

        # delete if already exists
        if str(ctx.author.id) in currents:
            lst = ["```md", "# Tracking retals"]
            for k, v in [(k, v) for k, v in currents[str(ctx.author.id)].items() if k != "mentions"]:
                lst.append(f'< {k} > {v[2]}{v[1]} [{v[0]}]')
            lst += ['', '<STOP>', "```"]
            await ctx.channel.send("\n".join(lst))
            del self.bot.configurations[ctx.guild.id]["chain"]["currents"][str(ctx.author.id)]
            await set_configuration(self.bot.bot_id, ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            return

        current = {"channel": [str(ctx.channel.id), f'{ctx.channel.name}', '#'],
                   "discord_user": [str(ctx.author.id), f'{ctx.author}', '']}

        # get torn user
        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author)
        if status < 0:
            lst = ['```md', f'# Tracking retals', f'< error > could not get {ctx.author}\'s API key```']
            await ctx.channel.send("\n".join(lst))
            return
        current["torn_user"] = [str(tornId), name, '', key]

        # get role
        if len(args) and args[0].replace("<@&", "").replace(">", "").isdigit():
            role = get(ctx.guild.roles, id=int(int(args[0].replace("<@&", "").replace(">", ""))))
        else:
            role = None

        if role is not None:
            current["role"] = [str(role.id), f'{role}', '@']

        lst = ["```md", "# Tracking retals"]
        for k, v in current.items():
            lst.append(f'< {k} > {v[2]}{v[1]} [{v[0]}]')
        lst += ['', '<START>', "```"]
        await ctx.channel.send("\n".join(lst))
        self.bot.configurations[ctx.guild.id]["chain"]["currents"][str(ctx.author.id)] = current
        await set_configuration(self.bot.bot_id, ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])

    async def _retal(self, guild, retal):

        # get channel
        channelId = retal.get("channel")[0] if len(retal.get("channel", {})) else None
        channel = get(guild.channels, id=int(channelId))
        if channel is None:
            return False

        # get discord member
        discord_id = retal.get("discord_user")[0] if len(retal.get("discord_user", {})) else "0"
        discord_member = get(guild.members, id=int(discord_id))
        if discord_member is None:
            await channel.send(f'```md\n# Tracking retals\n< error > discord member {discord_member} not found\n\n<STOP>```')
            return False

        # get torn id, name and key
        # # status, tornId, name, key = await self.bot.get_user_key(False, discord_member, guild=guild)
        #
        # if status < 0:
        #     await channel.send(f'```md\n# Tracking retals\n< error > could not find torn identity of discord member {discord_member}```')
        #     return False

        if len(retal.get("torn_user")) < 4:
            await channel.send(f'```md\n# Tracking retals\n< error > Sorry it\'s my bad. I had to change how the tracking is built. You can launch it again now.\nKivou\n\n<STOP>```')
            return False

        tornId = retal.get("torn_user")[0]
        name = retal.get("torn_user")[1]
        key = retal.get("torn_user")[3]

        roleId = retal.get("role")[0] if len(retal.get("role", {})) else None
        notified = " " if roleId is None else f" <@&{roleId}> "

        url = f'https://api.torn.com/faction/?selections=basic,attacks&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if 'error' in req:
            lst = [f'```md', f'# Tracking retals\n< error > Problem with {name} [{tornId}]\'s key: {req["error"]["error"]}']
            if req["error"]["code"] in [7]:
                lst.append("It means that you don't have the required AA permission (AA for API access) for this API request")
                lst.append("This is an in-game permission that faction leader and co-leader can grant to their members")

            if req["error"]["code"] in [1, 2, 6, 7, 10]:
                lst += ["", "<STOP>", "```"]
                await channel.send("\n".join(lst))
                return False
            else:
                lst += ["", "<CONTINUE>", "```"]
                await channel.send("\n".join(lst))
                return True

        if req is None or "ID" not in req:
            await channel.send(f'```md\n# Tracking retals\n< error > wrong API output\n\n{hide_key(req)}\n\n<CONTINUE>```')
            return True

        if not int(req["ID"]):
            await channel.send(f'```md\n# Tracking retals\n< error > no faction found for {name} {tornId}\n\n<STOP>```')
            return False

        # faction id and name
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
                timeout = ts_to_datetime(int(v["timestamp_ended"]) + 5 * 60, fmt="time")

                embed = Embed(title=f'{html.unescape(fName)} have {tleft:.1f} minutes to retal',
                              description=f'Target: [{v["attacker_name"]} [{v["attacker_id"]}]](https://www.torn.com/profiles.php?XID={v["attacker_id"]})',
                              color=550000)

                embed.add_field(name='Timeout', value=f'{timeout} TCT')
                message = f':rage:{notified}{html.unescape(fName)} can retal on **{v["attacker_name"]} [{v["attacker_id"]}]**'
                if v["attacker_faction"]:
                    message += f' from **{html.unescape(v["attacker_factionname"])} [{v["attacker_faction"]}]**'
                    embed.add_field(name='Faction', value=f'[{html.unescape(v["attacker_factionname"])} [{v["attacker_faction"]}]](https://www.torn.com/factions.php?step=profile&ID={v["attacker_faction"]})')
                else:
                    embed.add_field(name='Faction', value=f'None')

                embed.add_field(name='Defender', value=f'[{v["defender_name"]} [{v["defender_id"]}]](https://www.torn.com/profiles.php?XID={v["defender_id"]})')
                embed.add_field(name='Chain Bonus', value=f'{v["chain"]} (x {v["modifiers"]["chainBonus"]})')
                embed.add_field(name='Respect', value=f'{v["respect_gain"]:.2f}')
                embed.add_field(name=f'Log', value=f'[{v["result"]}](https://www.torn.com/loader.php?sid=attackLog&ID={v["code"]})')

                await channel.send(message, embed=embed)
                retal["mentions"].append(str(k))

            elif v["attacker_faction"] == int(fId) and float(v["modifiers"]["retaliation"]) > 1 and delay < 5:
                attack_time = ts_to_datetime(int(v["timestamp_ended"]), fmt="time")
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
        logging.debug("[chain/retal-notifications] start task")

        # iteration over all guilds
        for guild in self.bot.get_guilds_by_module("chain"):
            try:

                config = self.bot.get_guild_configuration_by_module(guild, "chain", check_key="currents")
                if not config:
                    logging.info(f"[chain/retal-notifications] No retal for {guild}")
                    continue
                logging.info(f"[chain/retal-notifications] retal for {guild}")

                # iteration over all members asking for retal watch
                # guild = self.bot.get_guild(guild.id)
                todel = []
                for discord_user_id, retal in config["currents"].items():
                    logging.debug(f"[chain/retal-notifications] {guild}: {retal}")

                    # call retal faction
                    status = await self._retal(guild, retal)

                    # update metionned messages (but don't save in database, will remention in case of reboot)
                    if status:
                        self.bot.configurations[guild.id]["chain"]["currents"][discord_user_id] = retal
                    else:
                        todel.append(discord_user_id)

                for d in todel:
                    del self.bot.configurations[guild.id]["chain"]["currents"][d]

                await set_configuration(self.bot.bot_id, guild.id, guild.name, self.bot.configurations[guild.id])

            except BaseException as e:
                logging.error(f'[chain/retal-notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on retal task"}
                await self.bot.send_log_main(e, headers=headers, full=True)

    @retalTask.before_loop
    async def before_retalTask(self):
        await self.bot.wait_until_ready()

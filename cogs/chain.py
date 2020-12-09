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
                await self.bot.send_error_message(ctx.channel, f'Ignore argument {arg}. The syntax is ```!chain <factionId> <@Role>```')

        # Initial call to get faction name
        status, tornId, Name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        response, e = await self.bot.api_call("faction", faction, ["basic", "chain"], key)
        if e and "error" in response:
            await self.bot.send_error_message(ctx.channel, f'Code {response["error"]["code"]}: {response["error"]["error"]}', title="API error")
            return

        # handle no faction
        if response["ID"] is None:
            await self.bot.send_error_message(ctx.channel, f'No faction with id `{faction}`')
            return

        # Set Faction role
        factionName = f'{html.unescape(response["name"])} [{response["ID"]}]'

        # if no chain
        if response.get("chain", dict({})).get("current", 0) == 0:
            eb = Embed(title=f"{factionName} chain watching", description=f'No chains on the horizon', color=my_red)
            await ctx.send(embed=eb)
            return

        if role is None:
            eb = Embed(title=f"{factionName} chain watching", description=f'Start watching', color=my_green)
            await ctx.send(embed=eb)
        else:
            eb = Embed(title=f"{factionName} chain watching", description=f'Start watching. Will notify {role} on timeout', color=my_green)
            await ctx.send(embed=eb)
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
                    eb = Embed(title=f"{factionName} chain watching", description=f'Stop watching.', color=my_red)
                    await ctx.send(embed=eb)
                    return

            # Initial call to get faction name
            status, tornId, Name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
            if status < 0:
                return

            response, e = await self.bot.api_call("faction", faction, ["chain", "timestamp"], key)
            if e and 'error' in response:
                eb = Embed(title=f"{factionName} chain watching", description=f'API error code {response["error"]["code"]} with master key: {response["error"]["error"]}.', color=my_red)
                await ctx.send(embed=eb)
                return

            # get timings
            timeout = response.get("chain", dict({})).get("timeout", 0)
            cooldown = response.get("chain", dict({})).get("cooldown", 0)
            current = response.get("chain", dict({})).get("current", 0)
            # timeout = 7
            # cooldown = 0
            # current = 10

            # get delay
            nowts = (now - epoch).total_seconds()
            apits = response.get("timestamp")

            delay = int(nowts - apits)
            txtDelay = f"   *API caching delay of {delay}s*" if delay else ""
            deltaLastNotified = int((now - lastNotified).total_seconds())

            # add delay to
            # timeout -= delay

            # if cooldown
            if cooldown > 0:
                eb = Embed(title=f"{factionName} chain watching", description=f'Chain at **{current}** in cooldown for {cooldown/60:.1f}min', color=my_blue)
                await ctx.send(embed=eb)
                return

            # if timeout
            elif timeout == 0:
                eb = Embed(title=f"{factionName} chain watching", description=f'Chain timed out', color=my_red)
                await ctx.send(embed=eb)
                return

            # if warning
            elif timeout < deltaW:
                eb = Embed(title=f"{factionName} chain watching", description=f'Chain at **{current}** and timeout in **{timeout}s**{txtDelay}', color=my_blue)
                await ctx.send("" if role is None else role, embed=eb)

            # if long enough for a notification
            elif deltaLastNotified > deltaN:
                lastNotified = now
                eb = Embed(title=f"{factionName} chain watching", description=f'Chain at **{current}** and timeout in **{timeout}s**{txtDelay}', color=my_blue)
                await ctx.send(embed=eb)

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
            await self.bot.send_error_message(ctx.channel, f'Either enter nothing or a faction `!fly <factionId>`')
            return

        # get configuration for guild
        status, _, _, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        if status in [-1, -2]:
            return

        # Torn API call
        r, e = await self.bot.api_call("faction", factionId, ["basic"], key)
        if e and "error" in r:
            await self.bot.send_error_message(ctx.channel, f'Code {r["error"]["code"]}: {r["error"]["error"]}', title="API error")
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
            await self.bot.send_error_message(ctx, 'Either enter nothing or a faction `!hosp <factionId>`')
            return

        # get configuration for guild
        status, _, _, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        if status in [-1, -2]:
            return

        # Torn API call
        r, e = await self.bot.api_call("faction", factionId, ["basic"], key)
        if e and "error" in r:
            await self.bot.send_error_message(ctx.channel, f'Code {r["error"]["code"]}: {r["error"]["error"]}', title="API error")
            return

        if not r["name"]:
            await self.bot.send_error_message(ctx, f'No faction with ID {factionId}')
            return

        hosps = {}
        for k, v in r.get("members", dict({})).items():
            if v["status"]["state"] in ["Hospital"]:
                s = v["status"]
                a = v["last_action"]
                hosps[k] = [v["name"], s["description"], cleanhtml(s["details"]), a["relative"], int(a["timestamp"])]

        lst = [f'Members of **{cleanhtml(r["name"])} [{r["ID"]}]** hospitalized: {len(hosps)}']
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
            await self.bot.send_error_message(ctx, 'Either enter nothing or a faction `!okay <factionId>`')
            return

        # get configuration for guild
        status, _, _, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        if status in [-1, -2]:
            return

        # Torn API call
        r, e = await self.bot.api_call("faction", factionId, ["basic"], key)
        if e and "error" in r:
            await self.bot.send_error_message(ctx.channel, f'Code {r["error"]["code"]}: {r["error"]["error"]}', title="API error")
            return

        if not r["name"]:
            await self.bot.send_error_message(ctx, f'No faction with ID {factionId}')
            return

        hosps = {}
        for k, v in r.get("members", dict({})).items():
            if v["status"]["state"] in ["Okay"]:
                s = v["status"]
                a = v["last_action"]
                hosps[k] = [v["name"], s["description"], cleanhtml(s["details"]), a["relative"], int(a["timestamp"])]

        lst = [f'Members of **{cleanhtml(r["name"])} [{r["ID"]}]** that are Okay: {len(hosps)}']
        for k, v in sorted(hosps.items(), key=lambda x: -x[1][4]):
            # line = f'**{v[0]}**: {v[1]} *{v[2]}* (last action {v[3]}) https://www.torn.com/profiles.php?XID={k}'
            line = f'**{v[0]}**: {v[1]}, *last action {v[3]}*, https://www.torn.com/profiles.php?XID={k}'
            lst.append(line)

        await send_tt(ctx, lst, tt=False)

    @commands.command(aliases=['la'])
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def last_action(self, ctx, *args):
        """Gives faction members that are okay"""
        logging.info(f'[chain/last_action] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

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
            await self.bot.send_error_message(ctx, 'Either enter nothing or a faction `!okay <factionId>`')
            return

        # get configuration for guild
        status, _, _, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, returnMaster=True, delError=True)
        if status in [-1, -2]:
            return

        # Torn API call
        r, e = await self.bot.api_call("faction", factionId, ["basic"], key)
        if e and "error" in r:
            await self.bot.send_error_message(ctx.channel, f'Code {r["error"]["code"]}: {r["error"]["error"]}', title="API error")
            return

        if not r["name"]:
            await self.bot.send_error_message(ctx, f'No faction with ID {factionId}')
            return

        members = r.get("members", dict({}))

        lst = [f'Members of **{cleanhtml(r["name"])} [{r["ID"]}]** ordered by last action']
        for k, v in sorted(members.items(), key=lambda x: -x[1]["last_action"]["timestamp"]):
            if v["last_action"]["status"] == "Idle":
                online = ":orange_circle:"
            elif v["last_action"]["status"] == "Offline":
                online = ":red_circle:"
            elif v["last_action"]["status"] == "Online":
                online = ":green_circle:"
            else:
                online = ":white_circle:"

            if v["status"]["color"] == "green":
                status = ":green_square:"
            elif v["status"]["color"] == "red":
                status = ":red_square:"
            elif v["status"]["color"] == "blue":
                status = ":blue_square:"
            else:
                status = ":white_circle:"
            line = f'{online}{status} **{v["name"]} [{k}]**: last action {v["last_action"]["relative"]}, {v["status"]["description"]}'
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

        if not len(args):
            await self.bot.send_error_message(ctx, "You need to enter a torn user ID: `!vault <torn_id>` or mention a member `!vault @Mention`")
            return

        # get author key
        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status != 0:
            return

        # get user id based on torn id or mention
        if args[0].isdigit():
            checkVaultId = args[0]

        elif re.match(r'<@!?\d+>', args[0]):
            discordID = re.findall(r'\d+', args[0])
            member = ctx.guild.get_member(int(discordID[0]))
            checkVaultId, err = await self.bot.discord_to_torn(member, key)
            if checkVaultId == -1:
                await self.bot.send_error_message(ctx, f'Error code {r["error"]["code"]}: {r["error"]["error"]}')
                return
            elif checkVaultId == -2:
                await self.bot.send_error_message(ctx, f'Discord member {discordID[0]} is not verified')
                return

        else:
            await self.bot.send_error_message(ctx, "You need to enter a torn user ID: `!vault <torn_id>` or mention a member `!vault @Mention`")
            return

        response, e = await self.bot.api_call("faction", "", ["basic", "donations"], key)
        if e and "error" in response:
            await self.bot.send_error_message(ctx.channel, f'Code {response["error"]["code"]}: {response["error"]["error"]}', title="API error")
            return

        factionName = f'{response["name"]} [{response["ID"]}]'
        members = response["members"]
        donations = response["donations"]
        checkVaultId = str(checkVaultId)
        eb = Embed(title="Vault status", color=my_blue)
        if checkVaultId in members:
            member = members[checkVaultId]
            eb.add_field(name=f'User', value=f'{member["name"]} [{checkVaultId}]')
            eb.add_field(name=f'Action', value=f'{member["last_action"]["relative"]}')
        else:
            eb.add_field(name=f'User', value=f'Member [{checkVaultId}]')
            eb.add_field(name=f'Action', value=f'Not in faction')

        if checkVaultId in donations:
            member = donations[checkVaultId]
            eb.add_field(name=f'Money', value=f'${member["money_balance"]:,d}')
            eb.add_field(name=f'Points', value=f'{member["points_balance"]:,d}')
        else:
            eb.add_field(name=f'Money', value=f'No vault records')
            eb.add_field(name=f'Points', value=f'No vault records')

        await ctx.author.send(embed=eb)

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
            eb = Embed(title="Retals tracking", description="STOP tracking", color=my_red)
            for k, v in [(k, v) for k, v in currents[str(ctx.author.id)].items() if k != "mentions"]:
                eb.add_field(name=f'{k.replace("_", " ").title()}', value=f'{v[2]}{v[1]} [{v[0]}]')
            await ctx.channel.send(embed=eb)
            del self.bot.configurations[ctx.guild.id]["chain"]["currents"][str(ctx.author.id)]
            await set_configuration(self.bot.bot_id, ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            return

        current = {"channel": [str(ctx.channel.id), f'{ctx.channel.name}', '#'],
                   "discord_user": [str(ctx.author.id), f'{ctx.author}', '']}

        # get torn user
        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author)
        if status < 0:
            await self.bot.send_error_message(ctx, f"Could not get {ctx.author}'s API key")
            return
        current["torn_user"] = [str(tornId), name, '', key]

        # get role
        if len(args) and args[0].replace("<@&", "").replace(">", "").isdigit():
            role = get(ctx.guild.roles, id=int(int(args[0].replace("<@&", "").replace(">", ""))))
        else:
            role = None

        if role is not None:
            current["role"] = [str(role.id), f'{role}', '@']

        eb = Embed(title="Retals tracking", description="START tracking", color=my_green)
        for k, v in current.items():
            eb.add_field(name=f'{k.replace("_", " ").title()}', value=f'{v[2]}{v[1]} [{v[0]}]')
        await ctx.channel.send(embed=eb)
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
            eb = Embed(title=f"Retals tracking error", description=f'Discord member {discord_member} not found', color=my_red)
            eb.set_footer(text="STOP tracking")
            await channel.send(embed=eb)
            return False

        # get torn id, name and key
        # # status, tornId, name, key = await self.bot.get_user_key(False, discord_member, guild=guild)
        #
        # if status < 0:
        #     await channel.send(f'```md\n# Tracking retals\n< error > could not find torn identity of discord member {discord_member}```')
        #     return False

        # if len(retal.get("torn_user")) < 4:
        #     await channel.send(f'```md\n# Tracking retals\n< error > Sorry it\'s my bad. I had to change how the tracking is built. You can launch it again now.\nKivou\n\n<STOP>```')
        #     return False

        tornId = retal.get("torn_user")[0]
        name = retal.get("torn_user")[1]
        key = retal.get("torn_user")[3]

        roleId = retal.get("role")[0] if len(retal.get("role", {})) else None
        notified = " " if roleId is None else f" <@&{roleId}> "

        response, e = await self.bot.api_call("faction", "", ["basic", "attacks"], key)
        # e = True; response = {'error': {'error': 'test', 'code': 8}}
        if e and 'error' in response:
            title=f'Retals tracking API key error'
            description = f'Error code {response["error"]["code"]} with {name} [{tornId}]\'s key: {response["error"]["error"]}'
            if response["error"]["code"] in [7]:
                description += "\nIt means that you don't have the required AA permission (AA for API access) for this API request."
                description += "\nThis is an in-game permission that faction leader and co-leader can grant to their members."

            if response["error"]["code"] in [1, 2, 6, 7, 10]:
                foot = "STOP tracking"
                color = my_red
                ret = False
            else:
                foot = "CONTINUE tracking"
                color = my_blue
                ret = True

            eb = Embed(title=title, description=description, color=color)
            eb.set_footer(text=foot)
            await channel.send(embed=eb)
            return ret

        if not int(response["ID"]):
            eb = Embed(title=f"Retals tracking error", description=f'No faction found for {name} {tornId}', color=my_red)
            eb.set_footer(text="STOP tracking")
            await channel.send(embed=eb)
            return False

        # faction id and name
        fId = response["ID"]
        fName = response["name"]

        now = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        nowts = (now - epoch).total_seconds()
        if "mentions" not in retal:
            retal["mentions"] = []
        for k, v in response["attacks"].items():
            delay = int(nowts - v["timestamp_ended"]) / float(60)
            if str(k) in retal["mentions"]:
                # logging.debug(f"[chain/_retalTask] ignore mention #{k}")
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
            if str(k) in response["attacks"]:
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
                    logging.debug(f"[chain/retal-notifications] No retal for {guild}")
                    continue
                logging.debug(f"[chain/retal-notifications] retal for {guild}")

                # iteration over all members asking for retal watch
                # guild = self.bot.get_guild(guild.id)
                todel = []
                tochange = {}
                for discord_user_id, retal in config["currents"].items():
                    # logging.debug(f"[chain/retal-notifications] {guild}: {retal}")

                    # call retal faction
                    previous_mentions = list(retal.get("mentions", []))
                    status = await self._retal(guild, retal)

                    # update metionned messages (but don't save in database, will remention in case of reboot)
                    if status and previous_mentions != retal.get("mentions", []):
                        tochange[discord_user_id] = retal
                    elif not status:
                        todel.append(discord_user_id)

                changes = False
                for d in todel:
                    del self.bot.configurations[guild.id]["chain"]["currents"][d]
                    changes = True

                for discord_user_id, retal in tochange.items():
                    self.bot.configurations[guild.id]["chain"]["currents"][discord_user_id] = retal
                    changes = True

                if changes:
                    await set_configuration(self.bot.bot_id, guild.id, guild.name, self.bot.configurations[guild.id])
                    logging.debug(f"[chain/retal-notifications] push notifications for {guild}")
                else:
                    logging.debug(f"[chain/retal-notifications] don't push notifications for {guild}")

            except BaseException as e:
                logging.error(f'[chain/retal-notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on retal task"}
                await self.bot.send_log_main(e, headers=headers, full=True)

    @retalTask.before_loop
    async def before_retalTask(self):
        await self.bot.wait_until_ready()

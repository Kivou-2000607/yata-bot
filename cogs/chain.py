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
import pytz
import json
import re
import logging
import html
import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FormatStrFormatter
from matplotlib.colors import to_rgba


# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks
from discord import Embed
from discord import File

# import bot functions and classes
from inc.handy import *


class Chain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.retalTask.start()
        self.chainTask.start()

    def cog_unload(self):
        self.retalTask.cancel()
        self.chainTask.cancel()

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def chain(self, ctx, *args):
        logging.info(f'[chain/chain] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "chain")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        # init current chains
        if "chains" not in self.bot.configurations[ctx.guild.id]["chain"]:
            self.bot.configurations[ctx.guild.id]["chain"]["chains"] = {}

        currents = config.get("chains", {})

        # delete if already exists
        if str(ctx.author.id) in currents:
            eb = Embed(title="STOP tracking chain", color=my_red)
            for k, v in [(k, v) for k, v in currents[str(ctx.author.id)].items() if k not in ["settings", "timestamp"]]:
                eb.add_field(name=k.replace("_", " ").title(), value=f'{v[2]}{v[1]} [{v[0]}]')
            await send(ctx.channel, embed=eb)
            del self.bot.configurations[ctx.guild.id]["chain"]["chains"][str(ctx.author.id)]
            await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            return

        alert = 90
        update = 15
        for arg in args:
            splt = arg.split("=")
            if len(splt) == 2 and splt[1].isdigit():
                if splt[0] == "timeout":
                    alert = int(splt[1])
                elif splt[0] == "update":
                    update = int(splt[1])

        current = {"channel": [str(ctx.channel.id), f'{ctx.channel.name}', '#'],
                   "discord_user": [str(ctx.author.id), f'{ctx.author}', ''],
                   "settings": [alert, update]}

        # get torn user
        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author)
        if status < 0:
            await self.bot.send_error_message(ctx.channel, f'Could not get {ctx.author}\'s API key')
            return
        current["torn_user"] = [str(tornId), name, '', key]

        # get role
        if len(args) and args[0].replace("<@&", "").replace(">", "").isdigit():
            role = get(ctx.guild.roles, id=int(int(args[0].replace("<@&", "").replace(">", ""))))
        else:
            role = None

        if role is not None:
            current["role"] = [str(role.id), f'{role}', '@']

        eb = Embed(title="START tracking chain", color=my_green)
        for k, v in [(k, v) for k, v in current.items() if k not in ["settings", "timestamp"]]:
            eb.add_field(name=k.replace("_", " ").title(), value=f'{v[2]}{v[1]} [{v[0]}]')
        eb.add_field(name="Update", value=f'Every {current["settings"][1]} minutes')
        eb.add_field(name="Alert", value=f'{current["settings"][0]} seconds before timeout')
        await send(ctx.channel, embed=eb)
        self.bot.configurations[ctx.guild.id]["chain"]["chains"][str(ctx.author.id)] = current
        await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])


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

        msg = await send("ctx, Gotcha! Just be patient, I'll stop watching on the next notification.")
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
            await send(ctx.channel, embed=eb)
            del self.bot.configurations[ctx.guild.id]["chain"]["currents"][str(ctx.author.id)]
            await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
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
        retal_msg = await send(ctx.channel, embed=eb)
        self.bot.configurations[ctx.guild.id]["chain"]["currents"][str(ctx.author.id)] = current
        await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])

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
            await send(channel, embed=eb)
            return False

        # get torn id, name and key
        # # status, tornId, name, key = await self.bot.get_user_key(False, discord_member, guild=guild)
        #
        # if status < 0:
        #     await send(channel, f'```md\n# Tracking retals\n< error > could not find torn identity of discord member {discord_member}```')
        #     return False

        # if len(retal.get("torn_user")) < 4:
        #     await send(channel, f'```md\n# Tracking retals\n< error > Sorry it\'s my bad. I had to change how the tracking is built. You can launch it again now.\nKivou\n\n<STOP>```')
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
            await send(channel, embed=eb)
            return ret

        if not int(response["ID"]):
            eb = Embed(title=f"Retals tracking error", description=f'No faction found for {name} {tornId}', color=my_red)
            eb.set_footer(text="STOP tracking")
            await send(channel, embed=eb)
            return False

        # faction id and name
        fId = response["ID"]
        fName = response["name"]
        retal_messages_sent = []

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

                embed = Embed(title=f'{v["attacker_name"]} [{v["attacker_id"]}] from {html.unescape(v["attacker_factionname"])}',
                              url=f'https://www.torn.com/profiles.php?XID={v["attacker_id"]})',
                              color=550000)

                embed.set_author(name=f'{html.unescape(fName)} have {tleft:.1f} minutes to retal on')

                embed.add_field(name='Timeout', value=f'{timeout} TCT')
                message = f':rage:{notified}{html.unescape(fName)} can retal on **{v["attacker_name"]} [{v["attacker_id"]}]**'
                if v["attacker_faction"]:
                    message += f' from **{html.unescape(v["attacker_factionname"])} [{v["attacker_faction"]}]**'
                    embed.add_field(name='Faction', value=f'[{html.unescape(v["attacker_factionname"])} [{v["attacker_faction"]}]](https://www.torn.com/factions.php?step=profile&ID={v["attacker_faction"]})')
                else:
                    embed.add_field(name='Faction', value=f'None')

                embed.add_field(name='Defender', value=f'[{v["defender_name"]} [{v["defender_id"]}]](https://www.torn.com/profiles.php?XID={v["defender_id"]})')
                embed.add_field(name='Chain Bonus', value=f'{v["chain"]} (x {v["modifiers"]["chain_bonus"]})')
                embed.add_field(name='Respect', value=f'{v["respect_gain"]:.2f}')
                embed.add_field(name=f'Log', value=f'[{v["result"]}](https://www.torn.com/loader.php?sid=attackLog&ID={v["code"]})')
                embed = append_update(embed, nowts)

                msg = await send(channel, message, embed=embed)
                retal["mentions"].append(str(k))
                retal_messages_sent.append((msg, v["attacker_id"]))

            elif v["attacker_faction"] == int(fId) and float(v["modifiers"]["retaliation"]) > 1 and delay < 5:
                attack_time = ts_to_datetime(int(v["timestamp_ended"]), fmt="time")
                await send(channel, f':middle_finger: {v["attacker_name"]} retaled on **{v["defender_name"]} [{v["defender_id"]}]** {delay:.1f} minutes ago at {attack_time} TCT')
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

        # try to find spies
        for retal_message, attacker_id in retal_messages_sent:
            spy = False

            # try tornstats
            if not spy:
                response, e = await self.bot.ts_api_call(f"{key}/spy/{attacker_id}")
                if e and "error" in response:
                    pass
                else:
                    spy_ts = response["spy"]
                    if spy_ts.get("status", False):
                        spy = {k: spy_ts[k] for k in ["strength", "speed", "defense", "dexterity", "total"] if spy_ts[k] not in ["N/A"]}
                        spy["src"] = f'Tornstats {spy_ts["difference"]}'

            # try yata
            if not spy:
                response, e = await self.bot.yata_api_call(f"spy/{attacker_id}?key={key}")
                if e and "error" in response:
                    pass
                else:
                    spy_yata = response["spies"][str(attacker_id)]
                    if spy_yata is not None:
                        spy = {k: spy_yata[k] for k in ["strength", "speed", "defense", "dexterity", "total"]}
                        spy["src"] = f'YATA {ts_format(spy_yata["update"], fmt="date")}'

            if spy:
                embed_dict = retal_message.embeds[0].to_dict()
                description = []
                description.append('```')
                description.append(f'str: {spy.get("strength", -1):>16,d}'.replace("-1", " -"))
                description.append(f'def: {spy.get("defense", -1):>16,d}'.replace("-1", " -"))
                description.append(f'spe: {spy.get("speed", -1):>16,d}'.replace("-1", " -"))
                description.append(f'dex: {spy.get("dexterity", -1):>16,d}'.replace("-1", " -"))
                description.append(f'tot: {spy.get("total", -1):>16,d}'.replace("-1", " -"))
                description.append(f'```*{spy["src"]}*'.lower())
                embed_dict["description"] = "\n".join(description)
                embed = Embed.from_dict(embed_dict)

                await retal_message.edit(embed=embed)

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
                    await self.bot.set_configuration(guild.id, guild.name, self.bot.configurations[guild.id])
                    logging.debug(f"[chain/retal-notifications] push notifications for {guild}")
                else:
                    logging.debug(f"[chain/retal-notifications] don't push notifications for {guild}")

            except BaseException as e:
                logging.error(f'[chain/retal-notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on retal task"}
                await self.bot.send_log_main(e, headers=headers, full=True)


    async def _chain(self, guild, chain):
        logging.info(f'[chain/_chain] {guild}')

        discord_id = chain.get("discord_user")[0] if len(chain.get("discord_user", {})) else "0"

        # get channel
        channelId = chain.get("channel")[0] if len(chain.get("channel", {})) else None
        channel = get(guild.channels, id=int(channelId))
        if channel is None:
            return discord_id  # return discord id to delete outside of the chain

        # get discord member
        discord_member = get(guild.members, id=int(discord_id))
        if discord_member is None:
            await self.bot.send_error_message(channel, f'Chain tracking: Discord member #`{discord_id}` not found\n\nSTOP', title="Error tracking chains")
            return discord_id  # return discord id to delete outside of the chain

        # api call
        key = chain["torn_user"][3]
        response, e = await self.bot.api_call("faction", "", ["basic", "chain", "timestamp"], key)
        if e and "error" in response:
            await self.bot.send_error_message(channel, f'Code {response["error"]["code"]}: {response["error"]["error"]}', title=f'API error on chain watching ({chain["torn_user"][1]})')
            return discord_id if response["error"]["code"] in [1, 2, 10, 13] else None

        # Set Faction role
        factionName = f'{html.unescape(response["name"])} [{response["ID"]}]'
        factionID = response["ID"]

        # if no chain
        if response.get("chain", dict({})).get("current", 0) == 0:
            eb = Embed(title=f"{factionName} chain watching", description=f'No chains on the horizon\n\nSTOP tracking', color=my_red)
            await send(channel, embed=eb)
            return discord_id  # return discord id to delete outside of the chain

        # get timings
        timeout = response.get("chain", dict({})).get("timeout", 0)
        cooldown = response.get("chain", dict({})).get("cooldown", 0)
        current = response.get("chain", dict({})).get("current", 0)
        # timeout = 7
        # cooldown = 10
        # current = 10

        # get delay
        nowts = int(time.time())
        apits = response.get("timestamp", 0)

        delay = int(nowts - apits)
        txtDelay = f"   *API caching delay of {delay}s*" if delay else ""

        if cooldown > 0:
            # if cooldown
            eb = Embed(title=f"{factionName} chain watching", description=f'Chain at **{current}** in cooldown for {cooldown/60:.1f} min', color=my_red)
            await send(channel, embed=eb)
            return discord_id  # return discord id to delete outside of the chain

        elif timeout == 0:
            # if timeout
            eb = Embed(title=f"{factionName} chain watching", description=f'Chain timed out', color=my_red)
            await send(channel, embed=eb)
            return discord_id  # return discord id to delete outside of the chain

        elif timeout < chain["settings"][0]:
            # if warning
            role = get(guild.roles, id=int(chain.get("role", [0])[0]))
            eb = Embed(title=f"{factionName} chain watching", description=f'Chain at **{current}** and timeout in **{timeout}s**{txtDelay}', color=my_blue)
            await send(channel, f'Chain timeout in {timeout}s {"" if role is None else role.mention}', embed=eb)

        elif nowts - self.bot.configurations[guild.id]["chain"]["chains"][discord_id].get("timestamp", 0) > chain["settings"][1] * 60:
            # if long enough for a notification
            eb = Embed(title=f"{factionName} chain watching", description=f'Chain at **{current}** and timeout in **{timeout}s**{txtDelay}', url="https://yata.yt/faction/chains/0", color=my_blue)
            file = None

            # try get data from YATA
            response, e = await self.bot.yata_api_call(f"faction/livechain/?key={key}")

            if e and "error" in response:
                eb.add_field(name="YATA error", value=response["error"]["error"])

            elif "chain" in response and "yata" in response["chain"]:
                yata_payload = response["chain"]["yata"]

                if "error" in yata_payload:
                    eb.add_field(name="YATA error", value=yata_payload["error"])
                else:

                    eb.add_field(name="Global hit rate", value=f'{60 * yata_payload["stats"]["global_hit_rate"]:,.2f} hits/min')
                    eb.add_field(name="Recent hit rate", value=f'{60 * yata_payload["stats"]["current_hit_rate"]:,.2f} hits/min')
                    eb.add_field(name="Next bonus ETA", value=f'{ts_format(yata_payload["stats"]["current_eta"], fmt="rounded")}')

                    # plot
                    time_elapsed = yata_payload["last"] - response["chain"]["start"]
                    x = [datetime.datetime.fromtimestamp(int(_[0])) for _ in yata_payload["hits"]]
                    y1 = [int(_[2]) for _ in yata_payload["hits"]]
                    y2 = [60 * int(_[1]) / float(yata_payload["stats"]["bin_size"]) for _ in yata_payload["hits"]]

                    plt.style.use('dark_background')
                    fig, ax1 = plt.subplots()
                    ax2 = ax1.twinx()
                    ax1.plot(x, y1, zorder=1)
                    ax2.plot(x, y2, zorder=2, linewidth=1, color='g', linestyle="--")
                    ax1.axhline(y=response["chain"]["max"], color='r', label='Next Bonus')
                    ax1.grid(linewidth=1, alpha=0.1)

                    ax1.xaxis.set_minor_locator(mdates.DayLocator(interval=max(int(time_elapsed / (3600 * 24 * 2)), 1)))
                    ax1.xaxis.set_minor_formatter(mdates.DateFormatter('%m/%d'))
                    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=max(int(time_elapsed / (3600 * 6)), 1)))
                    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    ax1.tick_params(axis="x", which="minor", pad=16)

                    ax1.set_ylabel("Total hits")
                    ax2.set_ylabel("Hit rate (hits/mins)")

                    fig.tight_layout()
                    fig.savefig(f'tmp/chain-{factionID}.png', dpi=420, bbox_inches='tight', transparent=True)
                    file = File(f'tmp/chain-{factionID}.png', filename=f'chain-{factionID}.png')
                    eb.set_image(url=f'attachment://chain-{factionID}.png')

                    eb.set_footer(text=f'Last update: {ts_format(yata_payload["update"], fmt="short")}')
                    eb.timestamp = datetime.datetime.fromtimestamp(yata_payload["update"], tz=pytz.UTC)

            await send(channel, file=file, embed=eb)

            self.bot.configurations[guild.id]["chain"]["chains"][discord_id]["timestamp"] = nowts



    async def _chain_main(self, guild):
        try:

            config = self.bot.get_guild_configuration_by_module(guild, "chain", check_key="chains")
            if not config:
                return

            to_del = []

            # loop over the chains of the server
            for discord_user_id, chain in config["chains"].items():
                discord_id = await self._chain(guild, chain)
                if discord_id is not None:
                    to_del.append(discord_id)

            # delete chains in the bot memory
            for discord_id in to_del:
                del self.bot.configurations[guild.id]["chain"]["chains"][discord_id]

            # send to db
            if len(to_del):
                await self.bot.set_configuration(guild.id, guild.name, self.bot.configurations[guild.id])

        except BaseException as e:
            logging.error(f'[chain/_chain_main] {guild} [{guild.id}]: {hide_key(e)}')
            await self.bot.send_log(e, guild_id=guild.id)
            headers = {"guild": guild, "guild_id": guild.id, "error": "error on chains task"}
            await self.bot.send_log_main(e, headers=headers, full=True)

    @tasks.loop(seconds=30)
    async def chainTask(self):
        logging.debug("[chain/chainTask] start task")
        await asyncio.gather(*map(self._chain_main, self.bot.get_guilds_by_module("chain")))
        logging.debug("[chain/chainTask] start end")

    @retalTask.before_loop
    async def before_retalTask(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

    @chainTask.before_loop
    async def before_chainTask(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

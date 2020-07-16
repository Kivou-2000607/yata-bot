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
import traceback
import logging

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks

# import bot functions and classes
from inc.yata_db import set_configuration
from inc.handy import *


class Crimes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ocTask.start()

    def cog_unload(self):
        self.ocTask.cancel()

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def ocready(self, ctx, *args):
        """ list oc ready
        """
        logging.info(f'[oc/ocready] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "oc")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, delError=True)

        if status < 0:
            return

        # make api call
        url = f"https://api.torn.com/faction/?selections=basic,crimes&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if "error" in req:
            await ctx.send(f':x: API error while pulling crimes with API key: *{req["error"]["error"]}*')
            return

        crimes = req["crimes"]
        members = req["members"]
        for k, v in crimes.items():
            ready = not v["time_left"] and not v["time_completed"]
            if ready:
                lst = ['```md', f'# organized crime ready', f'< Crime > {v["crime_name"]} #{k}', f'< Started > {ts_to_datetime(v["time_started"], fmt="short")}', f'< Ready > {ts_to_datetime(v["time_ready"], fmt="short")}', f'< Participants > {len(v["participants"])}\n']
                # logging.info(k, v)
                for p in v["participants"]:
                    tId = list(p)[0]
                    name = members.get(tId, dict({"name": "Player"}))["name"]
                    status = list(p.values())[0]
                    lst.append(f'- {name}: {status["state"]} ({status["description"]})')

                lst.append('```')
                await ctx.send(f"\n".join(lst))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def oc(self, ctx, *args):
        """ start / stop watching for organized crimes
        """
        logging.info(f'[oc/oc] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # get configuration
        config = self.bot.get_guild_configuration_by_module(ctx.guild, "oc")
        if not config:
            return

        # check if channel is allowed
        allowed = await self.bot.check_channel_allowed(ctx, config)
        if not allowed:
            return

        # init currents
        if "currents" not in self.bot.configurations[ctx.guild.id]["oc"]:
            self.bot.configurations[ctx.guild.id]["oc"]["currents"] = {}

        currents = config.get("currents", {})

        # delete if already exists
        if str(ctx.author.id) in currents:
            lst = ["```md", "# Tracking organized crimes"]
            for k, v in [(k, v) for k, v in currents[str(ctx.author.id)].items() if k != "mentions"]:
                lst.append(f'< {k} > {v[2]}{v[1]} [{v[0]}]')
            lst += ['', '<STOP>', "```"]
            await ctx.channel.send("\n".join(lst))
            del self.bot.configurations[ctx.guild.id]["oc"]["currents"][str(ctx.author.id)]
            await set_configuration(self.bot.bot_id, ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            return

        current = {"channel": [str(ctx.channel.id), f'{ctx.channel.name}', '#'],
                   "discord_user": [str(ctx.author.id), f'{ctx.author}', '']}

        # get torn user
        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author)
        if status < 0:
            lst = ['```md', f'# Tracking organized crimes', f'< error > could not get {ctx.author}\'s API key```']
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

        lst = ["```md", "# Tracking organized crimes"]
        for k, v in current.items():
            lst.append(f'< {k} > {v[2]}{v[1]} [{v[0]}]')
        lst += ['', '<START>', "```"]
        await ctx.channel.send("\n".join(lst))
        self.bot.configurations[ctx.guild.id]["oc"]["currents"][str(ctx.author.id)] = current
        await set_configuration(self.bot.bot_id, ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])

    async def _oc(self, guild, oc):

        # get channel
        channelId = oc.get("channel")[0] if len(oc.get("channel", {})) else None
        channel = get(guild.channels, id=int(channelId))
        if channel is None:
            return False

        # get discord member
        discord_id = oc.get("discord_user")[0] if len(oc.get("discord_user", {})) else "0"
        discord_member = get(guild.members, id=int(discord_id))
        if discord_member is None:
            await channel.send(f'```md\n# Tracking organized crimes\n< error > discord member {discord_member} not found\n\n<STOP>```')
            return False

        # get torn id, name and key
        # status, tornId, name, key = await self.bot.get_user_key(False, discord_member, guild=guild)
        #
        # if status < 0:
        #     await channel.send(f'```md\n# Tracking organized crimes\n< error > could not find torn identity of discord member {discord_member}```')
        #     return False

        if len(oc.get("torn_user")) < 4:
            await channel.send(f'```md\n# Tracking organized crimes\n< error > Sorry it\'s my bad. I had to change how the tracking is built. You can launch it again now.\nKivou\n\n<STOP>```')
            return False

        tornId = oc.get("torn_user")[0]
        name = oc.get("torn_user")[1]
        key = oc.get("torn_user")[3]

        roleId = oc.get("role")[0] if len(oc.get("role", {})) else None
        notified = " " if roleId is None else f" <@&{roleId}> "

        url = f'https://api.torn.com/faction/?selections=basic,crimes&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if 'error' in req:
            lst = [f'```md', f'# Tracking organized crimes\n< error > Problem with {name} [{tornId}]\'s key: {req["error"]["error"]}']
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
            await channel.send(f'```md\n# Tracking organized crimes\n< error > wrong API output\n\n{hide_key(req)}\n\n<CONTINUE>```')
            return True

        if not int(req["ID"]):
            await channel.send(f'```md\n# Tracking organized crimes\n< error > no faction found for {name} {tornId}\n\n<STOP>```')
            return False

        # faction id and name
        fId = req["ID"]
        fName = req["name"]

        # faction members
        members = req["members"]

        # get timestamps
        now = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        nowts = (now - epoch).total_seconds()

        # init mentions if empty
        if "mentions" not in oc:
            oc["mentions"] = []

        # loop over crimes
        for k, v in req["crimes"].items():

            # is already mentionned
            mentionned = True if str(k) in oc["mentions"] else False

            # is ready (without members)
            ready = v["time_left"] == 0

            # is completed
            completed = v["time_completed"] > 0

            # exit if not ready
            if not ready:
                continue

            # if completed and already mentionned -> remove the already mentionned
            if completed and mentionned:
                initId = str(v["initiated_by"])
                lst = [
                    '```md',
                    f'# Organized crime completed',
                    f'< Faction > {fName}',
                    f'< Crime > {v["crime_name"]}',
                    f'< Initiated > {members.get(initId, {"name": "Player"})["name"]} [{v["initiated_by"]}].',
                    f'< Money > ${v["money_gain"]:,}',
                    f'< Respect > {v["respect_gain"]:,}',
                    '```']
                await channel.send("\n".join(lst))
                oc["mentions"].remove(str(k))

            # exit if completed
            if completed:
                continue

            # change ready based on participants
            participants = [list(p.values())[0] for p in v["participants"] if v is not None]
            for p in participants:
                if p["state"] != "Okay":
                    ready = False

            # if ready and not already mentionned -> mention
            if ready and not mentionned:
                await channel.send(f'{notified} {v["crime_name"]} ready\n```md\n# Organized crime ready\n< Faction > {fName}\n< Crime > {v["crime_name"]} #{k}\n\n<READY>```')
                oc["mentions"].append(str(k))

            # if not ready (because of participants) and already mentionned -> remove the already mentionned
            if not ready and mentionned:
                await channel.send(f'{v["crime_name"]} ready\n```md\n# Organized crime not ready\n< Faction > {fName}\n< Crime > {v["crime_name"]} #{k}\n\nNot ready anymore because of non Okay participants```')
                oc["mentions"].remove(str(k))

        # clean mentions
        cleanedMentions = []
        for k in oc["mentions"]:
            if str(k) in req["crimes"]:
                cleanedMentions.append(str(k))

        oc["mentions"] = cleanedMentions

        # delete old messages
        # fminutes = now - datetime.timedelta(minutes=5)
        # async for message in channel.history(limit=50, before=fminutes):
        #     if message.author.bot:
        #         await message.delete()

        return True

    # @tasks.loop(seconds=3)
    @tasks.loop(seconds=300)
    async def ocTask(self):
        logging.debug(f"[oc/notifications] start task")

        # iteration over all guilds
        for guild in self.bot.get_guilds_by_module("oc"):
            try:

                config = self.bot.get_guild_configuration_by_module(guild, "oc", check_key="currents")
                if not config:
                    logging.info(f"[oc/notifications] No oc for {guild}")
                    continue
                logging.info(f"[oc/notifications] OC for {guild}")

                # iteration over all members asking for oc watch
                # guild = self.bot.get_guild(guild.id)
                todel = []
                for discord_user_id, oc in config["currents"].items():
                    logging.debug(f"[oc/notifications] {guild}: {oc}")

                    # call oc faction
                    status = await self._oc(guild, oc)

                    if status:
                        self.bot.configurations[guild.id]["oc"]["currents"][discord_user_id] = oc
                    else:
                        todel.append(discord_user_id)

                for d in todel:
                    del self.bot.configurations[guild.id]["oc"]["currents"][d]

                await set_configuration(self.bot.bot_id, guild.id, guild.name, self.bot.configurations[guild.id])

            except BaseException as e:
                logging.error(f'[oc/notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(f'error on oc notifications: {e}', guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on oc notifications"}
                await self.bot.send_log_main(e, headers=headers, full=True)

    @ocTask.before_loop
    async def before_ocTask(self):
        await self.bot.wait_until_ready()

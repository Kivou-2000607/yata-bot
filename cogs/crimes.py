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
import includes.checks as checks
import includes.formating as fmt
from includes.yata_db import push_configurations


class Crimes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ocTask.start()

    def cog_unload(self):
        self.ocTask.cancel()

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def ocs(self, ctx):
        """ list all current ocs watching
        """
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "crimes"):
            await ctx.send(":x: Crimes module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = ["yata-admin"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        ocs = config["crimes"].get("oc")
        if ocs is None or not len(ocs):
            await ctx.send("You're not watching any ocs.")
        for v in ocs.values():
            channel = get(ctx.guild.channels, id=v["channelId"])
            admin = get(ctx.guild.channels, name="yata-admin")
            notify = 'nobody' if v["roleId"] is None else f'<@&{v["roleId"]}>'
            lst = [f'{v["name"]} [{v["tornId"]}] is notifying {notify} for ocs in #{channel}.',
                   f'It can be stopped either by them typing `!oc` in #{channel} or anyone typing `!stopoc {v["tornId"]}` in #{admin}.']
            await ctx.send("\n".join(lst))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def stopoc(self, ctx, *args):
        """ force stop a oc watching (for admin)
        """
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "crimes"):
            await ctx.send(":x: Crimes module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "crimes")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        if len(args) and args[0].isdigit():
            tornId = str(args[0])
        else:
            admin = get(ctx.guild.channels, name="yata-admin")
            lst = ["If you want to stop watching ocs you started simply type `!oc` in the channel you started it.",
                   f"If you want to stop watching ocs someone else started you need to enter a user Id in {admin.mention}.",
                   f"Type `!ocs` in {admin.mention} for more detals."]
            await ctx.send("\n".join(lst))
            return

        ocs = config["crimes"].get("oc")
        if ocs is None:
            await ctx.send("You're not watching any ocs.")
        elif str(tornId) not in ocs:
            await ctx.send(f"Player {tornId} was not watching any ocs.")
        else:
            v = config["crimes"]["oc"][str(tornId)]
            name = v.get("name")
            channel = get(ctx.guild.channels, id=v["channelId"])
            del config["crimes"]["oc"][str(tornId)]
            if channel is not None:
                await channel.send(f':x: **{name} [{tornId}]**: Stop watching ocs on behalf of {ctx.author.nick}.')

            self.bot.configs[str(ctx.guild.id)] = config
            await push_configurations(self.bot.bot_id, self.bot.configs)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def ocready(self, ctx, *args):
        """ list oc ready
        """
        logging.info(f'[oc/ocready] {ctx.guild}: {member.nick} / {member}')

        # return if chain not active
        if not self.bot.check_module(ctx.guild, "crimes"):
            await ctx.send(":x: Crimes module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "crimes")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
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
                lst = ['```YAML', f'OC: {v["crime_name"]} #{k}', f'Started: {fmt.ts_to_datetime(v["time_started"], fmt="short")}', f'Ready: {fmt.ts_to_datetime(v["time_ready"], fmt="short")}', f'Participants: {len(v["participants"])}']
                # logging.info(k, v)
                for p in v["participants"]:
                    tId = list(p)[0]
                    name = members.get(tId, dict({"name": "Player"}))["name"]
                    status = list(p.values())[0]
                    lst.append(f'    {name}: {status["state"]} ({status["description"]})')

                lst.append('```')
                await ctx.send(f"\n".join(lst))

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def oc(self, ctx, *args):
        """ start / stop watching for organized crimes
        """
        logging.info(f'[oc/oc] {ctx.guild}: {ctx.member.nick} / {ctx.member}')

        # return if chain not active
        if not self.bot.check_module(ctx.guild, "crimes"):
            await ctx.send(":x: Crimes module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "crimes")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, delError=True)

        # just to be sure
        tornId = str(tornId)

        if config["crimes"].get("oc") is None:
            config["crimes"]["oc"] = dict({})

        if status == 0:

            if len(args) and args[0].replace("<@&", "").replace(">", "").isdigit():
                roleId = int(args[0].replace("<@&", "").replace(">", ""))
            else:
                roleId = None

            if str(tornId) in config["crimes"].get("oc"):
                del config["crimes"]["oc"][str(tornId)]
                await ctx.send(f':x: **{name} [{tornId}]**: Stop watching organized crimes.')
            else:
                oc = {"name": name,
                      "tornId": str(tornId),
                      "key": key,
                      "roleId": roleId,
                      "channelId": ctx.channel.id}
                config["crimes"]["oc"][str(tornId)] = oc

                notified = "Nobody" if roleId is None else f"<@&{roleId}>"
                await ctx.send(f':white_check_mark: **{name} [{tornId}]** Start watching organized crimes for their faction in {ctx.channel.mention}. {notified} will be notified.')

        else:
            if str(tornId) in config["crimes"].get("oc"):
                del config["crimes"]["oc"][str(tornId)]
                await ctx.send(f':x: **{name} [{tornId}]**: Stop watching organized crimes.')

        self.bot.configs[str(ctx.guild.id)] = config
        await push_configurations(self.bot.bot_id, self.bot.configs)

    async def _oc(self, guild, oc):

        key = oc.get("key")
        tornId = str(oc.get("tornId"))
        name = oc.get("name")
        roleId = oc.get("roleId")
        channelId = oc.get("channelId")

        channel = get(guild.channels, id=channelId)
        notified = " " if roleId is None else f" <@&{roleId}> "
        if channel is None:
            return False

        url = f'https://api.torn.com/faction/?selections=basic,crimes&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if 'error' in req:
            await channel.send(f':x: `{name} [{tornId}]` Problem with their key for oc: *{req["error"]["error"]}*')
            if req["error"]["code"] in [7]:
                await channel.send("It means that you don't have the required AA permission (AA for API access) for this API request. This is an in-game permission that faction leader and co-leader can grant to their members.")

            if req["error"]["code"] in [1, 2, 6, 7, 10]:
                await channel.send(f':x: `{name} [{tornId}]` oc stopped...')
                return False
            else:
                return True

        if not int(req["ID"]):
            await channel.send(f':x: `{name} [{tornId}]` No factions found... oc stopped...')
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
                lst = [f'{fName}: {v["crime_name"]} #{k} has been completed by {members.get(initId, {"name": "Player"})["name"]} [{v["initiated_by"]}].',
                       f'Money: ${v["money_gain"]:,}',
                       f'Respect: {v["respect_gain"]:,}',
                       ]
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
                await channel.send(f'{notified}{fName}: {v["crime_name"]} #{k} is ready.')
                oc["mentions"].append(str(k))

            # if not ready (because of participants) and already mentionned -> remove the already mentionned
            if not ready and mentionned:
                await channel.send(f'{fName}: {v["crime_name"]} #{k} is not ready anymore because of non Okay participants.')
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
        logging.info(f"[oc/notifications] start task")

        # iteration over all guilds
        for guild in self.bot.get_guild_module("crimes"):
            try:
                # ignore servers with no verify
                # if not self.bot.check_module(guild, "crimes"):
                #     continue

                # ignore servers with no option daily check
                config = self.bot.get_config(guild)
                if not config["crimes"].get("oc", False):
                    continue

                # logging.info(f"[OC] oc {guild}: start")

                # iteration over all members asking for oc watch
                # guild = self.bot.get_guild(guild.id)
                todel = []
                for tornId, oc in config["crimes"]["oc"].items():
                    logging.debug(f"[oc/notifications] {guild}: {tornId}")

                    # call oc faction
                    status = await self._oc(guild, oc)

                    # update metionned messages (but don't save in database, will remention in case of reboot)
                    if status:
                        self.bot.configs[str(guild.id)]["crimes"]["oc"][str(tornId)] = oc
                    else:
                        todel.append(str(tornId))

                for d in todel:
                    del self.bot.configs[str(guild.id)]["crimes"]["oc"][d]
                    await push_configurations(self.bot.bot_id, self.bot.configs)

                # logging.info(f"[OC] oc {guild}: end")

            except BaseException as e:
                logging.error(f'[oc/notifications] {guild} [{guild.id}]: {e}')
                await self.bot.send_log(e, guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on oc notifications"}
                await self.bot.send_log_main(e, headers=headers)

    @ocTask.before_loop
    async def before_ocTask(self):
        logging.info('[oc/notifications] waiting...')
        await self.bot.wait_until_ready()
        logging.info('[oc/notifications] start loop')

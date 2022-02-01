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
import traceback
import logging
import html
import time

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.utils import escape_markdown
from discord.ext import tasks
from discord import Embed

# import bot functions and classes
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
        response, e = await self.bot.api_call("faction", "", ["basic", "crimes"], key, error_channel=ctx.channel)
        if e:
            return

        crimes = response["crimes"]
        members = response["members"]
        for k, v in crimes.items():
            ready = not v["time_left"] and not v["time_completed"]
            if ready:
                participants = []
                greatest_inactivity = int(time.time())
                greatest_inactivity_string = ""
                for p in v["participants"]:
                    tId = list(p)[0]
                    participant = members.get(tId, {})
                    name = participant.get("name", "Player") + "_test"
                    status = participant.get("status", {"state": "?", "description": "?"})
                    last_action = participant.get("last_action", {"timestamp": 0, "relative": "?"})
                    participants.append(f'- {escape_markdown(name)}: {status["state"]} ({last_action["relative"]})')
                    if last_action["timestamp"] < greatest_inactivity:
                        greatest_inactivity = last_action["timestamp"]
                        greatest_inactivity_string = f'{last_action["relative"]} ({name})'

                description = [
                    f'Started: {ts_to_datetime(v["time_started"], fmt="short")}',
                    f'Ready: {ts_to_datetime(v["time_ready"], fmt="short")}',
                    f'Inactivity: {greatest_inactivity_string}'
                ]
                eb = Embed(title=f'{v["crime_name"]} #{k} ready', description="\n".join(description), color=my_blue)
                eb.add_field(name=f'{len(v["participants"])} participants', value="\n".join(participants))

                await send(ctx, embed=eb)

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
            eb = Embed(title="STOP tracking organized crimes", color=my_red)
            for k, v in [(k, v) for k, v in currents[str(ctx.author.id)].items() if k != "mentions"]:
                eb.add_field(name=k.replace("_", " ").title(), value=f'{v[2]}{v[1]} [{v[0]}]')
            await send(ctx.channel, embed=eb)
            del self.bot.configurations[ctx.guild.id]["oc"]["currents"][str(ctx.author.id)]
            await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])
            return

        current = {"channel": [str(ctx.channel.id), f'{ctx.channel.name}', '#'],
                   "discord_user": [str(ctx.author.id), f'{ctx.author}', '']}

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

        eb = Embed(title="START tracking organized crimes", color=my_green)
        for k, v in current.items():
            eb.add_field(name=k.replace("_", " ").title(), value=f'{v[2]}{v[1]} [{v[0]}]')
        await send(ctx.channel, embed=eb)
        self.bot.configurations[ctx.guild.id]["oc"]["currents"][str(ctx.author.id)] = current
        await self.bot.set_configuration(ctx.guild.id, ctx.guild.name, self.bot.configurations[ctx.guild.id])

    async def _oc(self, guild, oc, notifications):
        # get channel
        channelId = oc.get("channel")[0] if len(oc.get("channel", {})) else None
        channel = get(guild.channels, id=int(channelId))
        if channel is None:
            return False

        # get discord member
        discord_id = oc.get("discord_user")[0] if len(oc.get("discord_user", {})) else "0"
        discord_member = get(guild.members, id=int(discord_id))
        if discord_member is None:  # recover discord member if not in cache
            discord_member = await self.bot.fetch_user(int(discord_id))

        if discord_member is None:
            await self.bot.send_error_message(channel, f'Discord member #{discord_id} not found\n\nSTOP', title="Error tracking organized crimes")
            return False

        # get torn id, name and key
        # status, tornId, name, key = await self.bot.get_user_key(False, discord_member, guild=guild)
        #
        # if status < 0:
        #     await send(channel, f'```md\n# Tracking organized crimes\n< error > could not find torn identity of discord member {discord_member}```')
        #     return False

        if len(oc.get("torn_user")) < 4:
            await self.bot.send_error_message(channel, f'Sorry it\'s my bad. I had to change how the tracking is built. You can launch it again now.\nKivou\n\nSTOP', title="Error tracking organized crimes")
            return False

        tornId = oc.get("torn_user")[0]
        name = oc.get("torn_user")[1]
        key = oc.get("torn_user")[3]

        roleId = oc.get("role")[0] if len(oc.get("role", {})) else None
        notified = "OC" if roleId is None else f"<@&{roleId}>"

        response, e = await self.bot.api_call("faction", "", ["basic", "crimes", "timestamp"], key)
        if e and 'error' in response:

            lst = [f'Problem with {name} [{tornId}]\'s key: {response["error"]["error"]}']
            if response["error"]["code"] in [7]:
                lst.append("It means that you don't have the required AA permission (AA for API access) for this API request")
                lst.append("This is an in-game permission that faction leader and co-leader can grant to their members")

            if response["error"]["code"] in [1, 2, 6, 7, 10]:
                lst += ["", "STOP"]
                await self.bot.send_error_message(channel, "\n".join(lst), title="Error tracking organized crimes")
                return False
            else:
                lst += ["", "CONTINUE"]
                await self.bot.send_error_message(channel, "\n".join(lst), title="Error tracking organized crimes")
                return True

        if response is None or "ID" not in response:
            await self.bot.send_error_message(channel, f'API is talking shit... #blameched\n\nCONTINUE', title="Error tracking organized crimes")
            return True

        if not int(response["ID"]):
            await self.bot.send_error_message(channel, f'No faction found for {name} [{tornId}]\n\nSTOP', title="Error tracking organized crimes")
            return False

        # faction id and name
        fId = response["ID"]
        fName = html.unescape(response["name"])

        # faction members
        members = response["members"]

        # get timestamps
        now = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        nowts = (now - epoch).total_seconds()

        # init mentions if empty
        if "mentions" not in oc:
            oc["mentions"] = []

        # loop over crimes
        crimes_fields = {"ready": [], "completed": [], "not_ready": [], "waiting": []}
        need_to_mention = False
        need_to_display = []
        for k, v in response["crimes"].items():
            # is already mentionned
            mentionned = True if str(k) in oc["mentions"] else False

            # is ready (without members)
            ready = v["time_left"] == 0

            # is completed
            completed = v["time_completed"] > 0

            # DEBUG
            # print(k)
            # if k in ["9218624", "9218622"]:
            #     print("force ready")
            #     ready = True
            #     # completed = False

            # exit if not ready
            if not ready:
                continue

            # if completed and already mentionned -> remove the already mentionned
            if completed and mentionned:
                initId = str(v["initiated_by"])
                # crimes_fields["completed"].append({
                #     "ID": str(k),
                #     "Crime": f'{v["crime_name"]}',
                #     "Initiated": f'{members.get(initId, {"name": "Player"})["name"]} [{v["initiated_by"]}].',
                #     "Money": f'${v["money_gain"]:,}',
                #     "Respect": f'{v["respect_gain"]:,}'})
                crimes_fields["completed"].append(f'{v["crime_name"]} `{str(k)}`')
                oc["mentions"].remove(str(k))

            # exit if completed
            if completed:
                continue

            # DEBUG: handy to comment this to have fake ready
            # change ready based on participants
            n_p_tot = len(v["participants"])
            n_p_rea = 0
            greatest_inactivity = int(time.time())
            greatest_inactivity_string = ""
            for p in v["participants"]:
                tId = list(p)[0]
                participant = members.get(tId, {})
                status = participant.get("status", {"state": "?", "description": "?"})
                last_action = participant.get("last_action", {"timestamp": 0, "relative": "?"})
                name = participant.get("name", "Player")
                if status["state"] != "Okay":
                    ready = False
                else:
                    n_p_rea += 1

                if last_action["timestamp"] < greatest_inactivity:
                    greatest_inactivity = last_action["timestamp"]
                    greatest_inactivity_string = f'{last_action["relative"]} ({name})'

            # if ready and not already mentionned -> mention
            if ready:
                crimes_fields["ready"].append([str(k), v["crime_name"], greatest_inactivity_string])
                need_to_display.append(v["crime_name"])
                if not mentionned and str(v["crime_id"]) in notifications:
                    need_to_mention = True
                    oc["mentions"].append(str(k))

            # if not ready (because of participants) and already mentionned -> remove the already mentionned
            if not ready and mentionned:
                crimes_fields["not_ready"].append(f'{v["crime_name"]} {n_p_rea}/{n_p_tot} `{str(k)}`')
                oc["mentions"].remove(str(k))

            if not ready and not mentionned:
                crimes_fields["waiting"].append(f'- {v["crime_name"]} {n_p_rea}/{n_p_tot} `{str(k)}`')

        # clean mentions
        cleanedMentions = []
        for k in oc["mentions"]:
            if str(k) in response["crimes"]:
                cleanedMentions.append(str(k))

        oc["mentions"] = cleanedMentions

        # delete old messages
        # fminutes = now - datetime.timedelta(minutes=5)
        # async for message in channel.history(limit=50, before=fminutes):
        #     if message.author.bot:
        #         await message.delete()

        # create the message
        notified = notified if need_to_mention else "OC"
        if not len(need_to_display):
            content = f'{notified} no crimes ready'
        elif len(need_to_display) == 1:
            content = f'{notified} {need_to_display[0]} ready'
        else:
            content = f'{notified} {len(need_to_display)} crimes ready'

        title = f"{fName}'s Organized Crimes"
        embed = Embed(title=title, color=my_blue)
        if len(crimes_fields["ready"]):
            list_of_crimes = []
            for crime_id, crime_name, inactivity in crimes_fields["ready"]:
                list_of_crimes.append(f':white_check_mark: [{crime_name}](https://www.torn.com/factions.php?step=your#/tab=crimes) `{crime_id}`\n Longest inactivity: {inactivity}')
                if len("\n".join(list_of_crimes)) > 1000:
                    list_of_crimes[-1] = '...'
                    break
            embed.add_field(name="Ready", value="\n".join(list_of_crimes))
        else:
            embed.add_field(name="Ready", value="None")

        if len(crimes_fields["waiting"]):
            list_of_crimes = []
            for v in crimes_fields["waiting"]:
                list_of_crimes.append(v)
                if len("\n".join(list_of_crimes)) > 1000:
                    list_of_crimes[-1] = '...'
                    break
            embed.add_field(name="Waiting", value="\n".join(list_of_crimes))

        if len(crimes_fields["not_ready"]):
            list_of_crimes = []
            for v in crimes_fields["not_ready"]:
                list_of_crimes.append(v)
                if len("\n".join(list_of_crimes)) > 1000:
                    list_of_crimes[-1] = '...'
                    break
            embed.add_field(name="Not Ready anymore", value="\n".join(list_of_crimes))

        if len(crimes_fields["completed"]):
            list_of_crimes = []
            for v in crimes_fields["completed"]:
                list_of_crimes.append(v)
                if len("\n".join(list_of_crimes)) > 1000:
                    list_of_crimes[-1] = '...'
                    break
            embed.add_field(name="Just Completed", value="\n".join(list_of_crimes))

        embed.set_footer(text=f'Last update: {ts_format(response["timestamp"], fmt="short")}')
        embed.timestamp = datetime.datetime.fromtimestamp(response["timestamp"], tz=pytz.UTC)

        # lookup in the last 10 messages to update instead of creating a new one
        # or delete if need a new mention
        async for message in channel.history(limit=2):
            if message.author.bot and len(message.embeds):
                # check title of embed to get the message
                eb1 = message.embeds[0].to_dict()
                if eb1.get('title') != title:
                    # print("pass, not good message")
                    continue

                # print("found message to update")

                # delete and create new message if need to mention
                if need_to_mention:
                    # print("delete message because need new mention")
                    await message.delete()
                    await send(channel, content, embed=embed)
                    return True

                # compare embed to see if needs to update or not
                if not message.embeds[0].to_dict().get('fields') == embed.to_dict().get('fields'):
                    # print("update message")
                    await message.edit(content=content, embed=embed)

                return True

        # if no message found send a new one
        # print("no message found")
        await send(channel, content, embed=embed)

        return True

    @tasks.loop(seconds=300)
    async def ocTask(self):
        logging.debug(f"[oc/notifications] start task")

        # iteration over all guilds
        for guild in self.bot.get_guilds_by_module("oc"):
            try:

                config = self.bot.get_guild_configuration_by_module(guild, "oc", check_key="currents")
                if not config:
                    logging.debug(f"[oc/notifications] <{guild}> No OC tracking")
                    continue

                # if not self.bot.get_guild_beta(guild):
                #     logging.debug(f"[oc/notifications] <{guild}> Skip OC beta because this server is not beta tester")
                #     continue

                logging.debug(f"[oc/notifications] <{guild}>  OC tracking")

                # iteration over all members asking for oc watch
                # guild = self.bot.get_guild(guild.id)
                todel = []
                tochange = {}
                for discord_user_id, oc in config["currents"].items():
                    # logging.debug(f"[oc/notifications] {guild}: {oc}")

                    # call oc faction
                    previous_mentions = list(oc.get("mentions", []))
                    status = await self._oc(guild, oc, config.get("notifications", {}))

                    if status and previous_mentions != oc.get("mentions", []):
                        tochange[discord_user_id] = oc
                    elif not status:
                        todel.append(discord_user_id)

                changes = False
                for d in todel:
                    logging.debug(f"[oc/notifications] <{guild}> delete current {d}")
                    del self.bot.configurations[guild.id]["oc"]["currents"][d]
                    changes = True

                for discord_user_id, oc in tochange.items():
                    logging.debug(f"[oc/notifications] <{guild}> change current {discord_user_id}")
                    self.bot.configurations[guild.id]["oc"]["currents"][discord_user_id] = oc
                    changes = True

                if changes:
                    await self.bot.set_configuration(guild.id, guild.name, self.bot.configurations[guild.id])
                    logging.debug(f"[oc/notifications] <{guild}> push notifications")
                else:
                    logging.debug(f"[oc/notifications] <{guild}> don't push notifications")

            except BaseException as e:
                logging.error(f'[oc/notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(f'error on oc notifications: {e}', guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on oc notifications"}
                await self.bot.send_log_main(e, headers=headers, full=True)

    @ocTask.before_loop
    async def before_ocTask(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

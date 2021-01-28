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
import aiohttp
import asyncio
import asyncpg
import json
import re
import os
import html
import logging

# import discord modules
import discord
from discord import Embed
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get

# import bot functions and classes
from inc.yata_db import reset_notifications
from inc.yata_db import get_credentials
from inc.handy import *


class API(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if self.bot.bot_id == 3:
            self.notify.start()

    def cog_unload(self):
        self.notify.cancel()

    @commands.command(aliases=['we'])
    @commands.guild_only()
    async def weaponexp(self, ctx, *args):
        """DM weaponexp to author"""
        logging.info(f'[api/weaponexp] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        # make api call
        response, e = await self.bot.api_call("user", "", ["weaponexp"], key, check_key=["weaponexp"], error_channel=ctx.author)
        if e:
            return

        # send list
        maxed = []
        tomax = []
        for w in response.get("weaponexp", []):
            if w["exp"] == 100:
                maxed.append(w)
            elif w["exp"] > 4:
                tomax.append(w)

        # convert exp to hits remainings
        def exp_to_hits(exp):
            if exp < 25:
                return (25 - exp) * 8 + 1800
            elif exp < 50:
                return (50 - exp) * 12 + 1500
            elif exp < 75:
                return (75 - exp) * 20 + 1000
            else:
                return (100 - exp) * 40

        lst = []
        eb = Embed(title=f"Weapon experience and remaining hits", colour=my_blue)
        n = 1
        for w in maxed:
            lst.append(f'{n: >2} {w["name"]}')
            n += 1

        if len(lst):
            eb.add_field(name="Weapon maxed", value="\n".join(lst))

        lst = []
        for w in tomax:
            lst.append(f'{n: >2} {w["name"]}: {w["exp"]}% ({exp_to_hits(int(w["exp"]))} hits)')
            n += 1

        if len(lst):
            eb.add_field(name="Experience > 5%", value="\n".join(lst))

        eb.set_image(url="https://awardimages.torn.com/615034470.png")
        await send(ctx.author, embed=eb)
        return

    @commands.command(aliases=['fh'])
    @commands.guild_only()
    async def finishing(self, ctx, *args):
        """DM number of finishing hits to author"""
        logging.info(f'[api/finishing] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        # make api call
        response, e = await self.bot.api_call("user", "", ["personalstats"], key, check_key=["personalstats"], error_channel=ctx.author)
        if e:
            return

        bridge = {"heahits": "Heavy artillery",
                  "chahits": "Mechanical guns",
                  "axehits": "Clubbin weapons",
                  "grehits": "Temporary weapons",
                  "machits": "Machine guns",
                  "pishits": "Pistols",
                  "rifhits": "Rifles",
                  "shohits": "Shotguns",
                  "smghits": "Sub machin guns",
                  "piehits": "Piercing weapons",
                  "slahits": "Slashing weapons",
                  "h2hhits": "Hand to hand"}

        finishingHits = []
        for k, v in bridge.items():
            finishingHits.append([v, response.get("personalstats", dict({})).get(k, 0)])

        lst = []
        # send list
        for fh in sorted(finishingHits, key=lambda x: -x[1]):
            lst.append(f"{fh[0]: <17} {fh[1]: >6,d}")

        eb = Embed(title=f"Finishing hits", description="\n".join(lst), colour=my_blue)
        eb.set_image(url="https://awardimages.torn.com/433435448.png")

        await send(ctx.author, embed=eb)
        return

    @commands.command(aliases=['net'])
    @commands.guild_only()
    async def networth(self, ctx, *args):
        """DM your networth breakdown (in case you're flying)"""
        logging.info(f'[api/networth] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        await ctx.message.delete()

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            return

        # make api call
        response, e = await self.bot.api_call("user", "", ["networth"], key, check_key=["networth"], error_channel=ctx.author)
        if e:
            return

        # send list
        lst = []
        eb = Embed(title=f"Networth breakdown", colour=my_blue)
        for k, v in response.get("networth", dict({})).items():
            if int(v):
                if k == "displaycase":
                    name = "Display Case"
                elif k == "stockmarket":
                    name = "Stock Market"
                else:
                    name = k.title()
                eb.add_field(name=name, value=f"${v:,.0f}")

        await send(ctx.author, embed=eb)
        return

    @commands.command(aliases=['profile', 'p', 'id'])
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def who(self, ctx, *args):
        """Gives information on a user"""
        logging.info(f'[api/who] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        # init variables
        helpMsg = f"You have to mention a member `!who @Kivou [2000607]` or enter a Torn ID or `!who 2000607`."

        logging.debug(f'[api/who] args: {args}')

        # send error message if no arg (return)
        if not len(args):
            logging.debug(f'[api/who] no args given')
            await self.bot.send_help_message(ctx.channel, helpMsg)
            return

        # check if arg is int
        elif args[0].isdigit():
            if len(args[0]) <= 7:  # torn ID
                logging.debug(f'[api/who] 1 int given -> torn user')
                tornId = int(args[0])
            else:  # discord ID (requires an API call)
                logging.debug(f'[api/who] 1 int given -> discord user')
                # get author key
                status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
                if status < 0:
                    await self.bot.send_error_message(ctx.channel, "Author key not found to make the API call")
                    return
                r, e = await self.bot.api_call("user", int(args[0]), ["discord"], key, error_channel=ctx.channel)
                if e or 'discord' not in r:
                    return
                tornId = r.get('discord', {}).get('userID', 0)
                if str(tornId).isdigit():
                    tornId = int(tornId)
                else:
                    await self.bot.send_error_message(ctx.channel, f"Discord ID `{args[0]}` not verified")
                    return

        # check if arg is a mention of a discord user ID
        elif re.match(r'<@!?\d+>', args[0]):
            discordId = re.findall(r'\d+', args[0])
            logging.debug(f'[api/who] 1 mention given -> discord member')

            if len(discordId) and discordId[0].isdigit():
                member = ctx.guild.get_member(int(discordId[0]))
            else:
                await self.bot.send_help_message(ctx.channel, helpMsg)
                return

            # check if member
            if member is None:
                await self.bot.send_error_message(ctx.channel, f"Couldn't find discord member: {discordId}.\nTry `!who < torn ID >`.")
                return

            # try to parse Torn user ID
            regex = re.findall(r'\[(\d{1,7})\]', member.display_name)
            if len(regex) == 1 and regex[0].isdigit():
                tornId = int(regex[0])
            else:
                status, tornId, _, _ = await self.bot.get_user_key(ctx, member, needPerm=False)
                if status in [-1, -2, -3]:
                    await self.bot.send_error_message(ctx.channel, "Could not find Torn ID within their display name and verification failed.\nTry `!who < Torn ID >`.")
                    return

        # other cases I didn't think of
        else:
            await self.bot.send_help_message(ctx.channel, helpMsg)
            return

        # at this point tornId should be a interger corresponding to a torn ID
        if ctx.message.content[1:3] == "id":
            await send(ctx, f"https://www.torn.com/profiles.php?XID={tornId}")
            return

        # get configuration for guild
        # status, _, key = await self.bot.get_master_key(ctx.guild)
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            await self.bot.send_error_message(ctx.channel, "Author key not found to make the API call")
            return

        # Torn API call
        selections = ["profile", "personalstats", "discord", "timestamp"]
        r, e = await self.bot.api_call("user", tornId, selections, key, error_channel=ctx.channel)
        if e:
            return

        eb = Embed(description=f'Level {r["level"]} | {r["rank"]} | {r["age"]:,d} days old', colour=my_blue)
        try:
            dm = self.bot.get_user(int(r["discord"].get("discordID")))
        except BaseException as e:
            dm = None

        if dm is not None:
            eb.set_author(name=f'{r["name"]} [{r["player_id"]}]', url=f'https://www.torn.com/profiles.php?XID={tornId}', icon_url=dm.avatar_url)
        else:
            eb.set_author(name=f'{r["name"]} [{r["player_id"]}]', url=f'https://www.torn.com/profiles.php?XID={tornId}')

        # status
        s = r["status"]
        if r["last_action"]["status"] == "Idle":
            online_status = ":orange_circle:"
        elif r["last_action"]["status"] == "Offline":
            online_status = ":red_circle:"
        else:
            online_status = ":green_circle:"
        lst = [
                f'Last Action: {r["last_action"]["relative"]}',
                f'Description: {s["description"]}',
            ]
        if s["details"]:
            lst.append(cleanhtml(s["details"]))
        lst.append(f'Life: {r["life"]["current"]:,d}/{r["life"]["maximum"]:,d}')
        eb.add_field(name=f"{online_status} Status", value="\n".join(lst))

        # items
        lst = [f'Xanax: {r["personalstats"].get("xantaken", 0):,d}', f'Refills: {r["personalstats"].get("refills", 0):,d}', f'SE: {r["personalstats"].get("statenhancersused", 0):,d}']
        eb.add_field(name="Energy", value="\n".join(lst))

        # faction
        if int(r["faction"]["faction_id"]):
            f = r["faction"]
            lst = [
                    f'Name: [{html.unescape(f["faction_name"])} [{f["faction_id"]}]](https://www.torn.com/factions.php?&step=profile&ID={f["faction_id"]})',
                    f'Position: {f["position"]}',
                    f'Days: since {f["days_in_faction"]} days'
                    ]
            eb.add_field(name="Faction", value="\n".join(lst))

        # company
        if int(r["job"]["company_id"]):
            j = r["job"]
            lst = [
                f'Name: [{html.unescape(j["company_name"])} [{j["company_id"]}]](https://www.torn.com/joblist.php?#!p=corpinfo&ID={j["company_id"]})',
                f'Position: {j["position"]}',
            ]
            eb.add_field(name="Company", value="\n".join(lst))

        # social
        lst = [f'Friends: {r["friends"]:,d}', f'Enemies: {r["enemies"]:,d}']
        if r["forum_posts"]:
            lst.append(f'Karma: {r["karma"]:,d} ({100 * r["karma"] // r["forum_posts"]}%)')
        else:
            lst.append(f'Karma: No forum post')
        eb.add_field(name="Social", value='\n'.join(lst))


        # Misc
        lst = [
                f'Networth: ${r["personalstats"].get("networth", 0):,d}',
        ]
        s = r["married"]
        if s["spouse_id"]:
            lst.append(f'Spouse: [{s["spouse_name"]} [{s["spouse_id"]}]](https://www.torn.com/profiles.php?&XID={s["spouse_id"]}) for {s["duration"]:,d} days')
        eb.add_field(name="Misc", value="\n".join(lst))


        # try:
        #     dm = self.bot.get_user(int(r["discord"].get("discordID")))
        #     eb.set_thumbnail(url=dm.avatar_url)
        # except BaseException:
        #     pass

        # if r.get("discord" {}).get("discordID", False):
        # eb.set_footer(text=f'Update: {ts_format(r["timestamp"], fmt="short")}')

        await send(ctx, embed=eb)


    @tasks.loop(minutes=1)
    async def notify(self):
        logging.debug("[api/notifications] start task")

        # main guild
        guild = get(self.bot.guilds, id=self.bot.main_server_id)

        # connect to YATA database of notifiers
        db_cred = get_credentials()
        dbname = db_cred["dbname"]
        del db_cred["dbname"]
        sql = 'SELECT "tId", "dId", "notifications", "value" FROM player_view_player_key WHERE "activateNotifications" = True;'
        con = await asyncpg.connect(database=dbname, **db_cred)

        # async loop over notifiers
        async with con.transaction():
            async for record in con.cursor(sql, prefetch=100, timeout=2):
                # get corresponding discord member
                member = get(guild.members, id=record["dId"])
                if member is None:
                    logging.warning(f'[api/notifications] reset notifications for discord [{record["dId"]}] torn [{record["tId"]}]')
                    # headers = {"error": "notifications", "discord": record["dId"], "torn": record["tId"]}
                    # await self.bot.send_log_main("member not found", headers=headers)
                    if self.bot.bot_id == 3:
                        await reset_notifications(record["tId"])
                    continue

                try:

                    # get notifications preferences
                    logging.debug(f'[api/notifications] {member.nick} / {member}')
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
                    response, e = await self.bot.api_call("user", "", keys, record["value"])

                    if e and 'error' in response:
                        logging.warning(f'[api/notifications] {member.nick} / {member} error in api payload: {response["error"]["code"]}: {response["error"]["error"]}')
                        continue

                    # notify event
                    if "event" in notifications:
                        if not response["notifications"]["events"]:
                            notifications["event"] = dict({})
                        else:
                            # loop over events
                            for k, v in response["events"].items():
                                # if new event not notified -> notify
                                if not v["seen"] and k not in notifications["event"]:
                                    await send(member, cleanhtml(v["event"]).replace(" [View]", ""))
                                    notifications["event"][k] = True

                                # if seen even already notified -> clean table
                                elif v["seen"] and k in notifications["event"]:
                                    del notifications["event"][k]

                    # notify message
                    if "message" in notifications:
                        if not response["notifications"]["messages"]:
                            notifications["messages"] = dict({})
                        else:
                            # loop over messages
                            for k, v in response["messages"].items():
                                # if new event not notified -> notify
                                if not v["seen"] and k not in notifications["message"]:
                                    await send(member, f'New message from {v["name"]}: {v["title"]}')
                                    notifications["message"][k] = True

                                # if seen even already notified -> clean table
                                elif v["seen"] and k in notifications["message"]:
                                    del notifications["message"][k]

                    # notify awards
                    if "award" in notifications:
                        if response["notifications"]["awards"]:
                            # if new award or different number of awards
                            if not notifications["award"].get("notified", False) or notifications["award"].get("notified") != response["notifications"]["awards"]:
                                s = "s" if response["notifications"]["awards"] > 1 else ""
                                await send(member, f'You have {response["notifications"]["awards"]} new award{s}')
                                notifications["award"]["notified"] = response["notifications"]["awards"]

                        else:
                            notifications["award"] = dict({})

                    # notify energy
                    if "energy" in notifications:
                        if response["energy"]["fulltime"] < 90:
                            if not notifications["energy"].get("notified", False):
                                await send(member, f'Energy at {response["energy"]["current"]} / {response["energy"]["maximum"]}')
                            notifications["energy"]["notified"] = True

                        else:
                            notifications["energy"] = dict({})

                    # notify nerve
                    if "nerve" in notifications:
                        if response["nerve"]["fulltime"] < 90:
                            if not notifications["nerve"].get("notified", False):
                                await send(member, f'Nerve at {response["nerve"]["current"]} / {response["nerve"]["maximum"]}')
                            notifications["nerve"]["notified"] = True

                        else:
                            notifications["nerve"] = dict({})

                    # notify chain
                    if "chain" in notifications:
                        if response["chain"]["timeout"] < 90 and response["chain"]["current"] > 10:
                            if not notifications["chain"].get("notified", False):
                                await send(member, f'Chain timeout in {response["chain"]["timeout"]} seconds')
                            notifications["chain"]["notified"] = True

                        else:
                            notifications["chain"] = dict({})

                    # notify education
                    if "education" in notifications:
                        if response["education_timeleft"] < 90:
                            if not notifications["education"].get("notified", False):
                                await send(member, f'Education ends in {response["education_timeleft"]} seconds')
                            notifications["education"]["notified"] = True

                        else:
                            notifications["education"] = dict({})

                    # notify bank
                    if "bank" in notifications:
                        if response["city_bank"]["time_left"] < 90:
                            if not notifications["bank"].get("notified", False):
                                await send(member, f'Bank investment ends in {response["city_bank"]["time_left"]} seconds (${response["city_bank"]["amount"]:,.0f})')
                            notifications["bank"]["notified"] = True

                        else:
                            notifications["bank"] = dict({})

                    # notify drug
                    if "drug" in notifications:
                        if response["cooldowns"]["drug"] < 90:
                            if not notifications["drug"].get("notified", False):
                                await send(member, f'Drug cooldown ends in {response["cooldowns"]["drug"]} seconds')
                            notifications["drug"]["notified"] = True

                        else:
                            notifications["drug"] = dict({})

                    # notify medical
                    if "medical" in notifications:
                        if response["cooldowns"]["medical"] < 90:
                            if not notifications["medical"].get("notified", False):
                                await send(member, f'Medical cooldown ends in {response["cooldowns"]["medical"]} seconds')
                            notifications["medical"]["notified"] = True

                        else:
                            notifications["medical"] = dict({})

                    # notify booster
                    if "booster" in notifications:
                        if response["cooldowns"]["booster"] < 90:
                            if not notifications["booster"].get("notified", False):
                                await send(member, f'Booster cooldown ends in {response["cooldowns"]["booster"]} seconds')
                            notifications["booster"]["notified"] = True

                        else:
                            notifications["booster"] = dict({})

                    # notify travel
                    if "travel" in notifications:
                        if response["travel"]["time_left"] < 90:
                            if not notifications["travel"].get("destination", False):
                                await send(member, f'Landing in {response["travel"]["destination"]} in {response["travel"]["time_left"]} seconds')
                            notifications["travel"] = response["travel"]

                        else:
                            notifications["travel"] = dict({})

                    # update notifications in YATA's database
                    await con.execute('UPDATE player_player SET "notifications"=$1 WHERE "dId"=$2', json.dumps(notifications), member.id)

                except BaseException as e:
                    logging.error(f'[api/notifications] {member.nick} / {member}: {hide_key(e)}')
                    # headers = {"guild": guild, "guild_id": guild.id, "member": f'{member.nick} / {member}', "error": "personal notification error"}
                    # await self.bot.send_log_main(e, headers=headers, full=True)

        await con.close()

    @notify.before_loop
    async def before_notify(self):
        await self.bot.wait_until_ready()

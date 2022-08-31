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
from inc.handy import *


class War(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warsTask.start()

    def cog_unload(self):
        self.warsTask.cancel()

    @tasks.loop(minutes=5)
    async def warsTask(self):
        logging.debug("[war/notifications] start task")

        guild = self.bot.get_guild(self.bot.main_server_id)
        _, _, key = await self.bot.get_master_key(guild)

        if key is None:
            logging.error(f"[war/notifications] Error no key found for on main server id {self.bot.main_server_id}")
            return

        response, e = await self.bot.api_call("torn", "", ["raids", "rackets", "territorywars", "timestamp"], key)
        if e:
            logging.error(f"[war/notifications] Error {e}")
            return

        # get previous data to compare with current api call
        _, randt_p = await self.bot.get_data("wars")
        wars_p = randt_p.get("territorywars", {})
        raids_p = randt_p.get("raids", {})

        mentions = []

        # Check for new wars
        for k, v in response["territorywars"].items():
            # no new war
            if k in wars_p:
                continue

            assaulting_faction_id = v["assaulting_faction"]
            assaulting_faction = self.bot.get_faction_name(assaulting_faction_id)
            defending_faction_id = v["defending_faction"]
            defending_faction = self.bot.get_faction_name(defending_faction_id)
            title = f"New assault over the sovereignty of {k}"
            url = f'https://www.torn.com/city.php#terrName={k}'
            embed = Embed(title=title, url=url, color=my_red)

            embed.add_field(name='Assaulting faction', value=f'[{html.unescape(assaulting_faction)}](https://www.torn.com/factions.php?step=profile&ID={assaulting_faction_id})')
            embed.add_field(name='Defending faction', value=f'[{html.unescape(defending_faction)}](https://www.torn.com/factions.php?step=profile&ID={defending_faction_id})')

            if k in response["rackets"]:
                embed.add_field(name="Racket", value=response["rackets"][k]["name"])

            embed.set_thumbnail(url=f'https://yata.yt/media/territories/50x50/{k}.png')
            embed.set_footer(text=f'Started: {ts_to_datetime(v["started"], fmt="short")} - Ends: {ts_to_datetime(v["ends"], fmt="short")}')
            mentions.append(embed)

        # Check for new raids
        for k, v in response["raids"].items():
            # no new raid
            if k in raids_p:
                continue

            assaulting_faction_id = v["assaulting_faction"]
            assaulting_faction = self.bot.get_faction_name(assaulting_faction_id)
            defending_faction_id = v["defending_faction"]
            defending_faction = self.bot.get_faction_name(defending_faction_id)
            title = f"New raid"

            embed = Embed(title=title, color=my_red)
            embed.add_field(name='Assaulting faction', value=f'[{html.unescape(assaulting_faction)}](https://www.torn.com/factions.php?step=profile&ID={assaulting_faction_id})')
            embed.add_field(name='Defending faction', value=f'[{html.unescape(defending_faction)}](https://www.torn.com/factions.php?step=profile&ID={defending_faction_id})')

            if str(v["started"]).isdigit():  # to handle bug in the API that currently returns a string
                embed.set_footer(text=f'Started: {ts_to_datetime(v["started"], fmt="short")}')
            else:
                embed.set_footer(text=f'Started: {v["started"]}')
            mentions.append(embed)

        # Check ended wars
        for k, v in wars_p.items():
            # war not over
            if k in response["territorywars"]:
                continue

            assaulting_faction_id = v["assaulting_faction"]
            assaulting_faction = self.bot.get_faction_name(assaulting_faction_id)
            defending_faction_id = v["defending_faction"]
            defending_faction = self.bot.get_faction_name(defending_faction_id)
            title = f"Assault ended over the sovereignty of {k}"
            url = f'https://www.torn.com/city.php#terrName={k}'

            # get result
            description = ''
            r_tmp, e = await self.bot.api_call("torn", "", ["territory"], key)
            if not e:
                t_faction = r_tmp.get("territory", {}).get(k, {}).get("faction", 0)
                if t_faction == assaulting_faction_id:
                    description = f"[{html.unescape(assaulting_faction)}](https://www.torn.com/factions.php?step=profile&ID={assaulting_faction_id}) successfully assaulted [{html.unescape(defending_faction)}](https://www.torn.com/factions.php?step=profile&ID={defending_faction_id})"
                elif t_faction == defending_faction_id:
                    description = f"[{html.unescape(defending_faction)}](https://www.torn.com/factions.php?step=profile&ID={defending_faction_id}) successfully defended against [{html.unescape(assaulting_faction)}](https://www.torn.com/factions.php?step=profile&ID={assaulting_faction_id})"

            embed = Embed(title=title, description=description, url=url, color=my_green)

            if not description:
                embed.add_field(name='Assaulting faction', value=f'[{html.unescape(assaulting_faction)}](https://www.torn.com/factions.php?step=profile&ID={assaulting_faction_id})')
                embed.add_field(name='Defending faction', value=f'[{html.unescape(defending_faction)}](https://www.torn.com/factions.php?step=profile&ID={defending_faction_id})')

            if k in response["rackets"]:
                embed.add_field(name="Racket", value=response["rackets"][k]["name"])

            embed.set_thumbnail(url=f'https://yata.yt/media/territories/50x50/{k}.png')
            embed.set_footer(text=f'Started: {ts_to_datetime(v["started"], fmt="short")}')
            mentions.append(embed)


        # Check ended raids
        for k, v in raids_p.items():
            # raid not over
            if k in response["raids"]:
                continue

            assaulting_faction_id = v["assaulting_faction"]
            assaulting_faction = self.bot.get_faction_name(assaulting_faction_id)
            defending_faction_id = v["defending_faction"]
            defending_faction = self.bot.get_faction_name(defending_faction_id)
            title = f"Raid ended"

            embed = Embed(title=title, color=my_green)
            embed.add_field(name='Assaulting faction', value=f'[{html.unescape(assaulting_faction)}](https://www.torn.com/factions.php?step=profile&ID={assaulting_faction_id})')
            embed.add_field(name='Defending faction', value=f'[{html.unescape(defending_faction)}](https://www.torn.com/factions.php?step=profile&ID={defending_faction_id})')
            embed.add_field(name='Assaulting score', value=v["assaulting_score"])
            embed.add_field(name='Defending score', value=v["defending_score"])

            if str(v["started"]).isdigit():  # to handle bug in the API that currently returns a string
                embed.set_footer(text=f'Started: {ts_to_datetime(v["started"], fmt="short")}')
            else:
                embed.set_footer(text=f'Started: {v["started"]}')
            mentions.append(embed)


        logging.debug(f'[war/notifications] mentions: {len(mentions)}')

        logging.debug(f"[war/notifications] push wars")
        await self.bot.push_data(int(response["timestamp"]), response, "wars")

        # DEBUG
        # embed = Embed(title="Test Racket")
        # mentions.append(embed)

        if not len(mentions):
            logging.debug(f"[war/notifications] no notifications")
            return

        # iteration over all guilds
        for guild in self.bot.get_guilds_by_module("wars"):
            try:
                logging.debug(f"[war/notifications] {guild}")

                config = self.bot.get_guild_configuration_by_module(guild, "wars", check_key="channels_alerts")
                if not config:
                    logging.info(f"[war/notifications] No wars channels for guild {guild}")
                    continue

                # get role & channel
                role = self.bot.get_module_role(guild.roles, config.get("roles_alerts", {}))
                channel = self.bot.get_module_channel(guild.channels, config.get("channels_alerts", {}))

                if channel is None:
                    continue

                for m in mentions:
                    dmsg = await send(channel, '' if role is None else f'Wars update {role.mention}', embed=m)
                    # publish if possible
                    try:
                        await dmsg.publish()
                        logging.debug(f"[war/notifications] guild {guild}: published.")
                    except:
                        logging.debug(f"[war/notifications] guild {guild}: not published.")

            except discord.Forbidden as e:
                logging.error(f'[war/notifications] {guild} [{guild.id}]: {hide_key(e)}')
                pass

            except BaseException as e:
                logging.error(f'[war/notifications] {guild} [{guild.id}]: {hide_key(e)}')
                await self.bot.send_log(f'Error during a war alert: {e}', guild_id=guild.id)
                headers = {"guild": guild, "guild_id": guild.id, "error": "error on war notifications"}
                await self.bot.send_log_main(e, headers=headers, full=True)

    @warsTask.before_loop
    async def before_warsTask(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(10)

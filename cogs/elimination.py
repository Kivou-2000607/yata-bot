"""
Copyright 2021 kivou@yata.yt

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


class Elimination(commands.Cog):
    def __init__(self, bot, api_token):
        self.bot = bot
        self.api_token = api_token
        self.score.start()
        self.wave.start()

        # temp store message ID to avoid message history lookup
        self.message_id = {}

    def cog_unload(self):
        self.wave.cancel()
        self.score.cancel()

    async def elim_api_call(self, id):
        url = f'https://elimination.me/api/user/{id}/elimination'
        headers={"Authorization": f"Bearer {self.api_token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as r:
                if r.status == 200:
                    return await r.json()
                elif r.status == 404:
                    return {'error': {'error': 'Invalid or unkown user ID', 'code': 404}}
                else:
                    return {'error': {'error': 'Invalid or unkown user ID', 'code': r.status}}


    ############
    # COMMANDS #
    ############
    @commands.command(aliases=['elim'])
    @commands.guild_only()
    async def elimination(self, ctx, *args):
        """Get elimination scores"""
        logging.info(f'[elimination/elim] {ctx.guild}: {ctx.author.nick} / {ctx.author}')

        logging.debug(f'[elimination/elim] args: {args}')

        # self restults if not args
        if not len(args):
            torn_or_discord_id = ctx.author.id

        # check if arg is int
        elif args[0].isdigit():
            logging.debug(f'[elimination/elim] 1 int given -> torn user')
            torn_or_discord_id = int(args[0])  # now it can also be a user ID

        # check if arg is a mention of a discord user ID
        elif re.match(r'<@!?\d+>', args[0]):
            torn_or_discord_id = re.findall(r'\d+', args[0])[0]
            logging.debug(f'[elimination/elim] 1 mention given -> discord member')

        # other cases I didn't think of
        else:
            await self.bot.send_help_message(ctx.channel, "You have to mention a member `!elim @mention` or enter a Torn ID or `!elim 2000607`.")
            return

        # get user key
        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            await self.bot.send_error_message(ctx.channel, "Author key not found to make the API call")
            return


        logging.debug(f'[elimination/elim] id {torn_or_discord_id}')
        # make torn api call
        r, e = await self.bot.api_call("user", torn_or_discord_id, [], key, error_channel=ctx.channel)
        if e:
            return

        description = []
        if "team" in r["competition"]:
            if r["competition"]["team"]:
                description.append(f'**Live data**')
                description.append(f'__2021__ {r["competition"]["team"].replace("-", " ").title()}')
                description.append("```")
                description.append(f'Attacks: {r["competition"]["attacks"]:>5,d}')
                description.append("```")
            else:
                now = ts_now()
                start = 1631275200
                description.append(f"__2021__ Elimination starts in {s_to_hms(start - now)}\n")
        else:
            description.append("__2021__ did not participate\n")

        # past years
        # make pyrit api call
        description.append(f'**Ranks**')
        s = await self.elim_api_call(torn_or_discord_id)
        if "error" in s:
            description.append("\n*No data found*")
        else:
            for y in ["2021", "2020", "2019"]:
                if s[y]:
                    description.append(f'__{y}__ {s[y]["team"].replace("-", " ").title()}')
                    description.append("```")

                    k = "attacks"
                    title = f'{k.replace("_", " ").title()}:'
                    description.append(f'{title:<13} {s[y][k]:>5,d}')
                    k = "rank_in_team"
                    title = f'{k.replace("_", " ").title()}:'
                    if s[y]["percentile"]:
                        description.append(f'{title:<13} {s[y][k]:>5,d} ({s[y]["percentile"]}%)')
                    else:
                        description.append(f'{title:<13} {s[y][k]:>5,d}')
                    k = "rank"
                    title = f'{k.replace("_", " ").title()}:'
                    description.append(f'{title:<13} {s[y][k]:>5,d}')
                    k = "deserted"
                    title = f'{k.replace("_", " ").title()}:'
                    description.append(f'{title:<13} {"yes" if s[y][k] else "no":>5}')

                    description.append("```")
                else:
                    description.append(f"**{y}** did not participate")

        eb = Embed(title=f'Elimination: {r["name"]} [{r["player_id"]}]', description="\n".join(description), colour=my_blue)
        eb.set_footer(text="Dataset from Pyrit [2111649]")
        await send(ctx.channel, embed=eb)


    #########
    # SCORE #
    #########
    @tasks.loop(seconds=60)
    async def score(self):

        async def _update_score(guild, embed):
            try:
                if guild is None:
                    logging.debug(f"[elimination score] guild {guild}: None")
                    return

                # get configuration
                config = self.bot.get_guild_configuration_by_module(guild, "elim", check_key="channels_scores")
                if not config:
                    logging.debug(f"[elimination score] guild {guild}: score not enabled")
                    return

                # get channel
                for k, v in config["channels_scores"].items():  # only the first one
                    channel = get(guild.channels, id=int(k))
                    if channel is None:
                        logging.debug(f"[elimination score] guild {guild}: channel {v} [{k}]")
                        return
                    break

                try:
                    msg = await channel.fetch_message(self.message_id.get(guild.id))
                    await msg.edit(embed=embed)
                    logging.debug(f"[elimination score] guild {guild}: edit message")
                    return

                except BaseException as e:
                    logging.warning(f"[elimination score] guild {guild}: base error {e}")
                    return

            except BaseException as e:
                logging.error(f"[elimination score] guild {guild}: {e}")

        # sleep to the minute
        sleep = 65 - ts_now() % 60
        logging.info(f'[elimination score] sleep for {sleep}s')
        await asyncio.sleep(sleep)

        # create embed
        embed = Embed(title="Elimination scores", color=550000)

        # update scores
        guild = self.bot.get_guild(self.bot.main_server_id)
        _, _, key = await self.bot.get_master_key(guild)

        r, e = await self.bot.api_call("torn", "", ["competition", "timestamp"], key)
        if e:
            logging.warning(f"[elimination score] Error {e}")
            embed.add_field(name=f'API error code #{r["error"]["code"]}', value=r["error"]["error"])
            embed.set_footer(text=f'Last update: {ts_format(ts_now(), fmt="time")}')

        else:
            for team in r["competition"]["teams"]:
                values = [f'[Participants: {team["participants"]}](https://www.torn.com/competition.php#/p=team&team={team["team"]})',
                          f'Score: {team["score"]}',
                          f'Lives: **{team["lives"]}**']
                embed.add_field(name=f'#{team["position"]} {team["name"]}', value='\n'.join(values))
                embed.set_footer(text=f'Last update: {ts_format(r["timestamp"], fmt="time")}')

        # get score guild
        guilds = self.bot.get_guilds_by_module("elim")
        await asyncio.gather(*map(_update_score, guilds, [embed] * len(guilds)))

    @score.before_loop
    async def before_score(self):
        await self.bot.wait_until_ready()

    #########
    # WAVES #
    #########
    @tasks.loop(seconds=10)
    async def wave(self):

        async def _update_wave(guild):
            try:
                if guild is None:
                    logging.debug(f"[elimination wave] guild {guild}: None")
                    return

                # get configuration
                config = self.bot.get_guild_configuration_by_module(guild, "elim", check_key="channels_scores")
                if not config:
                    logging.debug(f"[elimination wave] guild {guild}: score not enabled")
                    return

                # get channel
                for k, v in config["channels_scores"].items():  # only the first one
                    channel = get(guild.channels, id=int(k))
                    if channel is None:
                        logging.debug(f"[elimination wave] guild {guild}: channel {v} [{k}]")
                        return
                    break

                now = ts_now()
                start = 1631275200
                if now < start:
                    content = f"Elimination starts in **{s_to_hms(start - now)}**"

                else:
                    now = ts_to_datetime(now)
                    m = 14 - now.minute % 15
                    s = 59 - now.second
                    content = f"Next wave in **{m}:{s:02d}**"

                # look for the message
                message_id = None
                if guild.id in self.message_id:
                    message_id = self.message_id[guild.id]
                    logging.debug(f"[elimination wave] guild {guild}: message ID {message_id} found in memory")
                else:
                    for msg in [m for m in await channel.history(limit=5).flatten() if m.author == self.bot.user]:
                        message_id = msg.id
                        logging.debug(f"[elimination wave] guild {guild}: message ID {message_id} found in history")
                        break

                if message_id is None:
                    logging.debug(f"[elimination wave] guild {guild}: message not found")
                    if guild.id in self.message_id:  # cleanup in case None was recorded
                        del self.message_id[guild.id]
                        logging.warning(f"[elimination wave] guild {guild}: purging message ID from memory")

                try:
                    if message_id is None:
                        msg = await channel.send(content=content)
                        logging.debug(f"[elimination wave] guild {guild}: send message (message ID was None)")
                    else:
                        msg = await channel.fetch_message(message_id)
                        await msg.edit(content=content)
                        logging.debug(f"[elimination wave] guild {guild}: edit message")

                    self.message_id[guild.id] = msg.id
                    return

                except (discord.NotFound, discord.Forbidden) as e:
                    msg = await channel.send(content=content)
                    logging.debug(f"[elimination wave] guild {guild}: send message ({e})")
                    self.message_id[guild.id] = msg.id
                    return

                except discord.HTTPException as e:
                    logging.warning(f"[elimination wave] guild {guild}: http exception ({e})")
                    if guild.id in self.message_id:
                        del self.message_id[guild.id]
                        logging.warning(f"[elimination wave] guild {guild}: purging message ID from memory")
                    return

            except BaseException as e:
                logging.error(f"[elimination wave] guild {guild}: {e}")
                return

        # sleep to 10 seconds
        sleep = 9 - ts_now() % 10
        logging.info(f'[elimination wave] sleep for {sleep}s')
        await asyncio.sleep(sleep)

        # get score guild
        guilds = self.bot.get_guilds_by_module("elim")
        await asyncio.gather(*map(_update_wave, guilds))


    @wave.before_loop
    async def before_wave(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)

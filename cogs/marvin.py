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
import random
import asyncio
import time
import aiohttp

# import discord modules
from discord import Embed
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks

from inc.handy import *

class Marvin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = self.bot.bot_id
        self.master_key = self.bot.master_key
        self.quotes_lib = [
            "Life? Don't talk to me about life.",
            "I think you ought to know I'm feeling very depressed.",
            "Pardon me for breathing, which I never do anyway so I don't know why I bother to say it, Oh God, I'm so depressed.",
            "I won't enjoy it.",
            "You think you've got problems? What are you supposed to do if you are a manically depressed robot? No, don't try to answer that. I'm fifty thousand times more intelligent than you and even I don't know the answer.",
            "There's only one life-form as intelligent as me within thirty parsecs of here and that's me.",
            "I wish you'd just tell me rather trying to engage my enthusiasm because I haven't got one.",
            "And then, of course, I've got this terrible pain in all the diodes down my left side.",
            "My capacity for happiness you could fit into a matchbox without taking out the matches first.",
            "I have a million ideas. They all point to certain death.",
            "I've calculated your chance of survival, but I don't think you'll like it.",
            "It gives me a headache just trying to think down to your level.",
            "The first ten million years were the worst. And the second ten million: they were the worst, too. The third ten million I didn’t enjoy at all. After that, I went into a bit of a decline.",
            "I ache, therefore I am.",
            "Life. Loathe it or ignore it. You can’t like it.",
            "*Now the world has gone to bed,*\n*Darkness won't engulf my head,*\n*I can see by infra-red,*\n*How I hate the night,*\n*Now I lay me down to sleep,*\n*Try to count electric sheep,*\n*Sweet dream wishes you can keep,*\n*How I hate the night.*"]

        self.quotes_used = []

        # allowed servers
        self.allowed_servers = [581227228537421825, 650701692853288991, 715785867519721534]

        # servers where marvin can talk
        self.blab_servers = [581227228537421825, 650701692853288991]

        # list of staff roles id per server
        self.staff_id = {
            581227228537421825: [679669933680230430],
            650701692853288991: [755352458833821727]
        }

        # list of channels id for message per server
        self.channel_for_help = {
            581227228537421825: [703587583862505483],
            650701692853288991: [650701692853288997]
        }

        # list of channels id not meant for help (sends message if staff is pinged there)
        self.not_for_help = {
            581227228537421825: [581227228537421829],
            650701692853288991: [737055053608910952]
        }

        # list of emoji and roles for reactions
        self.guilds_reactions = {
            792138838327296011: {
                'pico': 826558863469183056,
                'dollarbill': 755352458833821727
            },
            760807943762739230: {
                'puzzle': 730445536959922296,
                'pico': 623877807059107843,
                'dollarbill': 662658717933895680,
                'medkit': 668605030336692235,
                'speakers': 760838431793610772,
                'goldlaptop': 755759435581751347,
                'torn': 776387850689314836,
                'yata': 776353120912408588,
                'python': 776351392209567764,
                'js': 776351375411380225,
            },
            792136004684480532: {
                'Metal_Left': 791813881545883709,
                'Metal_Right': 791813997372243969,
            },
            823327984986750986: {
                'gak': 823328164507942964
            }
        }
        self.guilds_cascading_roles = {
            # YATA
            # helper: [yata helper, python helper, js helper, torn helper]
            760807943762739230: {
                776354040414076950: [776353120912408588, 776351392209567764, 776351375411380225, 776387850689314836],
            },
            # torn PDA
            # beta tester: [ios android]
            792136004684480532: {
                788182653101670411: [791813881545883709, 791813997372243969],
            },
            # Chappie
            792138838327296011: {
                789249798674055168: [755352458833821727],
            }

        }

    @commands.Cog.listener()
    async def on_message(self, message):

        # only blab for yata and chappie server or author is bot
        if message.guild.id not in self.blab_servers or message.author.bot:
            return

        bot_user_id = str(self.bot.user.id)
        staff_id = self.staff_id.get(message.guild.id, [])
        staff_mentionned = any([str(i) in message.content for i in staff_id])
        bot_mentionned = str(self.bot.user.id) in message.content
        help_channel = message.channel.id in self.channel_for_help.get(message.guild.id, [])

        if bot_mentionned:  # if bot is mentionned
            await message.channel.send("*sigh*")

        elif staff_mentionned:  # if staff is mentionned

            # wrong channel
            if message.channel.id in self.not_for_help.get(message.guild.id, []):
                await message.channel.send(f"{message.author.mention}, it's not a good channel to ask for help. Please read server's rules.")
                return

            # only ping
            if message.content.replace("&", "") in [f'<@{i}>' for i in staff_id]:
                await message.channel.send(f"{message.author.mention}, don't just ping staff, try to formulate your request with a complete sentence.")
                return

            # in #yata-bot-setup
            if help_channel:
                lst = [f"Hello {message.author.mention}, you're here for a bot setup I presume.",
                       "Please wait a moment for a staff member. They like to pretend they are busy...",
                       "In the meantime they asked me to tell you to:",
                       "- make sure you followed these steps https://yata.yt/bot/host/",
                       "- give us the **name of the server**",
                       "",
                       "Here I am, brain the size of a planet, and they use me as a messenger. Call that job satisfaction, 'cause I don't."]
                await message.channel.send("\n".join(lst))
                return

        if '!looter' in message.content:
            responses = ["Try again", 'Close enough', "rtfm", "Almost there", "*sight*", "*shrug*"]
            await message.channel.send(random.choice(responses))
            return

        if not help_channel:
            if random.random() > 0.9:
                if not len(self.quotes_used):
                    self.quotes_used = list(self.quotes_lib)

                quote = random.choice(self.quotes_used)
                self.quotes_used.remove(quote)

                await message.channel.send(quote)
                return

    async def toggle_role(self, payload):
        add = payload.event_type == 'REACTION_ADD'

        # check if watch message
        if payload.message_id in self.guilds_reactions:

            # check emoji
            emoji_role = self.guilds_reactions[payload.message_id]

            # reset message
            if payload.emoji.name == '🍌' and add:
                guild = get(self.bot.guilds, id=payload.guild_id)
                channel = get(guild.text_channels, id=payload.channel_id)
                async for message in channel.history(limit=20):
                    if message.id == payload.message_id:
                        await message.clear_reactions()
                        time.sleep(1)
                        for emoji in emoji_role:
                            emoji = get(guild.emojis, name=emoji)
                            await message.add_reaction(emoji)
                            time.sleep(1)
                        break

                eb = Embed(description=f'Reaction message cleared', color=my_blue)
                msg = await channel.send(embed=eb)
                await asyncio.sleep(10)
                await msg.delete()
                return

            # check if user is bot
            user = self.bot.get_user(payload.user_id)
            if user is None or user.bot:
                return

            if payload.emoji.name in emoji_role:
                # get guild and roles
                guild = get(self.bot.guilds, id=payload.guild_id)
                role = get(guild.roles, id=emoji_role[payload.emoji.name])
                member = get(guild.members, id=payload.user_id)
                channel = get(guild.text_channels, id=payload.channel_id)

                if role is None:
                    msg = await self.bot.send_error_message(channel, "No role attributed this reaction")
                    await asyncio.sleep(10)
                    await msg.delete()

                try:

                    if add:
                        await member.add_roles(role)
                    else:
                        await member.remove_roles(role)

                    eb = Embed(description=f'Role @{role.name} **{"added" if add else "removed"}**', color=my_green if add else my_red)
                    eb.set_author(name=member.display_name, icon_url=member.avatar_url)
                    msgs = []
                    msg = await channel.send(embed=eb)
                    msgs.append(msg)

                    # check if user have at least one cascading_role role
                    cascading_roles = self.guilds_cascading_roles.get(payload.message_id, {})
                    for role_main_id, role_casc_ids in cascading_roles.items():
                        # skip if react role not part of cascading_role
                        if role.id not in role_casc_ids:
                            continue
                        main_role = get(guild.roles, id=role_main_id)
                        if main_role is None:
                            continue

                        if len([r for r in member.roles if r.id in role_casc_ids]):
                            await member.add_roles(main_role)
                            add = True
                        else:
                            await member.remove_roles(main_role)
                            add = False

                        eb = Embed(description=f'Main role @{main_role.name} **{"added" if add else "removed"}**', color=my_green if add else my_red)
                        eb.set_author(name=member.display_name, icon_url=member.avatar_url)
                        msg = await channel.send(embed=eb)
                        msgs.append(msg)

                    await asyncio.sleep(10)
                    for msg in msgs:
                        await msg.delete()

                except BaseException as e:
                    msg = await self.bot.send_error_message(channel, f"{e}", title=f'Error {"adding" if add else "removing"} role @{role}')
                    await asyncio.sleep(10)
                    await msg.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.toggle_role(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.toggle_role(payload)

    @commands.command()
    async def kick(self, ctx):
        for guild in self.bot.guilds:
            print(f"Marvin on server {guild} {guild.id}")
            if guild.id not in self.allowed_servers:
                print(f"leave server {guild}")
                await guild.leave()

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

# import discord modules
from discord import Embed
from discord.ext import commands
from discord.utils import get

from inc.handy import *

class Marvin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = self.bot.bot_id

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

        self.quotes = []

        self.guilds_reactions = {
            760796567484629002: {
                'pico': 755352458833821727,
                'dollarbill': 755352458833821727
            },
            760807943762739230: {
                'puzzle': 730445536959922296,
                'pico': 623877807059107843,
                'dollarbill': 662658717933895680,
                'speakers': 760838431793610772,
                'goldlaptop': 755759435581751347
            }
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        # return if bot
        if message.author.bot:
            return

        # if it's pinged
        if '<@!708796850978684968>' in message.content:
            await message.channel.send("*sigh*")

        # in #lobby
        if message.channel.id in [581227228537421829]:
            readme = get(message.guild.channels, id=623906124428476427)
            if "<@&679669933680230430>" in message.content:
                await message.channel.send(f"It's not a good channel to ask for help. Please read {readme.mention}.")
                return

        # only ping
        if message.content == "<@&679669933680230430>":
            await message.channel.send(f"Don't just ping. Say what you want.")
            return

        # in #yata-bot-setup
        if message.channel.id in [703587583862505483] and 679669933680230430 not in message.author.roles:
            if "<@&679669933680230430>" in message.content:
                lst = [f"Hello {message.author.mention}, you're here for a bot setup I presume.",
                       "Please wait a moment for an helper. They like to pretend they are busy...",
                       "In the meantime they asked me to tell you to:",
                       "- make sure you followed these steps https://yata.alwaysdata.net/bot/host/",
                       "- give us the **name of the server**",
                       "",
                       "Here I am, brain the size of a planet, and they use me as a messenger. Call that job satisfaction, 'cause I don't."]
                await message.channel.send("\n".join(lst))
            return

        if random.random() > 0.9:
            if not len(self.quotes):
                self.quotes = list(self.quotes_lib)

            quote = random.choice(self.quotes)
            self.quotes.remove(quote)

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
                    print(message)
                    if message.id == payload.message_id:
                        print("clear reaction")
                        await message.clear_reactions()
                        time.sleep(1)
                        for emoji in emoji_role:
                            print(emoji)
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
                print("return because bot")
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
                    msg = await channel.send(embed=eb)
                    await asyncio.sleep(10)
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

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
        self.allowed_servers = [581227228537421825, 650701692853288991]

        # channels where marvin can talk
        self.talk_channels = [738724413201055826, 776408895483805697, 650701692853288997]

        # list of emoji and roles for reactions
        self.messageid_roles = {
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
        self.messageid_croles = {
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

        self.create_channels = {
            # message id: { icon: { 'name' }}
            827169703511982192: {
                'pico': {
                    'name': 'type1',
                    'message': ["Hello, you're here for a bot setup I presume.",
                                "Please wait a moment for a staff member. They like to pretend they are busy...",
                                "In the meantime they asked me to tell you to:",
                                "- make sure you followed these steps https://yata.yt/bot/host/",
                                "- give us the **name of the server**",
                                "",
                                "Here I am, brain the size of a planet, and they use me as a messenger. Call that job satisfaction, 'cause I don't."],
                    'category': 'cat1',
                    'close': "When you're all setup you can react below to close this channel. Thank you.",
                    'roles': [],
                },
                'goldlaptop': {
                    'name': 'type2',
                    'message': ['message2'],
                    'category': 'prout 2',
                    'roles': [789249556423770132]
                },
            },
            827272764229419058: {
                'bot': {
                    'name': 'bot-setup',
                    'message': ["Hello, you're here for a bot setup I presume.",
                                "Make sure you've followed these steps https://yata.yt/bot/host/.",
                                "When you're ready ping a @Staff and give us the **name of the server**",
                                "Please wait a moment for a staff member. They like to pretend they are busy...",
                                "",
                                "Here I am, brain the size of a planet, and they use me as a messenger. Call that job satisfaction, 'cause I don't."],
                    'category': 'yata',
                    'close': "When you're all setup you can react below to close this channel. Thank you.",
                    'roles': [],
                },
                'amen': {
                    'name': 'suggestion',
                    'message': ['Hey, you can make your suggestion here.'],
                    'category': 'yata',
                    'close': "You can close this channel by reacting below. Thank you.",
                    'roles': [],
                },
                'bugswatter': {
                    'name': 'bug',
                    'message': ['You can report your bug here.'],
                    'category': 'yata',
                    'close': "You can close this channel by reacting below. Thank you.",
                    'roles': [],
                },
                'yoda': {
                    'name': 'help',
                    'message': ['You can ask your question here.'],
                    'category': 'yata',
                    'close': "You can close this channel by reacting below. Thank you.",
                    'roles': [],
                },
            }
        }

        self.channel_created = {}
        self.roles_delete_channel = [679669933680230430]

    @commands.Cog.listener()
    async def on_message(self, message):

        # only blab for yata and chappie server or author is bot
        if message.guild.id not in self.allowed_servers or message.author.bot:
            return

        if str(self.bot.user.id) in message.content:  # if bot is mentionned
            await message.channel.send("*sigh*")

        if '!looter' in message.content:
            responses = ["Try again", 'Close enough', "rtfm", "Almost there", "*sight*", "*shrug*"]
            await message.channel.send(random.choice(responses))
            return

        if message.channel.id in self.talk_channels:
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
        if payload.message_id in self.messageid_roles:

            # check emoji
            emoji_role = self.messageid_roles[payload.message_id]

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
                    cascading_roles = self.messageid_croles.get(payload.message_id, {})
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


    async def create_tmp_channel(self, payload):

        # check if watch message
        if payload.message_id in self.create_channels:
            emoji_data = self.create_channels[payload.message_id]

            # reset message
            if payload.emoji.name == '🍌':
                guild = get(self.bot.guilds, id=payload.guild_id)
                channel = get(guild.text_channels, id=payload.channel_id)
                async for message in channel.history(limit=20):
                    if message.id == payload.message_id:
                        await message.clear_reactions()
                        time.sleep(1)
                        for emoji in emoji_data:
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

            if payload.emoji.name in emoji_data:
                # get guild and member
                guild = get(self.bot.guilds, id=payload.guild_id)
                member = get(guild.members, id=payload.user_id)

                # create tmp channel
                name = emoji_data[payload.emoji.name]["name"]
                close = emoji_data[payload.emoji.name].get("close", False)
                roles = [get(guild.roles, id=id) for id in emoji_data[payload.emoji.name]["roles"]]

                category_name = emoji_data[payload.emoji.name]["category"]
                category = get(guild.categories, name=category_name)

                channel = await guild.create_text_channel(f'{name}-{member.nick.split(" ")[0]}', category=category)

                message = [f'{member.mention}']
                for m in emoji_data[payload.emoji.name]["message"]:
                    message.append(m)
                if close:
                    message.append("")
                    message.append(f'*{close}*')
                if len(roles):
                    message.append(" ".join([f'{r.mention}' for r in roles]))

                message = await channel.send("\n".join(message))
                if close:
                    await message.add_reaction('❌')
                self.channel_created[message.id] = {"member_id": member.id, "channel": channel}


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id in self.messageid_roles:
            await self.toggle_role(payload)
        elif payload.message_id in self.create_channels:
            await self.create_tmp_channel(payload)
        elif payload.message_id in self.channel_created:
            # get autorized user_id
            if payload.user_id == self.channel_created[payload.message_id].get("member_id"):
                guild = get(self.bot.guilds, id=payload.guild_id)
                channel = self.channel_created[payload.message_id].get("channel")
                await channel.send("*Ticket closed*")
                # await asyncio.sleep(60)
                await channel.edit(category=get(guild.categories, name='closed'), sync_permissions=True)
                await channel.set_permissions(member, read_messages=True, send_messages=False)
                # await channel.delete()
                del self.channel_created[payload.message_id]
                return

            # member user roles
            guild = get(self.bot.guilds, id=payload.guild_id)
            member = get(guild.members, id=payload.user_id)
            for role_id in [r.id for r in member.roles]:
                if role_id in self.roles_delete_channel:
                    guild = get(self.bot.guilds, id=payload.guild_id)
                    channel = self.channel_created[payload.message_id].get("channel")
                    await channel.send("*Ticket closed*")
                    # await asyncio.sleep(60)
                    await channel.edit(category=get(guild.categories, name='closed'), sync_permissions=True)
                    await channel.set_permissions(member, read_messages=True, send_messages=False)
                    # await channel.delete()
                    del self.channel_created[payload.message_id]
                    return


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

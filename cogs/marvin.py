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
from inc.yata_db import get_assists

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
        self.get_assists.start()

        def cog_unload(self):
            self.get_assists.cancel()

        self.clean_assists.start()

        def cog_unload(self):
            self.clean_assists.cancel()

        # server id: channel id for assist tools
        # self.assist_server_interaction = 650701692853288991  # chappie
        self.assist_server_interaction = 646420161372356648  # AK
        self.assist_servers = {
            650701692853288991: [650701692853288997],
            646420161372356648: [646471341205225473],
        }

        self.assist_spam = {
            650701692853288991: {},
            646420161372356648: {},
        }
        self.TIME_BETWEEN_ASSISTS = 30

        self.quotes_used = []

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
                'pico': 755352458833821727,
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

    async def handle_assist(self, message=None, assist=None):

        # return if no message send and no assist from db
        if message is None and assist is None:
            return

        # if assist from db sends init message
        if message is None:
            # send initial message
            guild = get(self.bot.guilds, id=self.assist_server_interaction)
            channel = get(guild.channels, id=self.assist_servers[guild.id][0])
            # channel_id = self.assist_servers[self.assist_server_interaction]
            # channel_id = self.assist_servers[self.assist_server_interaction]
            message = await channel.send("Incoming assist from TORN...")

        # only listen to specific channel
        if message.channel.id not in self.assist_servers[message.guild.id]:
            return

        # get target and player ids
        if assist is None:  # if from discord message
            # try to get and number of players
            split_content = message.content.split(" ")
            n_assists = "4"
            if len(split_content) > 1:
                n_assists = " ".join(split_content[1:])

            # check if isdigit
            if split_content[0].isdigit():
                target_id = int(split_content[0])

            else:
                # search 1
                search = re.search("XID=\d+", split_content[0])

                if search is None:
                    # search 2
                    search = re.search("user2ID=\d+", split_content[0])

                if search is None:
                    return

                target_id = int(search.group(0).split("=")[1])

            target_name = "Player"
            player_name = message.author.display_name

        else:  # if from DB
            target_id = assist.get("target_id")
            target_name = assist.get("target_name")
            player_name = assist.get("player_name")


        guild_id = message.guild.id
        last_assist = ts_now() - self.assist_spam[guild_id].get(target_id, 0)

        # check for spam
        if last_assist < self.TIME_BETWEEN_ASSISTS:
            msg = await message.channel.send(f"*Assist for Player [{target_id}] already sent {last_assist}s ago (less than {self.TIME_BETWEEN_ASSISTS}s)*")
            await message.delete()
            await asyncio.sleep(10)
            await msg.delete()
            return

        # add assist
        self.assist_spam[guild_id][target_id] = ts_now()

        # get spies from tornstats factionspy
        url = f"https://www.tornstats.com/api.php?key={self.master_key}&action=spy&target={target_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()
        spy = req["spy"] if req.get("spy", {}).get("status") else False


        # create message
        description = []
        if spy:
            description.append("```")
            for s in ["strength", "defense", "speed", "dexterity", "total"]:
                try:
                    description.append(f'{s.title():<9} {spy.get(s):>16,}')
                except BaseException as e:
                    description.append(f'{s}: ???')
            description.append("```")
        else:
            description.append("*No spies found...*\n")
        description.append("**React before joining:**")
        # description.append(f"**Assists required** {n_assists}")
        eb = Embed(title=f"{target_name} [{target_id}]",
                   description="\n".join(description),
                   url=f"https://www.torn.com/loader.php?sid=attack&user2ID={target_id}",
                   color=my_blue)
        eb.set_author(name=f'Assist call from {player_name}', icon_url=message.author.avatar_url)
        # eb.set_footer(text=f'React: 💪 for hits or ☁️ for temp - ☠️ when the fight is over')
        eb.timestamp = now()
        reactions_fields = {
            "React with 💪": "if you can hit",
            "React with ☁️": "if you just temp",
            "React with ☠️": "when the fight is over",
        }
        for k, v in reactions_fields.items():
            eb.add_field(name=f"{k}", value=v)

        # send assist message
        msg = await send(message.channel, "", embed=eb)
        await msg.add_reaction('💪')
        await msg.add_reaction('☁️')
        await msg.add_reaction('☠️')

        # delete origin message
        await message.delete()

        # update origin message with torn API call
        response, e = await self.bot.api_call("user", target_id, ["profile"], self.master_key, comment="ak-assist")
        if e and 'error' in response:
            tmp = await self.bot.send_error_message(msg.channel, f'API error AK-assist: {response["error"]["error"]}', delete=5)
        else:
            eb_d = msg.embeds[0].to_dict()

            # modify title to add name and faction
            f = response.get("faction", {})
            eb_d["title"] = eb_d["title"].replace("Player", response.get("name")) + f' {f.get("position").lower()} of {response.get("faction", {}).get("faction_tag")}'

            # add life and status
            l = response.get("life")
            s = response.get("last_action")
            description = f'**Life** {l.get("current"):,}/{l.get("maximum"):,} **Last action**: {s.get("relative")}'

            # modify description
            eb_d["description"] = f'{description}\n\n{eb_d["description"]}'

            eb = Embed.from_dict(eb_d)
            await msg.edit(embed=eb)

    @tasks.loop(seconds=5)
    async def get_assists(self):
        assists = await get_assists()
        for assist in assists:
            await self.handle_assist(assist=assist)

    @tasks.loop(seconds=10)
    async def clean_assists(self):
        print("clean assists")
        now = ts_now()
        for guild_id, assists in self.assist_spam.items():
            print(guild_id, assists)
            to_del = []
            for target_id, ts in assists.items():
                if now - ts > self.TIME_BETWEEN_ASSISTS:
                    to_del.append(target_id)
            for target_id in to_del:
                print("del", target_id)
                del self.assist_spam[guild_id][target_id]



        assists = await get_assists()
        for assist in assists:
            await self.handle_assist(assist=assist)

    @commands.Cog.listener()
    async def on_message(self, message):

        # tmp access to assists
        if message.guild.id in self.assist_servers and not message.author.bot:
            await self.handle_assist(message=message)
            return

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

                    # check if user have at least one helper role
                    cascading_roles = self.guilds_cascading_roles.get(payload.message_id, {})
                    for role_main_id, role_casc_ids in cascading_roles.items():
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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id in self.assist_servers[payload.guild_id] and not payload.member.bot:
            if payload.emoji.name == '☠️':
                guild = get(self.bot.guilds, id=payload.guild_id)
                channel = get(guild.text_channels, id=payload.channel_id)
                message = await channel.fetch_message(payload.message_id)

                if len(message.embeds):
                    message_title = message.embeds[0].to_dict().get("title")
                    await message.edit(content=f"*Fight against {message_title}: fight's over*", embed=None)
                else:
                    await message.edit(content=message.content.replace("enough joins for now", "fight's over"), embed=None)

                await message.clear_reactions()
                # await asyncio.sleep(1)
                # await message.delete()

            elif payload.emoji.name in ['☁️', '💪']:
                guild = get(self.bot.guilds, id=payload.guild_id)
                channel = get(guild.text_channels, id=payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                message_title = message.embeds[0].to_dict().get("title")

                # enough joins
                if not len(message.embeds):
                    await message.clear_reaction(payload.emoji)
                    return

                # check number of react and edit
                joins_reacts = []
                for reaction in [r for r in message.reactions if r.emoji in ['☁️', '💪']]:
                    for r in await reaction.users().flatten():
                        if r not in joins_reacts:
                            joins_reacts.append(r)
                joins = len(joins_reacts) - 1
                # print(joins)
                # edit message if joins == 4
                if joins > 4:
                    await message.edit(content=f'*Fight against {message_title}: enough joins for now*', embed=None)
                    await message.clear_reaction('☁️')
                    await message.clear_reaction('💪')
                    # await message.add_reaction('☠️')
                else:
                    msg = await channel.send(f'*Fight against {message_title}: {payload.member.display_name} joined ({"hitter" if payload.emoji.name == "💪" else "smoke"})*')
                    await asyncio.sleep(10)
                    await msg.delete()

                # if joins == 4:
                #     await asyncio.sleep(60)
                #     await message.delete()


    @get_assists.before_loop
    async def before_get_assists(self):
        await self.bot.wait_until_ready()

    @clean_assists.before_loop
    async def before_clean_assists(self):
        await self.bot.wait_until_ready()

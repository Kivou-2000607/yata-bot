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

# import discord modules
from discord.ext import commands


class Marvin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = self.bot.bot_id

        self.quotes = [
            "Life? Don't talk to me about life.",
            "I think you ought to know I'm feeling very depressed.",
            "Pardon me for breathing, which I never do anyway so I don't know why I bother to say it, Oh God, I'm so depressed.",
            "I won't enjoy it.",
            "You think you've got problems? What are you supposed to do if you are a manically depressed robot? No, don't try to answer that. I'm fifty thousand times more intelligent than you and even I don't know the answer. It gives me a headache just trying to think down to your level.",
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
            "*Now the world has gone to bed,*\n*arkness won't engulf my head,*\n*I can see by infra-red,*\n*How I hate the night,*\n*Now I lay me down to sleep,*\n*Try to count electric sheep,*\n*Sweet dream wishes you can keep,*\n*How I hate the night.*"]

    @commands.Cog.listener()
    async def on_message(self, message):

        # return if bot
        if message.author.bot:
            return

        # if it's pinged
        splt = message.content.split()
        if '<@!708796850978684968>' in splt:
            await message.channel.send("*sigh*")

        # in #yata-bot-setup
        if message.channel.id in [703587583862505483]:
            splt = message.content.split(" ")
            if "<@&679669933680230430>" in splt:
                lst = [f"Hello {message.author.mention}, if you asked for a bt setup you're in the good place, otherwise checkout <#623906124428476427>.",
                       f"Please wait just a moment for an @Helper to help you out.",
                       f"In the meantime you can check that you're verified and logged into YATA, make sure you gave us the server name and do an initial `!sync` on your server.",
                       f"Or just read the documentation on the website if what I just said doesn't make any sense to you.",
                       "",
                       "Here I am, brain the size of a planet, and they use me as a messenger. Call that job satisfaction, 'cause I don't."]
                await message.channel.send("\n".join(lst))
            return

            return

        speak = random.random() > 0.5 if "<@&679669933680230430>" in splt else random.random() > 0.9
        if speak:
            await message.channel.send(random.choice(self.quotes))
            return

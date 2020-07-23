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

    @commands.Cog.listener()
    async def on_message(self, message):

        # return if bot
        if message.author.bot:
            return

        # if it's pinged
        splt = message.content.split()
        if '<@!708796850978684968>' in splt or '<@708796850978684968>' in splt:
            await message.channel.send("*sigh*")

        # in #yata-bot-setup
        if message.channel.id in [703587583862505483] and 679669933680230430 not in message.author.roles:
            splt = message.content.split(" ")
            if "<@&679669933680230430>" in splt:
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

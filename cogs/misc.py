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
import xkcd
import asyncio
import aiohttp
import random
import logging
import urllib

# import discord modules
from discord.ext import commands
from discord import Embed

# import bot functions and classes
from inc.handy import *


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # snake emoji variables
        self.snake_e_u = "⬆️"
        self.snake_e_d = "⬇️"
        self.snake_e_l = "⬅️"
        self.snake_e_r = "➡️"

        # snake current games
        self.snakes = {}

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def xkcd(self, ctx, *args):
        """gives random xkcd comic"""
        if len(args) and args[0].isdigit():
            comic = xkcd.Comic(args[0])
            id = args[0]
        else:
            comic = xkcd.getRandomComic()
            id = comic.getExplanation().split("/")[-1]

        eb = Embed(description=f'[{comic.getTitle()} #{id}]({comic.getExplanation()})', color=my_blue)
        eb.set_image(url=comic.getImageLink())
        eb.set_footer(text=comic.getAltText())
        await ctx.send(embed=eb)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def crimes2(self, ctx):
        """gives latest update on crimes 2.0"""
        await ctx.send("https://yata.yt/media/misc/crimes2.gif")

    @commands.command(aliases=["ub"])
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def urban_dictionary(self, ctx, *args):
        """urban dictionary"""
        search = urllib.parse.quote(" ".join(args))
        await ctx.send(f'https://www.urbandictionary.com/define.php?term={search}')


    # @commands.command(aliases=["s"])
    # @commands.bot_has_permissions(send_messages=True)
    # @commands.guild_only()
    # async def snake(self, ctx):
    #     """play snake"""
    #
    #     # game setup
    #     size_x = 9
    #     size_y = 11
    #
    #     # screen
    #     s_u = ":arrow_up_small:"
    #     s_d = ":arrow_down_small:"
    #     s_r = ":arrow_forward:"
    #     s_l = ":arrow_backward:"
    #
    #     # helper function to pass from cartesian to lexicographical notations
    #     def c2l(x, y):
    #         return y * size_x + x
    #
    #     # helper function to pass from lexicographical to cartesian notations
    #     def l2c(n):
    #         return (n % size_x, n // size_x)
    #
    #     # randomly pick a free space
    #     def spawn_apple(snake):
    #         free = [_ for _ in range(size_x * size_y) if _ not in snake["body"] + snake["apples"]]
    #         snake["apples"].append(random.choice(free))
    #         return snake
    #
    #     # display screen
    #     def screen(snake):
    #
    #         # check if lost
    #         if snake["lost"]:
    #             screen = f'**Score** {len(snake["body"])}\n'
    #             for i in range(size_x * size_y):
    #                 if i == snake["body"][-1]:
    #                     screen += ":x:"
    #                 elif i in snake["body"]:
    #                     screen += ":o:"
    #                 elif i in snake["apples"]:
    #                     screen += ":green_square:"
    #                 else:
    #                     screen += ":wavy_dash:"
    #
    #                 if not (i + 1) % size_x:
    #                     screen += "\n"
    #
    #             return screen
    #
    #         screen = f'**Score** {len(snake["body"])} '
    #         screen += f'**Position** {l2c(snake["body"][-1])} '
    #         screen += f'**Speed** {snake["speed"]}/4\n'
    #         for i in range(size_x * size_y):
    #             if i == snake["body"][-1]:
    #                 screen += snake["direction"]
    #             elif i in snake["body"]:
    #                 screen += ":blue_square:"
    #             elif i in snake["apples"]:
    #                 screen += ":green_square:"
    #             else:
    #                 screen += ":wavy_dash:"
    #
    #             if not (i + 1) % size_x:
    #                 screen += "\n"
    #
    #         return screen
    #
    #     def move(snake, direction=None):
    #
    #         # set same direction as current
    #         if direction is None:
    #             direction = snake["direction"]
    #
    #         # ignore invalid move
    #         if sorted([snake["direction"], direction]) in [sorted([s_d, s_u]), sorted([s_r, s_l])]:
    #             return snake
    #
    #         # record direction
    #         snake["direction"] = direction
    #
    #         # add head
    #         x, y = l2c(snake["body"][-1])
    #         if direction == s_r:
    #             x += 1
    #         elif direction == s_l:
    #             x -= 1
    #         elif direction == s_d:
    #             y += 1
    #         elif direction == s_u:
    #             y -= 1
    #
    #         # check if wall
    #         if x == size_x or x == -1 or y == size_y or y == -1:
    #             snake["lost"] = True
    #             return snake
    #
    #         # lexico head
    #         head = c2l(x, y)
    #
    #         # hit itself
    #         if head in snake["body"]:
    #             snake["lost"] = True
    #             return snake
    #
    #
    #         # check if apple
    #         if head in snake["apples"]:
    #             snake["apples"].remove(head)
    #             snake = spawn_apple(snake)
    #         else:
    #             snake["body"].pop(0)
    #
    #         snake["body"].append(head)
    #
    #         return snake
    #
    #     # variables
    #     snake = { "body": [c2l(size_x // 2 - 1, size_y // 2), c2l(size_x // 2, size_y // 2)],
    #               "direction": s_r, "lost": False, "apples": [c2l(size_x // 2 + 2, size_y // 2)],
    #               "speed": 1 }
    #
    #     message = await ctx.send(screen(snake))
    #     await message.add_reaction(self.snake_e_l)
    #     await message.add_reaction(self.snake_e_u)
    #     await message.add_reaction(self.snake_e_d)
    #     await message.add_reaction(self.snake_e_r)
    #     self.snakes[message.id] = snake
    #
    #     while True:
    #         snake = self.snakes[message.id]
    #         snake = move(snake)
    #         await message.edit(content=screen(snake))
    #
    #         if snake["lost"]:
    #             await message.clear_reactions()
    #             return
    #
    #         if len(snake["body"]) > 15:
    #             snake["speed"] = 4
    #         elif len(snake["body"]) > 9:
    #             snake["speed"] = 3
    #         elif len(snake["body"]) > 4:
    #             snake["speed"] = 2
    #         else:
    #             snake["speed"] = 1
    #
    #         await asyncio.sleep(2.5 - 0.5*snake["speed"])
    #
    #
    # @commands.Cog.listener()
    # async def on_reaction_add(self, reaction, discord_user):
    #     if discord_user.bot:
    #         return
    #
    #     s_u = ":arrow_up_small:"
    #     s_d = ":arrow_down_small:"
    #     s_r = ":arrow_forward:"
    #     s_l = ":arrow_backward:"
    #
    #     if reaction.message.id in self.snakes:
    #         snake = self.snakes[reaction.message.id]
    #         if f"{reaction}" == self.snake_e_u:
    #             snake["direction"] = s_u
    #         elif f"{reaction}" == self.snake_e_d:
    #             snake["direction"] = s_d
    #         elif f"{reaction}" == self.snake_e_l:
    #             snake["direction"] = s_l
    #         elif f"{reaction}" == self.snake_e_r:
    #             snake["direction"] = s_r
    #
    #         await reaction.message.remove_reaction(reaction, discord_user)

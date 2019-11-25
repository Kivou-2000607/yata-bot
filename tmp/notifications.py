# # import standard modules
import time
import psycopg2
import asyncio
# import aiohttp
#
# # import discord modules
from discord.ext import tasks, commands
# from discord.utils import get
# from discord import Embed
#
# # import bot functions and classes
# import includes.checks as checks
# import includes.verify as verify


class Notifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.index = 0

        # start loop
        self.notify.start()

    # cancel the task on cog unload
    def cog_unload(self):
        self.notify.cancel()

    async def sendNotifications():
        print("coucou")

    @tasks.loop(seconds=1.0, count=1)
    async def notify(self):
        print("prout")
        
    async def on_ready(self):

        futures = [sendNotifications(), sendNotifications()]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(futures))
        loop.close()

        # discordIds = [1, 2]
        # asyncIt = asyncio.gather(discordIds)
        # print(asyncIt)
        #
        # print("One")
        # await asyncio.sleep(1)
        # print("Two")

        # dbCredentials = {'database': 'a', 'user': 'a', 'password': 'a', 'host': 'a', 'port': 'a'}
        # connect = psycopg2.connect(**dbCredentials)
        # print(connect)

        # async for i in discordIds:
        #     print(i)
        #     await time.sleep(2)

        #
        #
        #
        # if user is None:
        #     p.yataServer = False
        # else:
        #     p.yataServer = True
        #     p.yataServerName = user.name
        #
        # p.save()
        # print(p, p.yataServer, p.yataServerName)
        #
        # if p.hasNotifications() and p.yataServer:
        #     if user is None:
        #         print("\tuser not found")
        #     else:
        #         messages = p.sendNotifications()
        #         if messages:
        #             for message in messages:
        #                 print("\tnotification set: {}".format(message))
        #                 await user.send(message)
        #         else:
        #             print("\tno notification to send")
        #
        # else:
        #     print("\tno notifications on")
        #
        #
        # print(self.index)
        # self.index += 1

    # wait that the bot is up before starting the loop
    # @notify.before_loop
    # async def before_printer(self):
    #     await self.bot.wait_until_ready()

# import standard modules
import asyncio
import websockets
import cloudscraper
import json
import os

# import discord modules
from discord.ext import commands
from discord.ext import tasks
from discord.utils import get


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.secret = os.environ.get("secret")
        self.chat.start()

    def cog_unload(self):
        self.chat.cancel()

    @commands.command()
    async def talk(self, ctx, *args):
        """For Nub Navy Server only"""
        if ctx.author.id != 227470975317311488:
            await ctx.send(":x: This command is not for you")
            return

        guild = get(self.bot.guilds, id=432226682506575893)
        channel = get(guild.channels, name="chat-nn")

        await channel.send(" ".join(args))

    @tasks.loop(seconds=600)
    async def chat(self):
        """For Nub Navy Server only"""
        guild = get(self.bot.guilds, id=432226682506575893)
        channel = get(guild.channels, name="chat-nn")

        # thanks Pyrit [2111649] for the help
        token, agent = cloudscraper.get_cookie_string("https://www.torn.com")
        headers = {"User-Agent": agent, "Cookie": token}
        uri = f"wss://ws-chat.torn.com/chat/ws?uid=2000607&secret={self.secret}"
        print('[CHAT] connecting...')

        async with websockets.connect(uri, origin="https://www.torn.com", extra_headers=headers) as websocket:
            print('[CHAT] connected')
            while(True):
                data = await websocket.recv()
                d = json.loads(data).get("data", [dict({})])[0]
                if d.get("roomId", "") == "Faction:33241" and d.get("messageText"):
                    msg = f'`{d.get("senderName")} [{d.get("senderId")}]: {d.get("messageText")}`'
                    await channel.send(msg)

    @chat.before_loop
    async def before_notify(self):
        print('[CHAT] waiting...')
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)

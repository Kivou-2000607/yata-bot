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

from discord import Webhook, AsyncWebhookAdapter

import re
import asyncio
import websockets
import cloudscraper
import aiohttp
import json

from includes.yata_db import get_secret
import includes.formating as fmt

room = "Trade"
iud, secret, hooks = get_secret(room)

async def chat(uid, secret, hooks, room):

    uri = f"wss://ws-chat.torn.com/chat/ws?uid={iud}&secret={secret}"

    token, agent = cloudscraper.get_cookie_string("https://www.torn.com")
    headers = {"User-Agent": agent, "Cookie": token}

    async with websockets.connect(uri, origin="https://www.torn.com", extra_headers=headers) as websocket:
        async with aiohttp.ClientSession() as session:
            webhooks = dict({})
            for hookId, hookurl in hooks.items():
                webhooks[hookId] = Webhook.from_url(hookurl, adapter=AsyncWebhookAdapter(session))

            while(True):
                data = await websocket.recv()
                d = json.loads(data).get("data", [dict({})])[0]
                txt = d.get("messageText")
                if d.get("roomId", "") == room and txt:
                    msg = fmt.chat_message(d)
                    await webhooks["full"].send(msg)

                    for keyword in [k for k in webhooks if k != "full"]:
                        if re.search(f"\W*({keyword})\W*", txt.lower()) is not None:
                            await webhooks[keyword].send(msg)

asyncio.get_event_loop().run_until_complete(chat(iud, secret, json.loads(hooks), room))

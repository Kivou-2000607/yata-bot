from discord import Webhook, AsyncWebhookAdapter

import asyncio
import websockets
import cloudscraper
import aiohttp
import json

from includes.yata_db import get_secret

room = "Faction:33241"
iud, secret, hookurl = get_secret(room)


async def chat(uid, secret, hookurl, room):
    print("<chat>")
    print(iud, secret, hookurl)

    uri = f"wss://ws-chat.torn.com/chat/ws?uid={iud}&secret={secret}"

    token, agent = cloudscraper.get_cookie_string("https://www.torn.com")
    headers = {"User-Agent": agent, "Cookie": token}

    async with websockets.connect(uri, origin="https://www.torn.com", extra_headers=headers) as websocket:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(hookurl, adapter=AsyncWebhookAdapter(session))
            while(True):
                data = await websocket.recv()
                d = json.loads(data).get("data", [dict({})])[0]
                if d.get("roomId", "") == room and d.get("messageText"):
                    splitMessage = [w.lower().replace("@", "").replace("!", "") for w in d.get("messageText").split(" ")]
                    msg = f'`{d.get("senderName")} [{d.get("senderId")}]: {d.get("messageText")}`'
                    if "leader" in splitMessage:
                        msg += " <@&546769358744191006>"
                    await webhook.send(msg)
    print("</chat>")

asyncio.get_event_loop().run_until_complete(chat(iud, secret, hookurl, room))

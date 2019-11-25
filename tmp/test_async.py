#!/usr/bin/env python3
# rand.py

import asyncio


async def sendNotifications(i):
    print("coucou", i)
    await asyncio.sleep(2)


futures = [sendNotifications(1), sendNotifications(2)]
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.wait(futures))
loop.close()

# import standard modules
import requests
import json
import asyncio
import re
import os
import psycopg2
import asyncpg

# import discord modules
from discord.utils import get


async def get_member_key(member):
    """ get a member key from YATA database
        return tornId, Name, key
        return -1, None, None: did not parse torn id from display name
        return -2, None, None: did not find torn id in yata db
    """

    # get torn id from name
    match = re.match(r'([a-zA-Z0-9_-]{1,16}) \[(\d{1,7})\]', member.display_name)
    if match is not None:
        tornId = int(member.display_name.split("[")[-1][:-1])
    else:
        return -1, None, None

    # get YATA user
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    user = await con.fetch(f'SELECT "tId", name, key FROM player_player WHERE "tId" = {tornId};')
    await con.close()

    # return id, name, key
    if len(user):
        return tuple(user[0])
    else:
        return -2, None, None

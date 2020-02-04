# import standard modules
import json
import asyncio
import aiohttp
import re
import os
import asyncpg
import psycopg2


# definition of the view linking Player to Key
# Name of the view: player_view_player_key
# SELECT player_key.value,
#    player_player.notifications,
#    player_player."dId",
#    player_player."tId",
#    player_player.name,
#    player_player."botPerm",
#    player_player."activateNotifications"
#   FROM player_key
#     JOIN player_player ON player_key.player_id = player_player.id;

async def get_yata_user(tornId):
    # get YATA user
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    user = await con.fetch(f'SELECT "tId", "name", "value", "botPerm" FROM player_view_player_key WHERE "tId" = {tornId};')
    await con.close()

    return user


async def push_guild_name(guild):
    """Writes the actual guild name in YATA database"""
    # get YATA user
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    await con.execute('UPDATE bot_guild SET "guildName"=$1, "guildOwnerId"=$2, "guildOwnerName"=$3 WHERE "guildId"=$4', guild.name, guild.owner_id, guild.owner.name, guild.id)
    await con.close()


def load_configurations(bot_id):
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    con = psycopg2.connect(**db_cred)
    cur = con.cursor()
    cur.execute(f"SELECT token, variables FROM bot_discordapp WHERE id = {bot_id};")
    token, configs = cur.fetchone()
    cur.close()
    con.close()
    return token, configs


async def push_configurations(bot_id, configs):
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    await con.execute('UPDATE bot_discordapp SET variables = $1 WHERE id = $2', json.dumps(configs), int(bot_id))
    await con.close()


def get_secret(name):
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    con = psycopg2.connect(**db_cred)
    cur = con.cursor()
    cur.execute(f"SELECT uid, secret, hookurl FROM bot_chat WHERE name = '{name}';")
    uid, secret, hookurl = cur.fetchone()
    cur.close()
    con.close()
    return uid, secret, hookurl

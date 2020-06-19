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
import json
import asyncio
import aiohttp
import re
import os
import asyncpg
import psycopg2
from datetime import datetime

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
    user = await con.fetch(f'SELECT "tId", "name", "value" FROM player_view_player_key WHERE "tId" = {tornId};')
    await con.close()

    return user

async def get_yata_user_by_discord(discordID):
    # get YATA user
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    user = await con.fetch(f'SELECT "tId" FROM player_player WHERE "dId" = {discordID};')
    await con.close()

    return user


async def push_guild_info(guild, member, contact, bot_pk):
    """Writes the actual guild name in YATA database"""
    # get YATA user
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    await con.execute('UPDATE bot_guild SET "guildName"=$1, "guildOwnerId"=$2, "guildOwnerName"=$3, "guildJoinedTime"=$4, "guildContactDiscordName"=$5, "guildContactDiscordId"=$6 WHERE "guildId"=$7 AND "configuration_id"=$8', guild.name, guild.owner_id, guild.owner.name, datetime.timestamp(member.joined_at), contact.name, contact.id, guild.id, int(bot_pk))
    await con.close()


def load_configurations(bot_id, verbose=False):
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    con = psycopg2.connect(**db_cred)
    cur = con.cursor()
    cur.execute(f"SELECT token, variables, administrators FROM bot_discordapp WHERE id = {bot_id};")
    token, configs, administrators = cur.fetchone()
    cur.close()
    con.close()
    return token, configs, administrators


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


async def push_rackets(timestamp, rackets):
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    await con.execute('UPDATE bot_rackets SET timestamp = $1, rackets = $2 WHERE id = 1', timestamp, json.dumps(rackets))
    await con.close()


def get_rackets():
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    con = psycopg2.connect(**db_cred)
    cur = con.cursor()
    cur.execute(f"SELECT timestamp, rackets FROM bot_rackets WHERE id = 1;")
    timestamp, rackets = cur.fetchone()
    cur.close()
    con.close()
    return timestamp, json.loads(rackets)


async def get_faction_name(tId):
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    row = await con.fetchrow('SELECT name FROM faction_faction WHERE "tId" = $1', tId)
    await con.close()
    return f'Faction [{tId}]' if row is None else f'{row.get("name", "Faction")} [{tId}]'


async def reset_notifications(tornId):
    """Writes the actual guild name in YATA database"""

    # get YATA user
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    await con.execute('UPDATE player_player SET "activateNotifications"=$1, "notifications"=$2 WHERE "tId"=$3', False, json.dumps({}), tornId)
    await con.close()

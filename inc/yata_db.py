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
import sys
import json
import asyncio
import aiohttp
import re
import os
import asyncpg
import psycopg2
import logging
import html
import string
import random
import time
from datetime import datetime
# change folder for .env file if
if len(sys.argv) > 1:
    from decouple import AutoConfig
    print(os.path.join(os.getcwd(), sys.argv[1]))
    config = AutoConfig(search_path=os.path.join(os.getcwd(), sys.argv[1]))
else:
    from decouple import config

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

# def get_credentials():
#     db_credentials = {
#         "dbname": config("DB_NAME"),
#         "user": config("DB_USER"),
#         "password": config("DB_PASSWORD"),
#         "host": config("DB_HOST"),
#         "port": config("DB_PORT")
#     }
#
#     return db_credentials


def load_configurations(bot_id, database):
    db_cred = {
        "dbname": database.get("database"),
        "user": database.get("user"),
        "password": database.get("password"),
        "host": database.get("host"),
        "port": database.get("port")
    }
    con = psycopg2.connect(**db_cred)

    # get bot
    cur = con.cursor()
    cur.execute(f"SELECT token, name FROM bot_bot WHERE id = {bot_id};")
    token, name = cur.fetchone()
    cur.close()

    # get servers configuration linked with the bot
    cur = con.cursor()
    cur.execute(f"SELECT id, discord_id, name, configuration FROM bot_server WHERE bot_server.bot_id = {bot_id};")
    configurations_raw = cur.fetchall()
    cur.close()

    # format configrations to a dict
    configurations = dict({})
    for id, discord_id, name, configuration in configurations_raw:
        configurations[discord_id] = json.loads(configuration)

    con.close()
    return token, configurations


def get_stocks_history(database):
    print("get stocks history")
    db_cred = {
        "dbname": database.get("database"),
        "user": database.get("user"),
        "password": database.get("password"),
        "host": database.get("host"),
        "port": database.get("port")
    }
    con = psycopg2.connect(**db_cred)


    # get bot
    cur = con.cursor()
    cur.execute(f'SELECT stock_id, timestamp, current_price, market_cap, total_shares FROM stocks_history WHERE timestamp >= {int(time.time()) - 3600 * 24};')
    rows = cur.fetchall()
    cur.close()

    stocks_history = {}

    for r in rows:
        stock_id = str(r[0]) if r[0] <= 23 else str(r[0] + 1)
        stock_id = "24" if r[0] == 32 else stock_id
        if stock_id not in stocks_history:
            stocks_history[stock_id] = []
        stocks_history[stock_id].append(
            {
                "timestamp": r[1],
                "current_price": r[2],
                "market_cap": r[3],
                "total_shares": r[4]
            }
        )

    print("get stocks history -> done")
    con.close()
    return stocks_history


# async def get_configuration(bot_id, discord_id):
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     server = await con.fetchrow(f'SELECT configuration FROM bot_server WHERE bot_id = {bot_id} AND discord_id = {discord_id};')
#     return False if server is None else json.loads(server.get("configuration"))

# async def set_n_servers(bot_id, n):
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#
#     await con.execute('''
#         UPDATE bot_bot SET number_of_servers = $2 WHERE id = $1
#         ''', bot_id, n)
#     await con.close()


# async def set_configuration(bot_id, discord_id, server_name, configuration):
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#
#     # check if server already in the database
#     server = await con.fetchrow(f'SELECT * FROM bot_server WHERE bot_id = {bot_id} AND discord_id = {discord_id};')
#     if server is None:  # create if not in the db
#         # logging.debug(f"[yata_db/set_configuration] Create db configuration {server_name}: {configuration}")
#         await con.execute('''
#         INSERT INTO bot_server(bot_id, discord_id, name, configuration, secret) VALUES($1, $2, $3, $4, $5)
#         ''', bot_id, discord_id, server_name, json.dumps(configuration), 'x')
#     else:  # update otherwise
#         # logging.debug(f"[yata_db/set_configuration] Update db configuration {server_name}: {configuration}")
#         await con.execute('''
#         UPDATE bot_server SET name = $3, configuration = $4 WHERE bot_id = $1 AND discord_id = $2
#         ''', bot_id, discord_id, server_name, json.dumps(configuration))
#     await con.close()


# async def delete_configuration(bot_id, discord_id):
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#
#     # check if server already in the database
#     server = await con.fetchrow(f'SELECT * FROM bot_server WHERE bot_id = {bot_id} AND discord_id = {discord_id};')
#     if server is not None:  # delete if in the db
#         # step 1 remove the admins
#         tmp = await con.fetch(f'SELECT * FROM bot_server_server_admin WHERE server_id = {server.get("id")};')
#         await con.execute(f'DELETE FROM bot_server_server_admin WHERE server_id = $1', server.get("id"))
#
#         # step 2 delete the configuration
#         await con.execute(f'DELETE FROM bot_server WHERE bot_id = $1 AND discord_id = $2', bot_id, discord_id)
#
#     await con.close()


# async def get_server_admins(bot_id, discord_id):
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     server = await con.fetchrow(f'SELECT * FROM bot_server WHERE bot_id = {bot_id} AND discord_id = {discord_id};')
#     if server is None:
#         return {}, 'x'
#
#     server_yata_id = server.get("id")
#     players_yata_id = await con.fetch(f'SELECT player_id FROM bot_server_server_admin WHERE server_id = {server_yata_id};')
#
#     admins = {}
#     for player_yata_id in [player.get("player_id") for player in players_yata_id]:
#         player = await con.fetchrow(f'SELECT "tId", "dId", "name" FROM player_player WHERE "id" = {player_yata_id};')
#         dId = player.get("dId", 0)
#         if dId:
#             admins[str(dId)] = {"name": player.get("name", "?"), "torn_id": player.get("tId")}
#
#     secret = json.loads(server.get("configuration", '{}')).get("admin", {}).get("secret", 'x')
#     if secret == 'x':
#         secret = ''.join(random.choice(string.ascii_lowercase) for i in range(16))
#
#     return admins, secret


# async def get_yata_user(user_id, type="T"):
#     # get YATA user
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     if type == "T":
#         user = await con.fetch(f'SELECT "tId", "name", "value" FROM player_view_player_key WHERE "tId" = {user_id};')
#     elif type == "D":
#         user = await con.fetch(f'SELECT "tId", "name", "value" FROM player_view_player_key WHERE "dId" = {user_id};')
#     await con.close()
#
#     return user


def get_secret(name):
    db_cred = get_credentials()
    con = psycopg2.connect(**db_cred)
    cur = con.cursor()
    cur.execute(f"SELECT uid, secret, hookurl FROM bot_chat WHERE name = '{name}';")
    uid, secret, hookurl = cur.fetchone()
    cur.close()
    con.close()
    return uid, secret, hookurl


# async def push_data(bot_id, timestamp, data, module):
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     if module == "rackets":
#         await con.execute('UPDATE bot_rackets SET timestamp = $1, rackets = $2 WHERE id = $3', timestamp, json.dumps(data), bot_id)
#     elif module == "stocks":
#         await con.execute('UPDATE bot_stocks SET timestamp = $1, rackets = $2 WHERE id = $3', timestamp, json.dumps(data), bot_id)
#     elif module == "wars":
#         await con.execute('UPDATE bot_wars SET timestamp = $1, wars = $2 WHERE id = $3', timestamp, json.dumps(data), bot_id)
#     await con.close()


# def get_data(bot_id, module):
#     db_cred = get_credentials()
#     con = psycopg2.connect(**db_cred)
#     cur = con.cursor()
#     if module == "rackets":
#         cur.execute(f"SELECT timestamp, rackets FROM bot_rackets WHERE id = {bot_id};")
#     elif module == "stocks":
#         cur.execute(f"SELECT timestamp, rackets FROM bot_stocks WHERE id = {bot_id};")
#     elif module == "wars":
#         cur.execute(f"SELECT timestamp, wars FROM bot_wars WHERE id = {bot_id};")
#
#     timestamp, data = cur.fetchone()
#     cur.close()
#     con.close()
#     return timestamp, json.loads(data)


# async def get_faction_name(tId):
#     if str(tId).isdigit():
#         tId = int(tId)
#         db_cred = get_credentials()
#         dbname = db_cred["dbname"]
#         del db_cred["dbname"]
#         con = await asyncpg.connect(database=dbname, **db_cred)
#         row = await con.fetchrow('SELECT name FROM faction_faction WHERE "tId" = $1', tId)
#         await con.close()
#         return f'Faction [{tId}]' if row is None else f'{html.unescape(row.get("name", "Faction"))} [{tId}]'
#     else:
#         return f'Faction [{tId}]'


# async def reset_notifications(tornId):
#     # get YATA user
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     await con.execute('UPDATE player_player SET "activateNotifications"=$1, "notifications"=$2 WHERE "tId"=$3', False, json.dumps({}), tornId)
#     await con.close()


# async def get_loots():
#     # get YATA npcs loot timings
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     loots = await con.fetch(f'SELECT * FROM loot_NPC WHERE show = true;')
#     await con.close()
#
#     return loots
#
#
# async def get_scheduled():
#     # get YATA npcs loot timings
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     loots = await con.fetch(f'SELECT * FROM loot_scheduledAttack;')
#     await con.close()
#
#     return loots
#
#
# async def get_npc(id):
#     # get YATA npcs loot timings
#     db_cred = get_credentials()
#     dbname = db_cred["dbname"]
#     del db_cred["dbname"]
#     con = await asyncpg.connect(database=dbname, **db_cred)
#     npc = await con.fetch(f'SELECT * FROM loot_NPC WHERE "id"=$1;', id)
#     await con.close()
#
#     return npc

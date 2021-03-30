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
import os
import sys
import json
import psycopg2
import logging
import logging.config
import time
import sys
import discord
# change folder for .env file if
if len(sys.argv) > 1:
    from decouple import AutoConfig
    print(os.path.join(os.getcwd(), sys.argv[1]))
    config = AutoConfig(search_path=os.path.join(os.getcwd(), sys.argv[1]))
else:
    from decouple import config

# import bot
from bots.yata import YataBot

# import cogs
from cogs.verify import Verify
from cogs.loot import Loot
from cogs.stocks import Stocks
from cogs.api import API
from cogs.chain import Chain
from cogs.racket import Racket
from cogs.war import War
from cogs.admin import Admin
from cogs.revive import Revive
from cogs.misc import Misc
from cogs.crimes import Crimes
from cogs.repository import Repository
from cogs.marvin import Marvin

# import includes
from inc.yata_db import load_configurations

# configure intents
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True

# logging
logging.config.fileConfig('logging.conf')
logging.Formatter.converter = time.gmtime
logging.debug("debug")
logging.info("info")
logging.warning("warning")
logging.error("error")

# get basic config
bot_id = config("BOT_ID", default=1)
github_token = config("GITHUB_TOKEN", default="")
main_server_id = config("MAIN_SERVER_ID", default=581227228537421825)
master_key = config("MASTER_KEY", default="")
logging.info(f'Starting bot: bot id = {bot_id}')

# databse
database = {
    "host": config("DB_HOST", cast=str),
    "database": config("DB_DATABASE", cast=str),
    "user": config("DB_USER", cast=str),
    "password": config("DB_PASSWORD", cast=str),
    "port": config("DB_PORT", cast=int),
    "min_size": config("DB_MIN_SIZE", cast=int, default=1),
    "max_size": config("DB_MAX_SIZE", cast=int, default=5)
}

# sentry
if config("ENABLE_SENTRY", default=False, cast=bool):
    logging.info(f'Sentry: enabled')
    import sentry_sdk
    sentry_sdk.init(
        dsn=config("SENTRY_DSN"),
        traces_sample_rate=config("SENTRY_SAMPLE_RATE", default=1.0, cast=float),
        environment=config("SENTRY_ENVIRONMENT"),
    )
else:
    logging.info(f'Sentry: disabled')

# get configurations from YATA's database
token, configurations = load_configurations(bot_id, database)

def get_prefix(client, message):
    if message.guild:
        prefix = client.configurations.get(message.guild.id, {}).get("admin", {}).get("prefix", "!")
        return prefix
    else:
        return "!"


# init yata bot
bot = YataBot(configurations=configurations,
              command_prefix=get_prefix,
              bot_id=bot_id,
              main_server_id=main_server_id,
              github_token=github_token,
              master_key=master_key,
              database=database,
              intents=intents)
bot.remove_command('help')

# load classes
bot.add_cog(Admin(bot))

# bot ids:
# 1: Chappie (dev bot)
# 2: Marvin (YATA server administrator)
# 3: YATA (the public bot)
# 4: Nub Boat (duplicate WSSB stock for Nub Navy server)
# 5: YATA backup (the backup version of the public bot)

if int(bot_id) in [1, 3, 5]:
    bot.add_cog(Verify(bot))
    bot.add_cog(Loot(bot))
    bot.add_cog(Stocks(bot))
    bot.add_cog(Racket(bot))
    bot.add_cog(War(bot))
    bot.add_cog(Revive(bot))
    bot.add_cog(Crimes(bot))
    bot.add_cog(API(bot))
    bot.add_cog(Chain(bot))
    bot.add_cog(Misc(bot))
    bot.add_cog(Repository(bot))
    bot.add_cog(Marvin(bot))

elif int(bot_id) in [2]:
    bot.add_cog(Marvin(bot))

elif int(bot_id) in [4]:
    bot.add_cog(Stocks(bot))

# run bot
bot.run(token)

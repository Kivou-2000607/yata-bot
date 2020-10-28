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
import json
import psycopg2
import logging
import logging.config
import time
import sys
import discord

# import bot
from bots.yata import YataBot

# import cogs
from cogs.verify import Verify
from cogs.loot import Loot
from cogs.stocks import Stocks
from cogs.api import API
from cogs.chain import Chain
from cogs.racket import Racket
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
bot_id = os.environ.get("YATA_ID", 1)
github_token = os.environ.get("GITHUB_TOKEN", "")
main_server_id = os.environ.get("MAIN_SERVER_ID", 581227228537421825)
logging.info(f'Starting bot: bot id = {bot_id}')

# get configurations from YATA's database
token, configurations = load_configurations(bot_id)


def get_prefix(client, message):
    if message.guild:
        prefix = client.configurations.get(message.guild.id, {}).get("admin", {}).get("prefix", "!")
        # logging.debug(f'[get_prefix] {message.guild}: {prefix}')
        return prefix
    else:
        return "!"


# init yata bot
bot = YataBot(configurations=configurations,
              command_prefix=get_prefix,
              bot_id=bot_id,
              main_server_id=main_server_id,
              github_token=github_token,
              intents=intents)
bot.remove_command('help')

# load classes
bot.add_cog(Admin(bot))

if int(bot_id) in [1, 3]:
    bot.add_cog(Verify(bot))
    bot.add_cog(Loot(bot))
    bot.add_cog(Stocks(bot))
    bot.add_cog(Racket(bot))
    bot.add_cog(Revive(bot))
    bot.add_cog(Crimes(bot))
    bot.add_cog(API(bot))
    bot.add_cog(Chain(bot))
    bot.add_cog(Misc(bot))
    bot.add_cog(Repository(bot))

elif int(bot_id) in [2]:
    bot.add_cog(Marvin(bot))

elif int(bot_id) in [4]:
    bot.add_cog(Stocks(bot))

# run bot
bot.run(token)

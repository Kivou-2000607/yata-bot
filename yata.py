# import standard modules
import os
import json
import psycopg2

# import bot
from bots.yata import YataBot

# import cogs
from cogs.verify import Verify
from cogs.loot import Loot
from cogs.stocks import Stocks
from cogs.api import API
from cogs.chain import Chain
from cogs.admin import Admin
from cogs.revive import Revive
from cogs.chat import Chat

# import includes
from includes.yata_db import load_configurations

# get basic config
bot_id = os.environ.get("YATA_ID", 1)
prefix = os.environ.get("BOT_PREFIX", "!")

# get configurations from YATA's database
token, configs = load_configurations(bot_id)

# init yata bot
bot = YataBot(configs=json.loads(configs), command_prefix=prefix, bot_id=bot_id)

# load classes
bot.add_cog(Verify(bot))
bot.add_cog(Loot(bot))
bot.add_cog(Stocks(bot))
bot.add_cog(API(bot))
bot.add_cog(Chain(bot))
bot.add_cog(Admin(bot))
bot.add_cog(Revive(bot))
bot.add_cog(Chat(bot))

# run bot
bot.run(token)

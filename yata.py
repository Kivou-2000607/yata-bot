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
from cogs.misc import Misc
from cogs.repository import Repository
from cogs.invite import Invite

# get basic config
bot_id = os.environ.get("YATA_ID", 1)
prefix = os.environ.get("BOT_PREFIX", "!")

# get configurations from YATA's database
if os.environ.get("DB_CREDENTIALS", False):
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    con = psycopg2.connect(**db_cred)
    cur = con.cursor()
    cur.execute(f"SELECT * FROM bot_discordapp WHERE id = {bot_id};")
    _, token, configs, _ = cur.fetchone()
    cur.close()
    con.close()

# get custom configs (skipping YATA databse configurations)
else:
    configs = os.environ.get("YATA_CONFIGS")
    token = os.environ.get("BOT_TOKEN")

# init yata bot
bot = YataBot(configs=json.loads(configs), command_prefix=prefix)

# load classes
bot.add_cog(Verify(bot))
bot.add_cog(Loot(bot))
bot.add_cog(Stocks(bot))
bot.add_cog(Misc(bot))
bot.add_cog(Repository(bot))
bot.add_cog(Invite(bot))

# run bot
bot.run(token)

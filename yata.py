# import standard modules
import os
import json
import psycopg2

# import bot
from bots.yata import YataBot

# import cogs
from cogs.verify import Verify
from cogs.loot import Loot
from cogs.github import Github
from cogs.misc import Misc

# get configurations from YATA's database
db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
con = psycopg2.connect(**db_cred)
cur = con.cursor()
cur.execute("SELECT * FROM bot_configuration WHERE id = 1;")
_, token, configs = cur.fetchone()
cur.close()
con.close()

# init yata bot
bot = YataBot(configs=json.loads(configs), command_prefix="!")

# load classes
bot.add_cog(Verify(bot))
bot.add_cog(Loot(bot))
# bot.add_cog(Github(bot))
bot.add_cog(Misc(bot))

# run bot
bot.run(token)

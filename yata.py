# import standard modules
import os

# import bot
from bots.yata import YataBot

# import cogs
from cogs.verify import Verify
from cogs.loot import Loot
from cogs.github import Github
from cogs.misc import Misc

# init yata bot
bot = YataBot(command_prefix=os.environ.get("BOT_PREFIX", "!"))

# load classes
if 'verify' in bot.MODULES:
    bot.add_cog(Verify(bot))
if 'loot' in bot.MODULES:
    bot.add_cog(Loot(bot))
if 'github' in bot.MODULES:
    bot.add_cog(Github(bot))
if 'misc' in bot.MODULES:
    bot.add_cog(Misc(bot))

# run bot
bot.run(bot.BOT_TOKEN)

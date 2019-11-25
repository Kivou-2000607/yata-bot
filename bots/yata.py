# import standard modules
import json
import os

# import discord modules
import discord
from discord.ext.commands import Bot
from discord.utils import get


# Child class of Bot with extra configuration variables
class YataBot(Bot):
    def __init__(self, **args):
        Bot.__init__(self, **args)
        self.BOT_TOKEN = os.environ.get("BOT_TOKEN")
        self.DATABASE_URL = os.environ.get("DATABASE_URL")
        self.API_KEY = os.environ.get("API_KEY")
        self.WATCHING = os.environ.get("WATCHING")
        self.MODULES = json.loads(os.environ.get("MODULES", "[]"))
        self.GUILD_ID = int(os.environ.get("GUILD_ID"))
        self.FACTIONS = json.loads(os.environ.get("FACTIONS", "{}"))
        self.FORCE_VERIF = bool(os.environ.get("FORCE_VERIF", False))
        print(f"Init YataBot: BOT_TOKEN = {self.BOT_TOKEN}")
        print(f"Init YataBot: API_KEY = {self.API_KEY}")
        print(f"Init YataBot: FORCE_VERIF = {self.FORCE_VERIF}")
        print(f"Init YataBot: DATABASE_URL = {self.DATABASE_URL}")
        print(f"Init YataBot: WATCHING = {self.WATCHING}")
        print("Init YataBot: MODULES = {}".format(", ".join(self.MODULES)))
        print(f"Init YataBot: GUILD_ID = {self.GUILD_ID}")
        print("Init YataBot: FACTIONS = {}".format(", ".join([f"{v} [{k}]" for k, v in self.FACTIONS.items()])))
        print("---")

    async def on_ready(self):

        # create faction roles
        if len(self.FACTIONS):
            guild = self.get_guild(self.GUILD_ID)
            for k, v in self.FACTIONS.items():
                role_name = f"{v} [{k}]"
                if get(guild.roles, name=role_name) is None:
                    print(f"Create role {role_name}")
                    await guild.create_role(name=role_name)

        # change activity
        if self.WATCHING is not None:
            activity = discord.Activity(name=self.WATCHING, type=discord.ActivityType.watching)
            await self.change_presence(activity=activity)
            print(f'YataBot ready to "watch {activity.name}" as {self.user.name} [{self.user.id}]')
        else:
            print(f'YataBot ready as {self.user.name} [{self.user.id}]')
        print("---")

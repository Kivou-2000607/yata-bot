# import standard modules
import json
import os

# import discord modules
import discord
from discord.ext.commands import Bot
from discord.utils import get


# Child class of Bot with extra configuration variables
class YataBot(Bot):
    def __init__(self, configs=None, **args):
        Bot.__init__(self, **args)
        self.configs = configs

    def get_config(self, guild):
        """ get_config: helper function
            gets configuration for a guild
        """
        return self.configs.get(str(guild.id), dict({}))

    def key(self, guild):
        """ key: helper function
            gets a random torn API key for a guild
        """
        import random

        # get configuration for the guild
        config = self.get_config(guild)

        # get all keys
        keys = config.get("keys", False)

        if keys:
            # select a random key
            return random.choice(keys)
        else:
            return False

    async def on_ready(self):
        """ on_ready
            loop over the bot guilds and do:
                - get guild config
                - create faction roles necessary
                - create Verified role
                TODO:
                - create default channels (#readme, #verify-id, #dev-bot)
                - send I'm back up message
                - change #dev-bot to #admin-bot
        """
        # loop over guilds
        for guild in self.guilds:
            print(f'Server {guild} [{guild.id}]')
            config = self.get_config(guild)

            # create faction roles
            fac = config.get("factions", dict({}))
            for k, v in fac.items():
                role_name = f"{v} [{k}]"
                if get(guild.roles, name=role_name) is None:
                    print(f"\tCreate role {role_name}")
                    await guild.create_role(name=role_name)

            # create verified role and channels
            if config.get("verify") is not None:
                role_name = "Verified"
                if get(guild.roles, name=role_name) is None:
                    print(f"\tCreate role {role_name}")
                    await guild.create_role(name=role_name)

                for channel_name in ["verify-id", "admin"]:
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        await guild.create_text_channel(channel_name, topic="Channel created for the YATA bot")

            # create Looter role
            if config.get("loot") is not None:
                for role_name in ["Looter"]:
                    if get(guild.roles, name=role_name) is None:
                        print(f"\tCreate role {role_name}")
                        await guild.create_role(name=role_name)

                for channel_name in ["start-looting", "loot"]:
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        await guild.create_text_channel(channel_name, topic="Channel created for the YATA bot")

            # change activity
            # a = config.get("activity", dict({}))
            # if "watching" in a:
            #    print(f'\twatching {a["watching"]}')
            #    activity = discord.Activity(name=a["watching"], type=discord.ActivityType.watching)
            #    await self.change_presence(activity=activity)
            # elif "listening" in a:
            #    print(f'\tlistening {a["listening"]}')
            #    activity = discord.Activity(name=a["listening"], type=discord.ActivityType.listening)
            #    await self.change_presence(activity=activity)
            # elif "playing" in a:
            #    print(f'\tplaying {a["playing"]}')
            #    activity = discord.Activity(name=a["playing"], type=discord.ActivityType.playing)
            #    await self.change_presence(activity=activity)

        print("Ready...")

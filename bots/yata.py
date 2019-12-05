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
        config = self.get_config(guild)
        keys = config.get("keys", False)
        return random.choice([v for k, v in keys.items()]) if keys else False

    def check_module(self, guild, module):
        """ check_module: helper function
            check if guild activated a module
        """
        config = self.get_config(guild)
        if config.get(module) is None:
            return False
        else:
            return bool(config[module].get("active", False))

    async def on_ready(self):
        """ on_ready
            loop over the bot guilds and do:
                - get guild config
                - create faction roles necessary
                - create Verified role
                TODO:
                - send I'm back up message
        """
        # loop over guilds
        for guild in self.guilds:
            print(f'[SETUP] Server {guild} [{guild.id}]')
            config = self.get_config(guild)

            # leave guild not in YATA database
            if not len(config):
                print(f'\tWTF I\'m doing here?')
                # send message to guild
                owner = self.get_user(guild.owner_id)
                await owner.send(f"Contact Kivou [2000607] if you want me on your guild {guild} [{guild.id}].")
                await owner.send("As for now I can't do anything without him setting me up... so I'll be leaving.")

                # leave guild
                await guild.leave()

                # send message to creator
                my_creator = self.get_user(227470975317311488)
                await my_creator.send(f"I left {guild} [{guild.id}] owned by {owner}")
                continue

            # create category
            yata_category = get(guild.categories, name="yata-bot")
            if yata_category is None:
                print(f"\tCreate category yata-bot")
                yata_category = await guild.create_category("yata-bot")

            # create verified role and channels
            if self.check_module(guild, "verify"):
                role_verified = get(guild.roles, name="Verified")
                if role_verified is None:
                    print(f"\tCreate role Verified")
                    role_verified = await guild.create_role(name="Verified")

                # create faction roles
                fac = config.get("factions", dict({}))
                for k, v in fac.items():
                    role_name = f"{v} [{k}]"
                    if get(guild.roles, name=role_name) is None:
                        print(f"\tCreate role {role_name}")
                        await guild.create_role(name=role_name)

                # create admin channel
                channel_name = "yata-admin"
                if get(guild.channels, name=channel_name) is None:
                    print(f"\tCreate channel {channel_name}")
                    overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False)}
                    channel_admin = await guild.create_text_channel(channel_name, topic="Administration channel for the YATA bot", overwrites=overwrites, category=yata_category)
                    await channel_admin.send(f"This is the admin channel for `!verifyAll`, `!checkFactions` or any other command")

                # create admin channel
                channel_name = "readme"
                if get(guild.channels, name=channel_name) is None:
                    print(f"\tCreate channel {channel_name}")
                    channel_readme = await guild.create_text_channel(channel_name, topic="User information about the YATA bot", category=yata_category)

                channel_name = "verify-id"
                if get(guild.channels, name=channel_name) is None:
                    print(f"\tCreate channel {channel_name}")
                    channel_verif = await guild.create_text_channel(channel_name, topic="Verification channel for the YATA bot", category=yata_category)
                    await channel_verif.send(f"This channel is now the system channel")
                    await channel_verif.send(f"If you haven't been assigned the {role_verified.mention} that's where you can type `!verify` or `!verify tornId` to verify another member")
                    await guild.edit(system_channel=channel_verif)

            if self.check_module(guild, "loot"):
                # create Looter role
                role_loot = get(guild.roles, name="Looter")
                if role_loot is None:
                    print(f"\tCreate role Looter")
                    role_loot = await guild.create_role(name="Looter")

                # create loot channel
                channel_name = "loot"
                if get(guild.channels, name=channel_name) is None:
                    print(f"\tCreate channel {channel_name}")
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        role_loot: discord.PermissionOverwrite(read_messages=True)
                        }
                    channel_loot = await guild.create_text_channel(channel_name, topic="Loot channel for the YATA bot", overwrites=overwrites, category=yata_category)
                    await channel_loot.send(f"{role_loot.mention} will reveive notification here")
                    await channel_loot.send("Type `!loot` here to get the npc timings")
                    await channel_loot.send(f"Type `!looter` to remove your {role_loot.mention} role")

                # create start-looting channel
                channel_loot = get(guild.channels, name="loot")
                channel_name = "start-looting"
                if get(guild.channels, name=channel_name) is None:
                    print(f"\tCreate channel {channel_name}")
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=True),
                        role_loot: discord.PermissionOverwrite(read_messages=False)
                        }
                    channel_slooting = await guild.create_text_channel(channel_name, topic="Loot channel for the YATA bot", overwrites=overwrites, category=yata_category)
                    await channel_slooting.send(f'Type `!looter` here to have access to the {channel_loot.mention} channel')

            # create socks role and channels
            if self.check_module(guild, "stocks"):
                stocks = config.get("stocks")
                for stock in [s for s in stocks if s not in ["active"]]:
                    stock_role = get(guild.roles, name=stock)
                    if stock_role is None:
                        print(f"\tCreate role {stock}")
                        stock_role = await guild.create_role(name=stock)

                    # create stock channel
                    if get(guild.channels, name=stock) is None:
                        print(f"\tCreate channel {stock}")
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            stock_role: discord.PermissionOverwrite(read_messages=True),
                            }
                        channel_stock = await guild.create_text_channel(stock, topic=f"{stock} stock channel for the YATA bot", overwrites=overwrites, category=yata_category)
                        await channel_stock.send(f"Type `!{stock}` to see the {stock} BB status amoung the members")

        # change activity
        activity = discord.Activity(name="TORN", type=discord.ActivityType.playing)
        await self.change_presence(activity=activity)

        print("[SETUP] Ready...")

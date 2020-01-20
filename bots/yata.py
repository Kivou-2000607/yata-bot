# import standard modules
import json
import os
import aiohttp

# import discord modules
import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

# import bot functions and classes
# from includes.yata_db import get_member_key
from includes.yata_db import *


# Child class of Bot with extra configuration variables
class YataBot(Bot):
    def __init__(self, configs=None, bot_id=0, **args):
        Bot.__init__(self, **args)
        self.configs = configs
        self.bot_id = bot_id

    def get_config(self, guild):
        """ get_config: helper function
            gets configuration for a guild
        """
        return self.configs.get(str(guild.id), dict({}))

    async def discord_to_torn(self, member, key):
        """ get a torn id form discord id
            return tornId, None: okay
            return -1, error: api error
            return -2, None: not verified on discord
        """
        url = f"https://api.torn.com/user/{member.id}?selections=discord&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        if 'error' in req:
            # print(f'[DISCORD TO TORN] api error "{key}": {req["error"]["error"]}')
            return -1, req['error']

        elif req['discord'].get("userID") == '':
            # print(f'[DISCORD TO TORN] discord id {member.id} not verified')
            return -2, None

        else:
            return int(req['discord'].get("userID")), None

    async def get_master_key(self, guild):
        """ gets a random master key from configuration
            return 0, id, Name, Key: All good
            return -1, None, None, None: no key given
        """
        import random
        config = self.get_config(guild)
        ids_keys = config.get("keys", False)
        if ids_keys:
            id, key = random.choice([(k, v) for k, v in ids_keys.items()]) if ids_keys else (False, False)
            return 0, id, key
        else:
            return -1, None, None

    async def get_user_key(self, ctx, member, needPerm=True):
        """ gets a key from discord member
            return status, tornId, Name, key
            return 0, id, Name, Key: All good
            return -1, None, None, None: no master key given
            return -2, None, None, None: master key api error
            return -3, None, None, None: user not verified
            return -4, id, None, None: did not find torn id in yata db
            return -5, id, Name, None: member did not give perm
        """

        # get master key to check identity

        # print(f"[GET USER KEY] <{ctx.guild}> get master key")
        master_status, master_id, master_key = await self.get_master_key(ctx.guild)
        if master_status == -1:
            # print(f"[GET USER KEY] <{ctx.guild}> no master key given")
            await ctx.send(":x: no master key given")
            return -1, None, None, None
        # print(f"[GET USER KEY] <{ctx.guild}> master key id {master_id}")

        # get torn id from discord id

        # print(f"[GET USER KEY] <{ctx.guild}> get torn id for {member} [{member.id}]")
        tornId, msg = await self.discord_to_torn(member, master_key)

        # handle master api error or not verified member

        if tornId == -1:
            # print(f'[GET MEMBER KEY] status -1: master key error {msg["error"]}')
            await ctx.send(f':x: api error with master key id {master_id}: *{msg["error"]}*')
            return -2, None, None, None
        elif tornId == -2:
            # print(f'[GET MEMBER KEY] status -2: user not verified')
            await ctx.send(f':x: {member.mention} is not verified')
            return -3, None, None, None

        # get YATA user

        user = await get_yata_user(tornId)

        # handle user not on YATA
        if not len(user):
            # print(f"[GET MEMBER KEY] torn id {tornId} not in YATA")
            await ctx.send(f':x: {member.mention} not found in YATA\'s database')
            return -4, tornId, None, None

        # Return user if perm given

        user = tuple(user[0])
        if not user[3] and needPerm:
            # print(f"[GET MEMBER KEY] torn id {user[1]} [{user[0]}] didn't gave perm")
            await ctx.send(f':x: {member.mention} didn\'t give permission to use their API key (https://yata.alwaysdata.net/bot/)')
            return -5, user[0], user[1], None

        # return id, name, key
        else:
            # print(f"[GET MEMBER KEY] torn id {user[1]} [{user[0]}] all gooood")
            return 0, user[0], user[1], user[2]

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
            loop over the bot guilds and do the setup
        """
        # loop over guilds
        for guild in self.guilds:
            try:
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

                # push guild name to yata
                await push_guild_name(guild)

                # stop if not managing channels
                if not self.check_module(guild, "channels"):
                    continue

                # create category
                yata_category = get(guild.categories, name="yata-bot")
                bot_role = get(guild.roles, name=self.user.name)
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
                        role_name = f"{v} [{k}]" if config['verify'].get('id', False) else f"{v}"
                        if get(guild.roles, name=role_name) is None:
                            print(f"\tCreate faction role {role_name}")
                            await guild.create_role(name=role_name)

                    # create common role
                    com = config['verify'].get("common")
                    if com:
                        role_name = get(guild.roles, name=com)
                        if role_name is None:
                            print(f"\tCreate common role {com}")
                            await guild.create_role(name=com)

                    # create admin channel
                    channel_name = "yata-admin"
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            bot_role: discord.PermissionOverwrite(read_messages=True)
                            }
                        channel_admin = await guild.create_text_channel(channel_name, topic="Administration channel for the YATA bot", overwrites=overwrites, category=yata_category)
                        await channel_admin.send(f"This is the admin channel for `!verifyAll`, `!checkFactions` or any other command")

                    # create readme channel
                    channel_name = "readme"
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        channel_readme = await guild.create_text_channel(channel_name, topic="User information about the YATA bot", category=yata_category)

                    channel_name = "verify-id"
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        channel_verif = await guild.create_text_channel(channel_name, topic="Verification channel for the YATA bot", category=yata_category)
                        await channel_verif.send(f"If you haven't been assigned the {role_verified.mention} that's where you can type `!verify` or `!verify tornId` to verify another member")
                        try:
                            await guild.edit(system_channel=channel_verif)
                            await channel_verif.send(f"This channel is now the system channel")
                        except BaseException:
                            pass

                if self.check_module(guild, "chain"):
                    # create chain channel
                    channel_name = self.get_config(guild).get("chain").get("channel", "chain")
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        channel_chain = await guild.create_text_channel(channel_name, topic="Chain channel for the YATA bot", category=yata_category)
                        await channel_chain.send("Type `!chain` here to start getting notifications and `!stop` to stop them.")
                    await get(guild.channels, name=channel_name).send(":arrows_counterclockwise: I had to reboot which stop all potential chains and retals watching. Please relaunch them.")

                if self.check_module(guild, "loot"):
                    # create Looter role
                    role_loot = get(guild.roles, name="Looter")
                    if role_loot is None:
                        print(f"\tCreate role Looter")
                        role_loot = await guild.create_role(name="Looter", mentionable=True)

                    # create loot channel
                    channel_name = "loot"
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            role_loot: discord.PermissionOverwrite(read_messages=True),
                            bot_role: discord.PermissionOverwrite(read_messages=True)
                            }
                        channel_loot = await guild.create_text_channel(channel_name, topic="Loot channel for the YATA bot", overwrites=overwrites, category=yata_category)
                        await channel_loot.send(f"{role_loot.mention} will reveive notification here")
                        await channel_loot.send("Type `!loot` here to get the npc timings")
                        await channel_loot.send(f"Type `!looter` to remove your {role_loot.mention} role")

                if self.check_module(guild, "revive"):
                    # create Reviver role
                    reviver = get(guild.roles, name="Reviver")
                    if reviver is None:
                        print(f"\tCreate role Reviver")
                        reviver = await guild.create_role(name="Reviver", mentionable=True)

                    # create revive channel
                    channel_name = "revive"
                    if get(guild.channels, name=channel_name) is None:
                        print(f"\tCreate channel {channel_name}")
                        channel_revive = await guild.create_text_channel(channel_name, topic="Revive channel for the YATA bot", category=yata_category)
                        await channel_revive.send(f"{reviver.mention} will reveive notifications here")
                        await channel_revive.send("Type `!revive` or `!r` here to send a revive call")
                        await channel_revive.send(f"Type `!reviver` to add or remove your {reviver.mention} role")

                # create socks role and channels
                if self.check_module(guild, "stocks"):
                    stocks = config.get("stocks")

                    # wssb and tcb
                    for stock in [s for s in stocks if s not in ["active", "channel", 'alerts']]:
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
                                bot_role: discord.PermissionOverwrite(read_messages=True)
                                }
                            channel_stock = await guild.create_text_channel(stock, topic=f"{stock} stock channel for the YATA bot", overwrites=overwrites, category=yata_category)
                            await channel_stock.send(f"Type `!{stock}` to see the {stock} BB status amoung the members")

                    # create alerts
                    if stocks.get("alerts"):
                        stock_role = get(guild.roles, name="Trader")
                        if stock_role is None:
                            print(f"\tCreate role Trader")
                            stock_role = await guild.create_role(name="Trader", mentionable=True)
                        channel_name = "stocks" if stocks.get("channel") is None else stocks.get("channel")
                        if get(guild.channels, name=channel_name) is None:
                            print(f"\tCreate channel {channel_name}")
                            overwrites = {
                                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                stock_role: discord.PermissionOverwrite(read_messages=True),
                                bot_role: discord.PermissionOverwrite(read_messages=True)
                            }
                            channel_stock = await guild.create_text_channel(channel_name, topic=f"Alerts stock channel for the YATA bot", overwrites=overwrites, category=yata_category)
                            await channel_stock.send(f"{stock_role.mention} will be notified here")

            except BaseException as e:
                print(f"[SETUP] Error in guild {guild}: {e}")

        # change activity
        activity = discord.Activity(name="TORN", type=discord.ActivityType.playing)
        await self.change_presence(activity=activity)

        print("[SETUP] Ready...")

    async def on_guild_join(self, guild):
        """notifies me when joining a guild"""
        owner = self.get_user(guild.owner_id)
        my_creator = self.get_user(227470975317311488)
        await my_creator.send(f"I joined guild **{guild} [{guild.id}]** owned by **{owner}**")

# import standard modules
import json
import os
import aiohttp
import traceback
import html

# import discord modules
import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

# import bot functions and classes
# from includes.yata_db import get_member_key
from includes.yata_db import *
import includes.formating as fmt


# Child class of Bot with extra configuration variables
class YataBot(Bot):
    def __init__(self, configs=None, administrators=None, bot_id=0, **args):
        Bot.__init__(self, **args)
        self.configs = configs
        self.administrators = administrators
        self.bot_id = bot_id

    def get_config(self, guild):
        """ get_config: helper function
            gets configuration for a guild
        """
        return self.configs.get(str(guild.id), dict({}))

    def get_allowed_channels(self, config, key):
        channels = config.get(key)
        if channels is None:
            return [key]
        elif '*' in channels["channels"]:
            return ["*"]
        else:
            return channels["channels"]

    def get_allowed_roles(self, config, key):
        roles = config.get(key)
        if roles is None:
            return [key]
        elif '*' in roles["roles"]:
            return ["*"]
        else:
            return roles["roles"]

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

    async def get_user_key(self, ctx, member, needPerm=True, returnMaster=False, delError=False):
        """ gets a key from discord member
            return status, tornId, Name, key
            return 0, id, Name, Key: All good
            return -1, None, None, None: no master key given
            return -2, None, None, None: master key api error
            return -3, master_id, None, master_key: user not verified
            return -4, id, None, master_key: did not find torn id in yata db
            return -5, id, Name, master_key: member did not give perm

            if returnMaster: return master key if key not available
            else return None
        """

        # get master key to check identity

        # print(f"[GET USER KEY] <{ctx.guild}> get master key")
        master_status, master_id, master_key = await self.get_master_key(ctx.guild)
        if master_status == -1:
            # print(f"[GET USER KEY] <{ctx.guild}> no master key given")
            m = await ctx.send(":x: no master key given")
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -1, None, None, None
        # print(f"[GET USER KEY] <{ctx.guild}> master key id {master_id}")

        # get torn id from discord id

        # print(f"[GET USER KEY] <{ctx.guild}> get torn id for {member} [{member.id}]")
        tornId, msg = await self.discord_to_torn(member, master_key)

        # handle master api error or not verified member

        if tornId == -1:
            # print(f'[GET MEMBER KEY] status -1: master key error {msg["error"]}')
            m = await ctx.send(f':x: Torn API error with master key id {master_id}: *{msg["error"]}*')
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -2, None, None, None
        elif tornId == -2:
            # print(f'[GET MEMBER KEY] status -2: user not verified')
            m = await ctx.send(f':x: {member.mention} is not verified in the official Torn discord. They have to go there and get verified first: https://www.torn.com/discord')
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -3, master_id, None, master_key if returnMaster else None

        # get YATA user

        user = await get_yata_user(tornId)

        # handle user not on YATA
        if not len(user):
            # print(f"[GET MEMBER KEY] torn id {tornId} not in YATA")
            m = await ctx.send(f':x: **{member}** is not in the YATA database. They have to log there so that I can use their key: https://yata.alwaysdata.net')
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -4, tornId, None, master_key if returnMaster else None

        # Return user if perm given

        user = tuple(user[0])
        if not user[3] and needPerm:
            # print(f"[GET MEMBER KEY] torn id {user[1]} [{user[0]}] didn't gave perm")
            m = await ctx.send(f':x: {member.mention} didn\'t give their permission to use their API key. They need to check out the API keys management section here: https://yata.alwaysdata.net/bot/documentation/')
            if delError:
                await asyncio.sleep(5)
                await m.delete()
            return -5, user[0], user[1], master_key if returnMaster else None

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

    async def sendAdminChannel(self, msg, channelId=651386992898342912):
        """ sends message to yata admin channel by default
        """
        channel = self.get_channel(channelId)
        if channel is not None:
            await channel.send(msg)

    async def sendLogChannel(self, msg, channelId=685470217002156098):
        """ sends message to yata admin channel by default
        """
        channel = self.get_channel(channelId)
        if channel is not None:
            await channel.send(msg)

    async def on_disconnect(self):
        await self.sendAdminChannel(":red_circle: disconnect")

    async def on_connect(self):
        await self.sendAdminChannel(":green_circle: connect")

    async def on_resume(self):
        await self.sendAdminChannel(":green_circle: resume")

    async def on_ready(self):
        """ on_ready
            loop over the bot guilds and do the setup
        """
        await self.sendAdminChannel(":green_circle: ready")
        await self.rebuildGuilds(reboot=True)

        # change activity
        activity = discord.Activity(name="TORN", type=discord.ActivityType.playing)
        await self.change_presence(activity=activity)

        print("[SETUP] Ready...")

    async def on_guild_join(self, guild):
        """notifies me when joining a guild"""
        owner = self.get_user(guild.owner_id)
        for administratorId in self.administrators:
            administrator = self.get_user(int(administratorId))
            await administrator.send(f"I **joined** guild **{guild} [{guild.id}]** owned by **{owner}**")

    async def on_guild_remove(self, guild):
        """notifies me when leaving a guild"""
        owner = self.get_user(guild.owner_id)
        for administratorId in self.administrators:
            administrator = self.get_user(int(administratorId))
            await administrator.send(f"I **left** guild **{guild} [{guild.id}]** owned by **{owner}** because I got banned, kicked, left the guild or the guild was deleted.")

    async def rebuildGuild(self, guild, reboot=False, verbose=False):
        try:
            config = self.get_config(guild)
            lst = [f"{guild}  [{guild.id}]"]

            # leave guild not in YATA database
            if not len(config):
                lst.append(f'\tWTF I\'m doing here?')
                # send message to guild
                owner = self.get_user(guild.owner_id)
                await owner.send(f"Contact Kivou [2000607] if you want me on your guild {guild} [{guild.id}].")
                await owner.send("As for now I can't do anything without him setting me up... so I'll be leaving.")

                # leave guild
                await guild.leave()

                # send message to creator
                for administratorId in self.administrators:
                    administrator = self.get_user(int(administratorId))
                    await administrator.send(f"On reboot I left **{guild} [{guild.id}]** owned by **{owner}** because no configurations were found in the database.")

                if verbose:
                    await fmt.send_tt(verbose, lst)
                return

            # push guild name to yata
            bot = get(guild.members, id=self.user.id)
            await push_guild_info(guild, bot, self.bot_id)

            # stop if not managing channels
            if not config["admin"].get("manage", False):
                lst.append("Skip managing")
                if verbose:
                    await fmt.send_tt(verbose, lst)
                return

            # create category
            yata_category = get(guild.categories, name="yata-bot")
            bot_role = get(guild.roles, name=self.user.name)
            if yata_category is None:
                lst.append("Create category yata-bot")
                yata_category = await guild.create_category("yata-bot")

            # create admin channel
            channel_name = "yata-admin"
            if get(guild.channels, name=channel_name) is None:
                lst.append(f"\tCreate channel {channel_name}")
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    bot_role: discord.PermissionOverwrite(read_messages=True)
                }
                channel_admin = await guild.create_text_channel(channel_name, topic="Administration channel for the YATA bot", overwrites=overwrites, category=yata_category)
                await channel_admin.send(f"This is the admin channel for `!verifyAll`, `!checkFactions` or `!reviveServers`")

            # create verified role and channels
            if self.check_module(guild, "verify"):
                role_verified = get(guild.roles, name="Verified")
                if role_verified is None:
                    lst.append(f"\tCreate role Verified")
                    role_verified = await guild.create_role(name="Verified")

                # create faction roles
                fac = config.get("factions", dict({}))
                for k, v in fac.items():
                    role_name = html.unescape(f"{v} [{k}]" if config['verify'].get('id', False) else f"{v}")
                    if get(guild.roles, name=role_name) is None:
                        lst.append(f"\tCreate faction role {role_name}")
                        await guild.create_role(name=role_name)

                # create common role
                com = config['verify'].get("common")
                if com:
                    role_name = get(guild.roles, name=com)
                    if role_name is None:
                        lst.append(f"\tCreate common role {com}")
                        await guild.create_role(name=com)

                for channel_name in [c for c in config["verify"].get("channels", ["verify"]) if c != "*"]:
                    if get(guild.channels, name=channel_name) is None:
                        lst.append(f"\tCreate channel {channel_name}")
                        channel_verif = await guild.create_text_channel(channel_name, topic="Verification channel for the YATA bot", category=yata_category)
                        await channel_verif.send(f"If you haven't been assigned the {role_verified.mention} that's where you can type `!verify` or `!verify tornId` to verify another member")

            if self.check_module(guild, "chain"):
                # create chain channel
                for channel_name in [c for c in config["chain"].get("channels", ["chain"]) if c != "*"]:
                    if get(guild.channels, name=channel_name) is None:
                        lst.append(f"\tCreate channel {channel_name}")
                        channel_chain = await guild.create_text_channel(channel_name, topic="Chain channel for the YATA bot", category=yata_category)
                        await channel_chain.send("Type `!chain` here to start getting notifications and `!stopchain` to stop them.")
                    # if reboot:
                    #     await get(guild.channels, name=channel_name).send(":arrows_counterclockwise: I had to reboot which stop all potential chains and retals watching. Please relaunch them.")

            if self.check_module(guild, "crimes"):
                # create crimes channel
                for channel_name in [c for c in config["crimes"].get("channels", ["oc"]) if c != "*"]:
                    if get(guild.channels, name=channel_name) is None:
                        lst.append(f"\tCreate channel {channel_name}")
                        channel_oc = await guild.create_text_channel(channel_name, topic="Crimes channel for the YATA bot", category=yata_category)
                        await channel_oc.send("Type `!oc` here to start/stop getting notifications when ocs are ready.")

            if self.check_module(guild, "rackets"):
                # create rackets channel
                for channel_name in [c for c in config["rackets"].get("channels", ["rackets"]) if c != "*"]:
                    if get(guild.channels, name=channel_name) is None:
                        lst.append(f"\tCreate channel {channel_name}")
                        await guild.create_text_channel(channel_name, topic="Rackets channel for the YATA bot", category=yata_category)

                # create rackets roles
                for role_name in [c for c in config["rackets"].get("roles")]:
                    if role_name is not None and get(guild.roles, name=role_name) is None:
                        lst.append(f"\tCreate role {role_name}")
                        channel_oc = await guild.create_role(name=role_name, mentionable=True)

            if self.check_module(guild, "loot"):
                # create Looter role
                role_loot = get(guild.roles, name="Looter")
                if role_loot is None:
                    lst.append(f"\tCreate role Looter")
                    role_loot = await guild.create_role(name="Looter", mentionable=True)

                # create loot channel
                for channel_name in [c for c in config["loot"].get("channels", ["loot"]) if c != "*"]:
                    if get(guild.channels, name=channel_name) is None:
                        lst.append(f"\tCreate channel {channel_name}")
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
                    lst.append(f"\tCreate role Reviver")
                    reviver = await guild.create_role(name="Reviver", mentionable=True)

                # create revive channel
                for channel_name in [c for c in config["revive"].get("channels", ["revive"]) if c != "*"]:
                    if get(guild.channels, name=channel_name) is None:
                        lst.append(f"\tCreate channel {channel_name}")
                        channel_revive = await guild.create_text_channel(channel_name, topic="Revive channel for the YATA bot", category=yata_category)
                        await channel_revive.send(f"{reviver.mention} will reveive notifications here")
                        await channel_revive.send("Type `!revive` or `!r` here to send a revive call")
                        await channel_revive.send(f"Type `!reviver` to add or remove your {reviver.mention} role")

            if self.check_module(guild, "api"):
                # create api channels
                for channel_name in [c for c in config["api"].get("channels", ["api"]) if c != "*"]:
                    if get(guild.channels, name=channel_name) is None:
                        lst.append(f"\tCreate channel {channel_name}")
                        channel_api = await guild.create_text_channel(channel_name, topic="API channel for the YATA bot", category=yata_category)
                        await channel_api.send("Use the API module commands here")

            # create socks role and channels
            if self.check_module(guild, "stocks"):
                stocks = config.get("stocks")

                # wssb and tcb
                for stock in [s for s in stocks if s not in ["active", "channels", 'alerts']]:
                    stock_role = get(guild.roles, name=stock)
                    if stock_role is None:
                        lst.append(f"\tCreate role {stock}")
                        stock_role = await guild.create_role(name=stock)

                    # create stock channel
                    if get(guild.channels, name=stock) is None:
                        lst.append(f"\tCreate channel {stock}")
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
                        lst.append(f"\tCreate role Trader")
                        stock_role = await guild.create_role(name="Trader", mentionable=True)

                    for channel_name in [c for c in config["stocks"].get("channels", ["stocks"]) if c != "*"]:
                        if get(guild.channels, name=channel_name) is None:
                            lst.append(f"\tCreate channel {channel_name}")
                            overwrites = {
                                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                stock_role: discord.PermissionOverwrite(read_messages=True),
                                bot_role: discord.PermissionOverwrite(read_messages=True)
                            }
                            channel_stock = await guild.create_text_channel(channel_name, topic=f"Alerts stock channel for the YATA bot", overwrites=overwrites, category=yata_category)
                            await channel_stock.send(f"{stock_role.mention} will be notified here")

            if verbose:
                await fmt.send_tt(verbose, lst)

        except BaseException as e:
            print(f'ERROR in {guild} [{guild.id}]: {e}')
            print(f'{traceback.format_exc()}')
            if verbose:
                await verbose.send(f'```ERROR in {guild} [{guild.id}]: {e}```')
                await verbose.send(f'```{traceback.format_exc()}```')

    async def rebuildGuilds(self, reboot=False, verbose=False):
        # loop over guilds
        for guild in self.guilds:
            await self.rebuildGuild(guild, reboot=reboot, verbose=verbose)

# import standard modules
import asyncio
import aiohttp
# import datetime
# import json

# import discord modules
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt
from includes.yata_db import load_configurations
from includes.yata_db import push_configurations


class Revive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["r"])
    async def revive(self, ctx):
        """ send revive message to @Reviver
        """

        # return if revive not active
        if not self.bot.check_module(ctx.guild, "revive"):
            await ctx.send(":x: Revive module not activated")
            return

        # check role and channel
        config = self.bot.get_config(ctx.guild)
        channelName = config.get("revive", dict({})).get("channel", False)
        ALLOWED_CHANNELS = [channelName] if channelName else ["revive"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # Get user key
        lst = []
        errors = []
        status, tornId, Name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status in [-1, -2, -3]:
            await ctx.send(":x: I cannot send revive message")
            return

        if status in [-4]:
            errors.append(":x: I cannot specify faction or hospitalization time")
            req = dict({})

        else:
            # api call to get potential status and faction
            url = f'https://api.torn.com/user/?key={key}'
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    req = await r.json()

            # handle API error
            if 'error' in req:
                errors.append(f':x: Problem with {Name} [{tornId}]\'s key: *{req["error"]["error"]}*')
                errors.append(":x: I cannot specify faction or hospitalization time")

        # get reviver role
        role = get(ctx.guild.roles, name="Reviver")
        url = f'https://www.torn.com/profiles.php?XID={tornId}'
        if req.get('faction', False) and req["faction"]["faction_id"]:
            lst.append(f'**{Name} [{tornId}]** from **{req["faction"]["faction_name"]} [{req["faction"]["faction_id"]}]** needs a revive {url}')
        else:
            lst.append(f'**{Name} [{tornId}]** needs a revive {url}')

        # add status
        if req.get('status', False) and req["status"]["state"] == "Hospital":
            lst.append(f'{req["status"]["description"]} ({req["status"]["details"]})')

        # send message to current channel
        if len(errors):
            msg = "\n".join(errors)
            await ctx.send(f'{msg}')
        msg = "\n".join(lst)
        await ctx.send(f'{role.mention} {msg}')

        for id in self.bot.configs[str(ctx.guild.id)]["revive"].get("servers", []):
            try:
                if ctx.guild.id in self.bot.configs[str(id)]["revive"].get("blacklist", []):
                    await ctx.send(f'Server {ctx.guild.name} has blacklisted you')
                else:
                    # get guild, role and channel
                    guild = self.bot.get_guild(id)
                    role = get(guild.roles, name="Reviver")
                    channel = get(guild.channels, name="revive")
                    await channel.send(f'{role.mention} {msg}')
                    # await ctx.send(f'Sent to {id}')
            except BaseException as e:
                await ctx.send(f":x: Error with guild {id}: {e}")

    @commands.command(aliases=["a"])
    async def reviveServers(self, ctx, *args):

        # return if revive not active
        if not self.bot.check_module(ctx.guild, "revive"):
            await ctx.send(":x: Revive module not activated")
            return

        # check role and channel
        ALLOWED_CHANNELS = ["yata-admin"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        # load configuration
        configs = self.bot.configs

        # dictionnary of all servers with revive enables
        servers = {k: [v["admin"], v["revive"].get("servers", []), v["revive"].get("blacklist", [])] for k, v in configs.items() if v.get("revive", dict({})).get("active", False) and int(k) != ctx.guild.id}

        # update configuration
        if len(args) and args[0].replace("-", "").isdigit() and args[0].replace("-", "") in servers:
            serverId = int(args[0])
            if serverId > 0:
                servTmp = configs[str(ctx.guild.id)]["revive"].get('servers', [])
                # toogle server id
                if serverId in servTmp:
                    servTmp.remove(serverId)
                else:
                    servTmp.append(serverId)
                configs[str(ctx.guild.id)]["revive"]['servers'] = servTmp

            else:
                serverId = -serverId
                servTmp = configs[str(ctx.guild.id)]["revive"].get('blacklist', [])
                # toogle server id
                if serverId in servTmp:
                    servTmp.remove(serverId)
                else:
                    servTmp.append(serverId)
                configs[str(ctx.guild.id)]["revive"]['blacklist'] = servTmp

            self.bot.configs = configs
            await push_configurations(self.bot.bot_id, configs)

        myServers = configs[str(ctx.guild.id)]["revive"].get("servers", [])  # id of all servers I want to send message
        myBlackList = configs[str(ctx.guild.id)]["revive"].get("blacklist", [])  # id of all servers I want to send message

        if len(servers):
            lst = ["List of servers with the *revive module* activated\n"]
            for k, [s, r, b] in servers.items():
                lst.append(f'**{s["name"]}** server (contact **{s["contact"]} [{s["contact_id"]}]**)')
                if int(k) in myServers:
                    lst.append('\tSending: **on**')
                else:
                    lst.append('\tSending: **off**')
                if ctx.guild.id in r:
                    lst.append('\tReceiving: **on**')
                else:
                    lst.append('\tReceiving: **off**')
                if int(k) in myBlackList:
                    lst.append('\tThis server is on your blacklist')
                if ctx.guild.id in b:
                    lst.append('\tThis server have you on their blacklist')

                lst.append('\tType `!reviveServers {}` to start or stop sending this server your revive calls'.format(k))
                lst.append('\tType `!reviveServers -{}` to add or remove this server from your blacklist\n'.format(k))

        else:
            await ctx.send(":x: No other servers have activated their revive option")
            return

        await fmt.send_tt(ctx, lst, tt=False)

    @commands.command()
    async def reviver(self, ctx):
        """Add/remove @Reviver role"""
        # return if revive not active
        if not self.bot.check_module(ctx.guild, "revive"):
            await ctx.send(":x: Revive module not activated")
            return

        # Get Reviver role
        role = get(ctx.guild.roles, name="Reviver")

        if role in ctx.author.roles:
            # remove Reviver
            await ctx.author.remove_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **stop** receiving notifications for revives.")
        else:
            # assign Reviver
            await ctx.author.add_roles(role)
            msg = await ctx.send(f"**{ctx.author.display_name}**, you'll **start** receiving notifications for revives.")

        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()

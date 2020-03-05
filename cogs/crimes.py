# import standard modules
import asyncio
import aiohttp
import datetime
import json
import re

# import discord modules
from discord.ext import commands
from discord.utils import get
from discord.ext import tasks

# import bot functions and classes
import includes.checks as checks
import includes.formating as fmt
from includes.yata_db import push_configurations


class Crimes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ocTask.start()

    def cog_unload(self):
        self.ocTask.cancel()

    @commands.command()
    async def ocs(self, ctx):
        """ list all current ocs watching
        """
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "crimes"):
            await ctx.send(":x: Crimes module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = ["yata-admin"]
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        ocs = config["crimes"].get("oc")
        if ocs is None or not len(ocs):
            await ctx.send("You're not watching any ocs.")
        for v in ocs.values():
            channel = get(ctx.guild.channels, id=v["channelId"])
            admin = get(ctx.guild.channels, name="yata-admin")
            notify = 'nobody' if v["roleId"] is None else f'<@&{v["roleId"]}>'
            lst = [f'{v["name"]} [{v["tornId"]}] is notifying {notify} for ocs in #{channel}.',
                   f'It can be stopped either by them typing `!oc` in #{channel} or anyone typing `!stopoc {v["tornId"]}` in #{admin}.']
            await ctx.send("\n".join(lst))

    @commands.command()
    async def stopoc(self, ctx, *args):
        """ force stop a oc watching (for admin)
        """
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "crimes"):
            await ctx.send(":x: Crimes module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "crimes")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        if len(args) and args[0].isdigit():
            tornId = str(args[0])
        else:
            admin = get(ctx.guild.channels, name="yata-admin")
            lst = ["If you want to stop watching ocs you started simply type `!oc` in the channel you started it.",
                   f"If you want to stop watching ocs someone else started you need to enter a user Id in {admin.mention}.",
                   f"Type `!ocs` in {admin.mention} for more detals."]
            await ctx.send("\n".join(lst))
            return

        ocs = config["crimes"].get("oc")
        if ocs is None:
            await ctx.send("You're not watching any ocs.")
        elif str(tornId) not in ocs:
            await ctx.send(f"Player {tornId} was not watching any ocs.")
        else:
            v = config["crimes"]["oc"][str(tornId)]
            name = v.get("name")
            channel = get(ctx.guild.channels, id=v["channelId"])
            del config["crimes"]["oc"][str(tornId)]
            if channel is not None:
                await channel.send(f':x: **{name} [{tornId}]**: Stop watching ocs on behalf of {ctx.author.nick}.')

            self.bot.configs[str(ctx.guild.id)] = config
            await push_configurations(self.bot.bot_id, self.bot.configs)

    @commands.command()
    async def oc(self, ctx, *args):
        """ start / stop watching for organized crimes
        """
        # return if chain not active
        if not self.bot.check_module(ctx.guild, "crimes"):
            await ctx.send(":x: Crimes module not activated")
            return

        # check channels
        config = self.bot.get_config(ctx.guild)
        ALLOWED_CHANNELS = self.bot.get_allowed_channels(config, "crimes")
        if await checks.channels(ctx, ALLOWED_CHANNELS):
            pass
        else:
            return

        status, tornId, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False, delError=True)

        # just to be sure
        tornId = str(tornId)

        if config["crimes"].get("oc") is None:
            config["crimes"]["oc"] = dict({})

        if status == 0:

            if len(args) and args[0].replace("<@&", "").replace(">", "").isdigit():
                roleId = int(args[0].replace("<@&", "").replace(">", ""))
            else:
                roleId = None

            if str(tornId) in config["crimes"].get("oc"):
                del config["crimes"]["oc"][str(tornId)]
                await ctx.send(f':x: **{name} [{tornId}]**: Stop watching organized crimes.')
            else:
                oc = {"name": name,
                      "tornId": str(tornId),
                      "key": key,
                      "roleId": roleId,
                      "channelId": ctx.channel.id}
                config["crimes"]["oc"][str(tornId)] = oc

                notified = "Nobody" if roleId is None else f"<@&{roleId}>"
                await ctx.send(f':white_check_mark: **{name} [{tornId}]** Start watching organized crimes for their faction in {ctx.channel.mention}. {notified} will be notified.')

        else:
            if str(tornId) in config["crimes"].get("oc"):
                del config["crimes"]["oc"][str(tornId)]
                await ctx.send(f':x: **{name} [{tornId}]**: Stop watching organized crimes.')

        self.bot.configs[str(ctx.guild.id)] = config
        await push_configurations(self.bot.bot_id, self.bot.configs)

    async def _oc(self, guild, oc):

        key = oc.get("key")
        tornId = str(oc.get("tornId"))
        name = oc.get("name")
        roleId = oc.get("roleId")
        channelId = oc.get("channelId")

        channel = get(guild.channels, id=channelId)
        notified = " " if roleId is None else f" <@&{roleId}> "
        if channel is None:
            return False

        url = f'https://api.torn.com/faction/?selections=basic,crimes&key={key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error
        if 'error' in req:
            await channel.send(f':x: `{name} [{tornId}]` Problem with their key for oc: *{req["error"]["error"]}*')
            if req["error"]["code"] in [1, 2, 6, 7, 10]:
                await channel.send(f':x: `{name} [{tornId}]` oc stopped...')
                return False
            else:
                return True

        if not int(req["ID"]):
            await channel.send(f':x: `{name} [{tornId}]` No factions found... oc stopped...')
            return False

        fId = req["ID"]
        fName = req["name"]

        now = datetime.datetime.utcnow()
        epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        nowts = (now - epoch).total_seconds()
        if "mentions" not in oc:
            oc["mentions"] = []
        for k, v in req["crimes"].items():
            # delay = int(nowts - v["timestamp_ended"]) / float(60)
            if str(k) in oc["mentions"]:
                continue

            ready = True
            participants = [list(p.values())[0] for p in v["participants"]]
            if participants[0] is None:
                ready = False
                continue

            for p in participants:
                if p["state"] != "Okay":
                    ready = False

            if v["time_left"] == 0 and v["time_completed"] == 0 and ready:
                lst = [f'{notified}{fName}: a {v["crime_name"]} ready.']
                await channel.send('\n'.join(lst))
                oc["mentions"].append(str(k))

        # clean mentions
        cleanedMentions = []
        for k in oc["mentions"]:
            if str(k) in req["crimes"]:
                cleanedMentions.append(str(k))

        oc["mentions"] = cleanedMentions

        # delete old messages
        # fminutes = now - datetime.timedelta(minutes=5)
        # async for message in channel.history(limit=50, before=fminutes):
        #     if message.author.bot:
        #         await message.delete()

        return True

    @tasks.loop(seconds=300)
    async def ocTask(self):
        print("[OC] start task")

        # iteration over all guilds
        async for guild in self.bot.fetch_guilds(limit=100):
            try:
                # ignore servers with no verify
                if not self.bot.check_module(guild, "crimes"):
                    continue

                # ignore servers with no option daily check
                config = self.bot.get_config(guild)
                if not config["crimes"].get("oc", False):
                    continue

                print(f"[OC] oc {guild}: start")

                # iteration over all members asking for oc watch
                guild = self.bot.get_guild(guild.id)
                todel = []
                for tornId, oc in config["crimes"]["oc"].items():
                    print(f"[OC] oc {guild}: {tornId}: {oc}")

                    # call oc faction
                    status = await self._oc(guild, oc)

                    # update metionned messages (but don't save in database, will remention in case of reboot)
                    if status:
                        self.bot.configs[str(guild.id)]["crimes"]["oc"][str(tornId)] = oc
                    else:
                        todel.append(str(tornId))

                for d in todel:
                    del self.bot.configs[str(guild.id)]["crimes"]["oc"][d]
                    await push_configurations(self.bot.bot_id, self.bot.configs)

                print(f"[OC] oc {guild}: end")

            except BaseException as e:
                print(f"[OC] guild {guild}: oc failed {e}.")

        print("[OC] end task")

    @ocTask.before_loop
    async def before_ocTask(self):
        print('[OC] waiting...')
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)

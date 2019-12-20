# import standard modules
import aiohttp

# import discord modules
import discord
from discord.ext import commands
from discord.utils import get

# import bot functions and classes
import includes.checks as checks


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx):
        """Clear not pinned messages"""
        async for m in ctx.channel.history():
            if not m.pinned:
                await m.delete()

    @commands.command(aliases=['we'])
    async def weaponexp(self, ctx, *args):
        """DM weaponexp to author"""

        await ctx.message.delete()

        # get user key

        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            print(f"[WEAPON EXP] error {status}")
            return

        # make api call

        url = f"https://api.torn.com/user/?selections=discord,weaponexp&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error

        if "error" in req:
            await ctx.author.send(f':x: You asked for your weapons experience but an error occured with your API key: *{req["error"]["error"]}*')
            return

        # if no weapon exp

        if not len(req.get("weaponexp", [])):
            await ctx.author.send(f"no weapon exp")
            return

        # send list

        await ctx.author.send(f"List of weapons experience greater than 5% of **{name} [{id}]**:")
        for i, w in enumerate(req.get("weaponexp", [])):
            if w["exp"] == 100:
                await ctx.author.send(f'**{i+1}**   ---   **{w["name"]} ** {w["exp"]}%')
            elif w["exp"] > 4:
                await ctx.author.send(f'{i+1}   ---   **{w["name"]}** {w["exp"]}%')
        await ctx.author.send(f"done")
        return

    @commands.command(aliases=['net'])
    async def networth(self, ctx, *args):
        """DM your networth breakdown (in case you're flying)"""

        await ctx.message.delete()

        # get user key

        status, id, name, key = await self.bot.get_user_key(ctx, ctx.author, needPerm=False)
        if status < 0:
            print(f"[NETWORTH] error {status}")
            return

        # make api call

        url = f"https://api.torn.com/user/?selections=discord,networth&key={key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                req = await r.json()

        # handle API error

        if "error" in req:
            await ctx.author.send(f':x: You asked for your networth but an error occured with your API key: *{req["error"]["error"]}*')
            return

        # send list

        lst = [f"Networth breakdown of {name} [{id}]", '---']
        for k, v in req.get("networth", dict({})).items():
            if k in ['total']:
                lst.append('---')
            if int(v):
                a = f"{k}:"
                b = f"${v:,.0f}"
                lst.append(f'{a: <13}{b: >16}')

        await ctx.author.send('```YAML\n{}```'.format('\n'.join(lst)))
        return

    @commands.command()
    async def banners(self, ctx, *args):
        """Gives missing honor banners or displays banner if id given"""

        # get yata's honor dict
        url = "https://yata.alwaysdata.net/awards/bannersId"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                honorBanners = await r.json()

        # display honor banners
        if len(args):
            for id in args:
                bannerId = honorBanners.get(id)
                if bannerId is None:
                    await ctx.send("Honor **#{}**: *honor not known*".format(id))
                elif int(bannerId) == 0:
                    await ctx.send("Honor **#{}**: *banner not known*".format(id))
                else:
                    await ctx.send("Honor **#{}**: https://awardimages.torn.com/{}.png".format(id, bannerId))

        # display missing banners
        else:
            # get configuration for guild
            status, tornId, key = await self.bot.get_master_key(ctx.guild)
            if status == -1:
                await ctx.send(":x: No master key given")
                return

            # get torn's honor dict
            url = "https://api.torn.com/torn/?selections=honors&key={}".format(key)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    tornHonors = await r.json()

            # handle API error
            if 'error' in tornHonors:
                await ctx.send(f':x: Master key problem: *{tornHonors["error"]["error"]}*')
                return

            # dirtiest way to deal with API error
            tornHonors = tornHonors.get('honors', dict({}))

            # select missing honors
            honors = []
            for k, v in honorBanners.items():
                if int(v) == 0:
                    honor = tornHonors.get(k, dict({}))
                    h = " #{} **{}** *{}*".format(k, honor.get('name', 'API'), honor.get('description', 'ERROR'))
                    honors.append(h)

            message = "Missing banners:\n{}".format("\n".join(honors))

            await ctx.send(message)

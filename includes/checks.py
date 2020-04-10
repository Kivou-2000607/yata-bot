"""
Copyright 2020 kivou.2000607@gmail.com

This file is part of yata-bot.

    yata is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    any later version.

    yata is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with yata-bot. If not, see <https://www.gnu.org/licenses/>.
"""

# import standard modules
import asyncio


async def channels(ctx, allowed):
    allowed_string = " or ".join(["`#{}`".format(c) for c in allowed])

    if ctx.channel.name == "yata-admin" or "*" in allowed:
        # print("[CHECK CHANNEL] access granted in {}".format(ctx.channel.name))
        return True

    elif ctx.channel.name not in allowed:
        if None in allowed:
            msg = await ctx.send("Sorry **{}**... This channel is not made for this command. Initiate a private conversation with me for that.".format(ctx.author.display_name, allowed_string))
        else:
            msg = await ctx.send("Sorry **{}**... This channel is not made for this command. Goto {}.".format(ctx.author.display_name, allowed_string))
        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()
        return False

    else:
        # print("[CHECK CHANNEL] access granted in {}".format(ctx.message.channel.name))
        return True


async def roles(ctx, allowed):
    # test if private channel or not
    if ctx.channel.name is None or "*" in allowed:
        return True

    allowed_string = " or ".join(["`@{}`".format(c) for c in allowed])
    access = False
    for allowed_role in allowed:
        if allowed_role in [role.name for role in ctx.author.roles]:
            access = True
            # print("[CHECK ROLE] access granted for {}".format(allowed_role))
            break

    if access:
        return True

    else:
        msg = await ctx.send("Sorry **{}** but you need to be at least a **{}** to ask me that.".format(ctx.author.display_name, allowed_string))
        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()
        return False

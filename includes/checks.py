# import standard modules
import asyncio


async def channels(ctx, allowed):
    allowed_string = " or ".join(["`#{}`".format(c) for c in allowed])

    if ctx.channel.name == "yata-admin":
        # print("[CHECK CHANNEL] access granted in {}".format(ctx.channel.name))
        return True

    elif ctx.channel.name not in allowed:
        if None in allowed:
            msg = await ctx.send("Sorry **{}**... This channel is not made for this kind of requests. Initiale a private conversation with me for that.".format(ctx.author.display_name, allowed_string))
        else:
            msg = await ctx.send("Sorry **{}**... This channel is not made for this kind of requests. Got to {}.".format(ctx.author.display_name, allowed_string))
        await asyncio.sleep(10)
        await msg.delete()
        await ctx.message.delete()
        return False

    else:
        # print("[CHECK CHANNEL] access granted in {}".format(ctx.message.channel.name))
        return True


async def roles(ctx, allowed):
    # test if private channel or not
    if ctx.channel.name is None:
        return True

    allowed_string = " or ".join(["`{}`".format(c) for c in allowed])
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

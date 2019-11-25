# import standard modules
import requests
import json
import asyncio

# import discord modules
from discord.utils import get


async def member(ctx, verified_role, userID=None, discordID=None, API_KEY=""):
    """ Verifies one member
        Returns what the bot should say
    """

    # WARNING: ctx is most of the time a discord context
    # But when using this function inside on_member_join ctx is a discord member
    # Thus ctx.author will fail in this case

    # WARNING: if discordID corresponds to a userID it will be considered as a user ID

    # cast userID and discordID into in if not none
    discordID = int(discordID) if str(discordID).isdigit() else None
    userID = int(userID) if str(userID).isdigit() else None

    # check userID and discordID > 0 otherwise api call will be on the key owner
    if discordID is not None:
        discordID = None if discordID < 1 else discordID

    if userID is not None:
        userID = None if userID < 1 else userID

    # works for both ctx as a context and as a member
    guild = ctx.guild

    # boolean that check if the member is verifying himself with no id given
    author_verif = userID is None and discordID is None

    # case no userID and no discordID is given (author verify itself)
    if author_verif:
        author = ctx.author
        req = requests.get(f"https://api.torn.com/user/{author.id}?selections=discord&key={API_KEY}").json()
        if 'error' in req:
            return ":x: There is a API key problem ({}). It's not your fault... Try later.".format(req['error']['error']), False
        userID = req['discord'].get("userID")
        if userID == '':
            return f":x: **{author}** you have not been verified because you didn't register to the official Torn discord server: https://www.torn.com/discord", False

    # case discordID is given
    # if discordID is not None and userID is None:  # use this condition to skip API call if userID is given
    if discordID is not None:  # use this condition to force API call to check userID even if it is given
        req = requests.get(f"https://api.torn.com/user/{discordID}?selections=discord&key={API_KEY}").json()
        if 'error' in req:
            return ":x: There is a API key problem ({}). It's not your fault... Try again later.".format(req['error']['error']), False
        if req['discord'].get("userID") == '':
            return f":x: **{guild.get_member(discordID)}** has not been verified because he didn't register to the official Torn discord server: https://www.torn.com/discord", False
        else:
            userID = int(req['discord'].get("userID"))

    print(f"verifying userID = {userID}")

    # api call request
    req = requests.get(f"https://api.torn.com/user/{userID}?selections=profile,discord&key={API_KEY}").json()

    # check api error
    if 'error' in req:
        if int(req['error']['code']) == 6:
            return f":x: Torn ID `{userID}` is not known. Please check again.", False
        else:
            return ":x: There is a API key problem ({}). It's not your fault... Try again later.".format(req['error']['error']), False

    # check != id shouldn't append or problem in torn API
    dis = req.get("discord")
    if int(dis.get("userID")) != userID:
        return ":x: That's odd... {} != {}.".format(userID, dis.get("userID")), False

    # check if registered in torn discord
    discordID = None if dis.get("discordID") in [''] else int(dis.get("discordID"))
    name = req.get("name", "???")
    nickname = f"{name} [{userID}]"

    if discordID is None:
        # the guy did not log into torn discord
        return f":x: **{nickname}** has not been verified because he didn't register to the official Torn discord server: https://www.torn.com/discord", False

    # the guy already log in torn discord
    if author_verif:
        author = ctx.author
        try:
            await author.edit(nick=nickname)
        except BaseException:
            return f":x: **{author}**, I don't have the permission to change your nickname.", False
        await author.add_roles(verified_role)

        # Set Faction role
        faction_name = "{faction_name} [{faction_id}]".format(**req['faction'])
        faction_role = get(ctx.guild.roles, name=faction_name)
        if faction_role is not None:
            await author.add_roles(faction_role)
            return f":white_check_mark: **{author}**, you've been verified and are now kown as **{author.mention}** from *{faction_name}*. o7", True
        else:
            return f":white_check_mark: **{author}**, you've been verified and are now kown as **{author.mention}**. o/", True

    else:
        # loop over all members to check if the id exists
        for member in ctx.guild.members:
            if int(member.id) == discordID:
                try:
                    await member.edit(nick=nickname)
                except BaseException:
                    return f":x: I don't have the permission to change **{member}**'s nickname.", False
                await member.add_roles(verified_role)

                # Set Faction role
                faction_name = "{faction_name} [{faction_id}]".format(**req['faction'])
                faction_role = get(ctx.guild.roles, name=faction_name)
                if faction_role is not None:
                    await member.add_roles(faction_role)
                    return f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}** from *{faction_name}*. o7", True
                else:
                    return f":white_check_mark: **{member}**, has been verified and is now know as **{member.display_name}**. o/", True

        # if no match in this loop it means that the member is not in this server
        return f":x: You're trying to verify **{nickname}** but he didn't join this server... Maybe he is using a different discord account on the official Torn discord server.", False

    return ":x: Weird... I didn't do anything...", False

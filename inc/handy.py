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
import pytz
import datetime
import re
import traceback
import time
import textwrap

# import discord modules
import discord
from discord import Embed

my_blue = 4488859
my_red = 15544372
my_green = 4175668

# split message if needed
async def send(obj, content='', embed=None):
    def lookahead(iterable):
        """Pass through all values from the given iterable, augmented by the
        information if there are more values to come after the current one
        (True), or if it is the last value (False).
        """
        # Get an iterator and pull the first value.
        it = iter(iterable)
        last = next(it)
        # Run the iterator to exhaustion (starting from the second value).
        for val in it:
            # Report the *previous* value (more to come).
            yield last, True
            last = val
        # Report the last value.
        yield last, False


    try:
        await obj.send(content, embed=embed)
    except BaseException as e:
        if isinstance(e, discord.errors.HTTPException) and e.code == 50035:
            contents = textwrap.wrap(content, 2000)
            for i, (content, in_between) in enumerate(lookahead(contents)):

                if in_between:
                    await obj.send(content, embed=None)

                elif embed is not None:

                    # +-------------+------------------------+
                    # |    Field    |         Limit          |
                    # +-------------+------------------------+
                    # | title       | 256 characters         |
                    # | description | 2048 characters        |
                    # | fields      | Up to 25 field objects |
                    # | field.name  | 256 characters         |
                    # | field.value | 256 characters         |
                    # | footer.text | 2048 characters        |
                    # | author.name | 256 characters         |
                    # +-------------+------------------------+

                    d = embed.to_dict()
                    new_embed = Embed(title=textwrap.shorten(d.get("titled", "qsdf qsdfq sdfqsdfsdfqsdfqsdfdfqsd"), width=256),
                                      description=textwrap.shorten(d.get("description", ""), width=2048),
                                      color=d.get("color"))

                    for f in d.get("fields", []):
                        new_embed.add_field(name=textwrap.shorten(f.get("name", ""), width=256), value=textwrap.shorten(f.get("value", ""), width=256))

                    if d.get('footer', False):
                        new_embed.set_footer(text=textwrap.shorten(d["footer"].get("text", ""), width=2048))

                    if d.get('author', False):
                        new_embed.set_author(name=textwrap.shorten(d["author"].get("name", ""), width=256), url=d["author"].get("url", ""), icon_url=d["author"].get("icon_url", ""))

                    embed = new_embed if len(new_embed) < 6000 else None

                    await obj.send(content, embed=embed)

        else:
            print(f"Sending message error {e}")


def permissions_rsm(permissions):
    perm = []
    if permissions.read_messages:
        perm.append('R')
    if permissions.send_messages:
        perm.append('S')
    if permissions.manage_messages:
        perm.append('M')
    return '/'.join(perm)


def now():
    return datetime.datetime.utcnow()


def ts_now():
    return int(time.time())


def ts_format(timestamp, fmt=None):
    d = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    if fmt == "time":
        return d.strftime("%H:%M:%S TCT")
    elif fmt == "short":
        return d.strftime("%m/%d %H:%M:%S TCT")
    else:
        return d


def hide_key(error):
    for find in re.findall('key=[a-zA-Z0-9]{1,16}', f'{error}'):
        error = str(error).replace(find, "key=***")
    return str(error)


def log_fmt(error, headers=dict({}), full=False):
    eb = Embed(title="YATA bot error", description=hide_key(error), color=my_red)

    # headers
    if len(headers):
        for k, v in headers.items():
            if isinstance(v, list):
                eb.add_field(name=k, value=", ".join(v))
            else:
                eb.add_field(name=k, value=v)

    # # error message
    # if len(headers) or full:
    #     lst.append('# error message')
    # errorMSG = hide_key(error)
    # lst.append(f'{errorMSG}')

    # traceback
    if full:
        tb = "\n".join([line[:-2] for line in traceback.format_exception(type(error), error, error.__traceback__)])
        tb = hide_key(tb)
        eb.add_field(name="Full message", value=f"```{tb}```")

    return eb


def is_mention(mention, type="role"):
    if type == "role":
        return False if re.match(r'<@&([0-9])+>', mention) is None else mention[3:-1]
    elif type == "channel":
        return False if re.match(r'<#([0-9])+>', mention) is None else mention[2:-1]


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


def s_to_hms(seconds, max_hours=24):
    time = float(seconds)
    hours = int(time // 3600)
    time %= 3600
    minutes = int(time // 60)
    time %= 60
    seconds = int(time)

    return "{:02d}hrs {:02d}mins {:02d}s".format(hours, minutes, seconds)


def s_to_ms(seconds):
    time = float(seconds)
    minutes = int(time // 60)
    time %= 60
    seconds = int(time)

    return "{:02d}mins {:02d}s".format(minutes, seconds)


def s_to_hm(seconds, max_hours=24):
    time = float(seconds)
    days = int(float(seconds) // (24 * 3600))
    time %= (24 * 3600)
    hours = int(time // 3600) + 24 * days
    time %= 3600
    minutes = int(time // 60)

    str_max_hours = ">{} hours".format(max_hours)
    return "{: >9}".format(str_max_hours) if hours > max_hours else "{: >2}h {: >2}min".format(hours, minutes)

def s_to_time(seconds, max_hours=24):
    time = float(seconds)
    hours = int(time // 3600)
    time %= 3600
    minutes = int(time // 60)
    time %= 60
    seconds = int(time)

    if hours > max_hours:
        return f'more than {max_hours}h'
    else:
        ret = ''
        for k, v in {"h": hours, "m": minutes, "s": seconds}.items():
            ret += f'{v:02d}{k} ' if v else ''
        return ret if ret else '0s'

def s_to_dhm(seconds, max_days=99):
    time = float(seconds)
    days = int(float(seconds) // (24 * 3600))
    time %= (24 * 3600)
    hours = int(time // 3600)
    time %= 3600
    minutes = int(time // 60)

    str_max_days = "> {} days".format(max_days)
    return "{: >13}".format(str_max_days) if days > max_days else "{: >2}d {: >2}h {: >2}min".format(days, hours, minutes)


def ts_to_date(timestamp):
    return datetime.date.fromtimestamp(timestamp, tz=pytz.UTC)


def ts_to_datetime(timestamp, fmt=None):
    d = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    if fmt == "time":
        return d.strftime("%H:%M:%S")
    elif fmt == "short":
        return d.strftime("%m/%d %H:%M:%S")
    else:
        return d


def chat_message(d):
    time = ts_to_datetime(d.get("time"), fmt="short")
    name = d.get("senderName")
    uid = d.get("senderId")
    message = d.get("messageText")
    return '```markdown\n[{}]({} [{}]) {}\n```'.format(time, name, uid, message)


def chat_embed(d):
    eb = Embed(description=d.get("messageText"), color=my_blue)
    eb.set_author(name=f'{d.get("senderName")} [{d.get("senderId")}]', url=f'https://www.torn.com/profiles.php?XID={d.get("senderId")}')
    eb.set_footer(text=ts_format(d.get("time"), fmt="short"))
    eb.timestamp = datetime.datetime.fromtimestamp(d.get("time"), tz=pytz.UTC)
    return eb


async def send_tt(ctx, lst, limit=1800, tt=True, style="md"):
    if len(lst):
        msg = ""
        for line in lst:
            msg += line + "\n"
            if len(msg) > limit:
                if tt:
                    await ctx.send("```{}\n{}```".format(style, msg))
                else:
                    await ctx.send("{}".format(msg))
                msg = ""
        if tt:
            await ctx.send("```{}\n{}```".format(style, msg))
        else:
            await ctx.send("{}".format(msg))

def append_update(embed, timestamp, text=""):
    embed.set_footer(text=f'{text}{ts_format(timestamp, fmt="short")}')
    embed.timestamp = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    return embed

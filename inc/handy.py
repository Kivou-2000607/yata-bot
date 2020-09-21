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

# import discord modules
from discord import Embed

my_blue = 4488859
my_red = 15544372
my_green = 4175668

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
    return int(datetime.datetime.timestamp(datetime.datetime.utcnow()))


def ts_format(timestamp, fmt=None):
    d = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    if fmt == "time":
        return d.strftime("%H:%M:%S")
    elif fmt == "short":
        return d.strftime("%m/%d %H:%M:%S")
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

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

from discord import Webhook, RequestsWebhookAdapter

import requests
import asyncio
import datetime
import pytz
import json

db = json.load(open("factionspies.json", "r"))


def get_key():
    k, v = sorted(db["keys"].items(), key=lambda x: x[1]["last_used"])[0]
    v["last_used"] = int(datetime.datetime.timestamp(datetime.datetime.utcnow()))
    return v["key"]


# do a call for each factions
for faction_id, faction in db["factions"].items():
    req = requests.get(f"https://api.torn.com/faction/{faction_id}?selections=basic,timestamp&key={get_key()}")
    try:
        faction_json = req.json()
    except BaseException as e:
        faction_json = {"error": {"error": f"API error: {e}", "code": -1}}

    if "error" in faction_json:
        print(f'[Fetching faction {faction_id}] API error code {faction_json["error"]["code"]}: {faction_json["error"]["error"]}')
        continue

    now = int(faction_json["timestamp"])
    for member_id, member in sorted(faction_json["members"].items(), key=lambda x: -x[1]["last_action"]["timestamp"]):
        print(f"Member {member_id}")
        if now - member["last_action"]["timestamp"] > db.get("last_action", 120):
            print("breaking", member["name"], member["last_action"]["relative"], now, member["last_action"]["timestamp"])
            break

        # make API call on member
        req = requests.get(f"https://api.torn.com/user/{member_id}?selections=basic,personalstats,timestamp&key={get_key()}")
        try:
            member_json = req.json()
        except BaseException as e:
            member_json = {"error": {"error": f"API error: {e}", "code": -1}}

        if "error" in member_json:
            print(f'[Fetching member {member_id}] API error code {member_json["error"]["code"]}: {faction_json["error"]["error"]}')
            continue

        if member_id not in faction["members"]:
            faction["members"][member_id] = {k: 0 for k in db["records"]}

        previous_record = dict(faction["members"][member_id])
        current_record = {k: member_json["personalstats"].get(k, 0) for k in db["records"]}

        for k, curr in current_record.items():
            prev = previous_record.get(k, 0)
            if prev and curr > prev:
                d = datetime.datetime.fromtimestamp(member_json["timestamp"], tz=pytz.UTC)
                log = f'```md\n[{d.strftime("%m/%d %H:%M:%S")}]({member_json.get("name")} [{member_id}]) {curr - prev} {db["records"].get(k, k)}```'
                webhook = Webhook.partial(db["wh_id"], db["wh_token"], adapter=RequestsWebhookAdapter())
                webhook.send(log, username=f'Spying on {faction_json["name"]} [{faction_id}]')

        # save new record
        faction["members"][member_id] = current_record

    json.dump(db, open("factionspies.json", "w+"), sort_keys=True, indent=4)

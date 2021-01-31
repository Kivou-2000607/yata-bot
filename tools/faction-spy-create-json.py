#!/usr/bin/env python

import json
import argparse

# parser
parser = argparse.ArgumentParser(description='Parse options to create json file.')
parser.add_argument('--instance', type=str, help="name of the instance of the script", required=True)
parser.add_argument('--factions', nargs='*', type=int, help="list of faction ids", required=True)
parser.add_argument('--keys', nargs='*', type=str, help="list of API keys", required=True)
parser.add_argument('--webhooks', nargs='*', type=str, help="list of webhook links", required=True)
args = vars(parser.parse_args())

d = {
    "factions": {},
    "keys": {},
    "webhooks": {},
    "last_action": 120,
    "records": {
        "attacksassisted": "attacks assisted",
        "attacksdraw": "attacks draw",
        "attackslost": "attacks lost",
        "bountiescollected": "bounties collected",
        "bountiesplaced": "bounties placed",
        "bountiesreceived": "bounties received",
        "energydrinkused": "energy drink used",
        "lsdtaken": "lsd taken",
        "medicalitemsused": "medicalitems used",
        "refills": "energy refill",
        "revives": "revives made",
        "revivesreceived": "revives received",
        "xantaken": "xanax taken"
    },
}

for faction_id in args.get("factions"):
    d["factions"][str(faction_id)] = {"members": {}}

for i, key in enumerate(args.get("keys")):
    d["keys"][str(i)] = {"key": key, "last_used": 0}

for i, wh in enumerate(args.get("webhooks")):
    whsplit = wh.split("/")
    d["webhooks"][str(i)] = {"wh_id": whsplit[-2], "wh_token": whsplit[-1]}


json.dump(d, open(f'faction-spy-{args.get("instance")}.json', 'w'), sort_keys=True, indent=4)

import json

raw_json = json.load(open('elim_data.json', 'r'))

dict_json = {}
for m in raw_json:
    # dict_json[m["id"]] = {"name": m["name"]}
    dict_json[m["id"]] = {}
    for y in[2019, 2020]:
        if m[f'team_{y}']:
            # dict_json[m["id"]][y] = {k: m.get(f"{k}_{y}") for k in ["team", "attacks", "rank_team", "rank_overall"]}
            dict_json[m["id"]][y] = [m.get(f"{k}_{y}") for k in ["team", "attacks", "rank_team", "rank_overall"]]

# json.dump(dict_json, open('elim_scores.json', 'w+'), indent=4)
json.dump(dict_json, open('elim_scores.json', 'w+'))

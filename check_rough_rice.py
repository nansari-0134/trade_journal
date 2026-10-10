import json

with open('journal/cftc_markets_cache.json') as f:
    data = json.load(f)

for x in data:
    if 'ROUGH RICE' in x['name'].upper() or '039601' in x['code']:
        print(x)

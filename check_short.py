import json

with open('journal/cftc_markets_cache.json') as f:
    data = json.load(f)

# Group by short name
short_names = {}
for m in data:
    short = m['name'].split('-')[0].strip()
    short_names.setdefault(short, []).append(m)

print(f"Total unique short names: {len(short_names)}")
for s, items in list(short_names.items())[:10]:
    print(f"{s}: {len(items)} items")

# What about "unable to open report"?

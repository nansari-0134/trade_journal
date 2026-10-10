import json

with open('discovered_markets.json') as f:
    data = json.load(f)

groups = {}
for m in data:
    g = m['group']
    groups.setdefault(g, []).append(m)

for group in sorted(groups.keys()):
    items = sorted(groups[group], key=lambda x: x['name'])
    print(f"\n=== {group} ({len(items)} products) ===")
    for m in items:
        print(f"  ({repr(m['code'])}, {repr(m['name'])}),")

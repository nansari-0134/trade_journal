import json

with open('journal/cftc_markets_cache.json') as f:
    data = json.load(f)

# Find if there are multiple entries for the same name but different codes,
# or multiple entries with the exact same name AND code (which shouldn't happen based on our deduplication, but maybe they have different cases?)
names = {}
for m in data:
    names.setdefault(m['name'], []).append(m['code'])

multi = {n: codes for n, codes in names.items() if len(codes) > 1}
print(f"Names associated with multiple codes: {len(multi)}")
for i, (n, codes) in enumerate(multi.items()):
    if i < 10:
        print(f"  {n}: {codes}")

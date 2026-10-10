"""
Normalise the discovered_markets.json into the cftc_markets_cache.json format
expected by cot_service.py:
  [{"code": "...", "name": "...", "group": "..."}, ...]
"""
import json, os

src = 'discovered_markets.json'
dst = os.path.join('journal', 'cftc_markets_cache.json')

with open(src) as f:
    raw = json.load(f)

# The discovered file already has code/name/group keys.
# Deduplicate by (code, name) and normalise group to uppercase.
seen = set()
markets = []
for m in raw:
    code = (m.get('code') or '').strip()
    name = (m.get('name') or '').strip()
    group = (m.get('group') or 'OTHER').strip().upper()
    key = (code, name)
    if code and name and key not in seen:
        seen.add(key)
        markets.append({'code': code, 'name': name, 'group': group})

markets.sort(key=lambda x: (x['group'], x['name']))

with open(dst, 'w', encoding='utf-8') as f:
    json.dump(markets, f, ensure_ascii=False, indent=2)

# Summary
groups = {}
for m in markets:
    groups[m['group']] = groups.get(m['group'], 0) + 1

print(f"Wrote {len(markets)} unique entries to {dst}")
for g, c in sorted(groups.items()):
    print(f"  {g}: {c}")

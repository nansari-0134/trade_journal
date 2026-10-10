import requests
import json

CFTC_API_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

def discover_markets():
    # Fetch distinct market codes and names for legacy futures
    # We use $select and $group to get unique combinations
    params = {
        '$select': 'cftc_contract_market_code, market_and_exchange_names, commodity_group_name',
        '$where': "futonly_or_combined='FutOnly'",
        '$group': 'cftc_contract_market_code, market_and_exchange_names, commodity_group_name',
        '$limit': 5000
    }
    
    print("Fetching available markets from CFTC...")
    try:
        resp = requests.get(CFTC_API_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        print(f"Found {len(data)} markets.")
        
        # Format for display or further use
        markets = []
        for d in data:
            markets.append({
                'code': d.get('cftc_contract_market_code'),
                'name': d.get('market_and_exchange_names'),
                'group': d.get('commodity_group_name', 'Other')
            })
            
        # Sort by group then name
        markets.sort(key=lambda x: (x['group'], x['name']))
        
        with open('c:/Users/nizam.ansari/.gemini/antigravity/scratch/trade_journal/discovered_markets.json', 'w') as f:
            json.dump(markets, f, indent=2)
            
        print("Summary of groups:")
        groups = {}
        for m in markets:
            g = m['group']
            groups[g] = groups.get(g, 0) + 1
            
        for g, count in sorted(groups.items()):
            print(f"- {g}: {count} products")
            
        print("\nResults saved to discovered_markets.json")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    discover_markets()

"""
Utility functions for reading product reference data from Products.xlsx.
All trade CRUD is handled by the Django ORM via services.py.
"""
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PRODUCTS_FILE = os.path.join(BASE_DIR, 'Products.xlsx')

# Month code mapping for futures contract months
MONTH_CODES = {
    1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
    7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z',
}
MONTH_NAMES = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]


def get_products_data() -> dict:
    """
    Read the Products.xlsx file and return a dict keyed by product symbol.
    Each value is a dict with keys: group, tc_pre, tc_post.
    """
    if not os.path.exists(PRODUCTS_FILE):
        return {}

    try:
        df = pd.read_excel(PRODUCTS_FILE)
        df = df.dropna(subset=['Product'])

        products = {}
        for _, row in df.iterrows():
            symbol = str(row['Product']).strip()
            products[symbol] = {
                'group': str(row.get('ProductGroup', 'Unknown')).strip(),
                'tc_pre': float(row['TC_PreRebate']) if pd.notna(row.get('TC_PreRebate')) else 0.0,
                'tc_post': float(row['TC_PostRebate']) if pd.notna(row.get('TC_PostRebate')) else 0.0,
                'name': str(row.get('Name', '')) if pd.notna(row.get('Name')) else '',
                'currency': str(row.get('Currency', 'USD')) if pd.notna(row.get('Currency')) else 'USD',
                'exchange': str(row.get('Exchange', '')) if pd.notna(row.get('Exchange')) else '',
                'tick_value': float(row['TickValue']) if pd.notna(row.get('TickValue')) else 1.0,
                'tick_size': float(row['TickSize']) if pd.notna(row.get('TickSize')) else 0.01,
                'point_value': float(row['PointValue']) if pd.notna(row.get('PointValue')) else 0.0,
                'fx_rate': float(row['FXRate']) if pd.notna(row.get('FXRate')) else 1.0,
                'display_factor': float(row['DisplayFactor']) if pd.notna(row.get('DisplayFactor')) else 1.0,
            }
        return products
    except Exception as e:
        print(f"Error reading Products.xlsx: {e}")
        return {}


def get_product_groups() -> dict:
    """Return {group_name: [sorted list of symbols]}."""
    products = get_products_data()
    groups: dict[str, list[str]] = {}
    for symbol, data in products.items():
        grp = data['group']
        groups.setdefault(grp, [])
        if symbol not in groups[grp]:
            groups[grp].append(symbol)

    return {k: sorted(v) for k, v in sorted(groups.items())}


def get_product_list() -> list[dict]:
    """Return a flat list of product dicts for JSON serialization."""
    products = get_products_data()
    return [
        {'symbol': sym, 'group': info['group'], 'tc_pre': info['tc_pre'], 'tc_post': info['tc_post']}
        for sym, info in sorted(products.items(), key=lambda x: (x[1]['group'], x[0]))
    ]


def get_contract_months(years_ahead: int = 3) -> list[str]:
    """
    Generate a list of contract month strings for the next N years.
    Format: 'MonthName Year' (e.g., 'Jan 2026')
    """
    from datetime import datetime
    current_year = datetime.now().year
    months = []
    for year in range(current_year, current_year + years_ahead):
        for month_name in MONTH_NAMES:
            months.append(f"{month_name} {year}")
    return months

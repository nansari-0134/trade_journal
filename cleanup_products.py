import pandas as pd

products_file = 'Products.xlsx'
df = pd.read_excel(products_file)

# Keep only the columns we want
final_cols = ['ProductGroup', 'Product', 'TC_PreRebate', 'TC_PostRebate', 'Rebate']
# Map the _y columns to their clean names
mapping = {
    'Name_y': 'Name',
    'Currency_y': 'Currency',
    'Exchange_y': 'Exchange',
    'TickValue_y': 'TickValue',
    'TickSize_y': 'TickSize',
    'PointValue_y': 'PointValue',
    'FXRate_y': 'FXRate',
    'DisplayFactor_y': 'DisplayFactor'
}

for old, new in mapping.items():
    if old in df.columns:
        df[new] = df[old]

# Drop any columns that are not in final_cols + the new clean names
keep = final_cols + list(mapping.values())
df = df[keep]

df.to_excel(products_file, index=False)
print("Cleaned up Products.xlsx")
print(df.columns.tolist())

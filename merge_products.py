import pandas as pd
import os

downloads_file = r'C:\Users\nizam.ansari\Downloads\product_details.xlsx'
products_file = r'c:\Users\nizam.ansari\.gemini\antigravity\scratch\trade_journal\Products.xlsx'

df_details = pd.read_excel(downloads_file)
df_products = pd.read_excel(products_file)

# Select relevant columns from details
details_subset = df_details[['ttProductCode', 'hgProductName', 'currency', 'hgExchange', 'tickValue', 'tickSize', 'pointValue', 'fxRate', 'displayFactor']].copy()
details_subset.columns = ['Product', 'Name', 'Currency', 'Exchange', 'TickValue', 'TickSize', 'PointValue', 'FXRate', 'DisplayFactor']

# Drop duplicates in details (sometimes there are multiple rows for same code)
details_subset = details_subset.drop_duplicates(subset=['Product'])

# Merge
merged = pd.merge(df_products, details_subset, on='Product', how='left')

# Save updated Products.xlsx
merged.to_excel(products_file, index=False)
print("Merged and saved Products.xlsx")
print(merged.head())

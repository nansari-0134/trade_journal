# Fee Modeling & Multipliers

In high-frequency commodity spread and butterfly trading, execution fees can account for a significant percentage of total gross profit. Trade Journal accounts for both **Gross PnL** and **Net Realized PnL** after broker/exchange fees.

---

## 1. Pre-Rebate vs. Post-Rebate Fees

Brokers and clearing members receive fee rebates based on monthly trading volume or exchange membership status:

- **`TC_PreRebate` (Pre-Rebate Transaction Cost)**: The standard rack-rate exchange and regulatory fee per contract charged to non-member participants.
- **`TC_PostRebate` (Post-Rebate Transaction Cost)**: The actual net cost per contract after volume rebates, exchange membership discounts, or clearing concessions are applied.

Both columns are stored in `Products.xlsx`:

```
Product | TC_PreRebate | TC_PostRebate
CL      | 2.50         | 1.25
FCPO    | 4.00         | 2.10
ES      | 1.85         | 1.15
```

---

## 2. Multi-Leg Fee Scaling

When trading a multi-leg strategy (e.g., Butterfly `1MF` with ratio `[1, -2, 1]`), entering **1 unit** of the strategy actually executes **4 contracts** in the market:

- Leg 1: 1 contract
- Leg 2: 2 contracts
- Leg 3: 1 contract

The transaction fee formula reflects this full execution weight:

$$\text{Trade Fee} = \sum_{l \in \text{legs}} \left( \text{TC\_PostRebate}_l \times |\text{Trade Size}| \times |\text{Leg Ratio}_l| \right)$$

For 10 units of a 1MF Crude Oil butterfly ($10 \times 4 = 40$ contracts total):
$$\text{Fee} = 1.25 \times 10 \times (1 + 2 + 1) = \$50.00$$

---

## 3. FX Translation to USD

For products denominated in foreign currencies (e.g., `FCPO` in Malaysian Ringgit `MYR`, Milling Wheat `EBM` in Euros `EUR`):
- `FXRate` in `Products.xlsx` establishes the conversion multiplier to base currency (USD).
- Gross PnL, Net PnL, and transaction fees are converted into USD terms for consistent portfolio-wide accounting.

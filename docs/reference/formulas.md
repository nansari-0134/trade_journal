# Multiplier & PnL Formulas

This reference specifies the exact mathematical formulas used across the Trade Journal calculation engine in `journal/services.py`.

---

## 1. Contract Multiplier Resolution

Commodity contracts express price in different conventions (e.g., dollars per barrel, cents per bushel, points per index). To convert price spread differences into cash values, the service layer computes:

$$\text{Multiplier} = \left(\frac{\text{PointValue}}{\text{DisplayFactor}}\right) \times \text{FXRate}$$

If `PointValue` is not defined, it defaults to:

$$\text{Multiplier} = \left(\frac{\text{TickValue}}{\text{TickSize}}\right) \times \text{FXRate}$$

### Examples:
- **WTI Crude (`CL`)**: $\text{PointValue} = 1000$, $\text{DisplayFactor} = 1.0$, $\text{FXRate} = 1.0 \implies \mathbf{1000.0}$
- **E-mini S&P (`ES`)**: $\text{PointValue} = 50.0$, $\text{DisplayFactor} = 1.0 \implies \mathbf{50.0}$
- **Corn (`ZC`)**: $50 \text{ bushels/contract}$ quoted in cents: $\text{Multiplier} = \left(\frac{5000}{100}\right) = \mathbf{50.0}$

---

## 2. Weighted Average Entry Price

When scaling into an existing trade ticket through multiple `Open` and `Add` adjustments:

$$\bar{P}_{\text{entry}} = \frac{\sum_{i \in \{\text{Open}, \text{Add}\}} (|S_i| \times P_i)}{\sum_{i \in \{\text{Open}, \text{Add}\}} |S_i|}$$

Where:
- $|S_i|$ is the absolute volume of contracts entered in adjustment $i$.
- $P_i$ is the executed price of adjustment $i$.

---

## 3. Realized PnL Calculation

For every `Reduce` or `Close` adjustment:

**Long Trades:**
$$\text{PnL} = (P_{\text{exit}} - \bar{P}_{\text{entry}}) \times \text{Multiplier} \times Q_{\text{exit}}$$

**Short Trades:**
$$\text{PnL} = (\bar{P}_{\text{entry}} - P_{\text{exit}}) \times \text{Multiplier} \times Q_{\text{exit}}$$

---

## 4. Net PnL (After Transaction Costs)

$$\text{Net PnL} = \text{Realized PnL} - \sum_{l \in \text{legs}} \left( \text{TC\_PostRebate}_l \times Q_{\text{exit}} \times |\text{Ratio}_l| \right)$$

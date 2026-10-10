# Executive Dashboard

The **Dashboard** (`/`) is the central control tower of the Trade Journal, delivering a bird's-eye view of your account performance, open risk exposures, and recent closed trade summaries.

![Executive Dashboard](../assets/images/dashboard.png)

---

## 1. Key Performance Metrics (KPIs)

At the top of the dashboard, real-time summary cards reflect aggregate trading performance:

| KPI Card | Formula / Definition | Significance |
| :--- | :--- | :--- |
| **Total Realized PnL** | $\sum \text{Realized PnL from Closed / Reduced Trades}$ | Net dollar performance across all completed executions. |
| **Win Rate** | $\left(\frac{\text{Winning Trades}}{\text{Total Closed Trades}}\right) \times 100$ | Percentage of closed trades that resulted in positive net PnL. |
| **Win / Loss Ratio** | $\frac{\text{Average Dollar Win}}{\text{Average Dollar Loss}}$ | Profit factor measuring payout asymmetry. |
| **Open Positions** | $\text{Count of trades where Status} \in [\text{'Open'}, \text{'PartiallyReduced'}]$ | Live active exposures currently requiring monitoring. |
| **Fees & Commissions** | $\sum \text{Post-Rebate Transaction Costs}$ | Total execution costs deducted across all trades. |

---

## 2. Cumulative Net Equity Curve

The interactive **Equity Curve** chart is generated dynamically via **Chart.js**:

- **Time-Series Tracking**: Every `PositionAdjustment` event (`Reduce` or `Close`) that generates realized PnL adds a point to the time axis.
- **Transaction Cost Netting**: The curve tracks **Net PnL**, automatically subtracting each contract's transaction fee (`TC_PostRebate`) scaled by leg ratios:
  $$\text{Adjustment Net PnL} = \text{Gross Realized PnL} - \sum_{\text{legs}} \left( \text{TC\_PostRebate} \times |\text{Size}| \times |\text{Ratio}| \right)$$
- **Interactive Tooltips**: Hover over data points to inspect date, trade title, and cumulative balance.

---

## 3. Privacy Mode Toggle 👁️

For traders who present their setups, record educational content, or stream their screens, the Trade Journal includes a built-in **Privacy Mode**:

- **One-Click Activation**: Click the eye icon (`#privacyToggle`) in the top navigation bar.
- **Instant CSS Masking**: Applies a Gaussian blur (`filter: blur(6px)`) and disables text selection on all `.sensitive-value` elements.
- **Persistence**: Remembers your privacy preference across page navigations using local storage.

---

## 4. Open Positions & Closed Summaries Tables

- **Open Positions Table**: Displays current open size, volume-weighted entry price, unrealized PnL estimate, and quick action buttons to adjust or close.
- **Closed Trades Log**: Displays completion dates, gross realized PnL, target PnL, and net payout after exchange fee deduction.

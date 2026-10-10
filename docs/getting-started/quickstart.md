# Quickstart Walkthrough

Follow this step-by-step walkthrough to record your first trade, monitor it on the dashboard, scale position size, and examine COT positioning.

---

## 1. Navigating the Interface

Once the server is running, the left sidebar provides access to every module:

- ➕ **Plus Button**: Instant New Trade execution modal.
- 📊 **Dashboard**: High-level KPIs, open positions, and net equity curve.
- 🧾 **Trades**: Detailed trade log, realized PnL, and position adjustment inspector.
- 📅 **Calendar**: Visual calendar of execution days and planned setups.
- 🏷️ **Product Fees**: Contract specs, tick sizes, point values, and exchange fees.
- 📊 **COT Report**: CFTC Commitments of Traders data and speculator curves.
- 🍃 **Palm Oil**: Crude Palm Oil forward curve, MPOB balance sheets, and surveyor exports.
- 🗂️ **Strategies**: Template ratio builder and inter-product pairs manager.

![Dashboard Preview](../assets/images/dashboard.png)

---

## 2. Entering Your First Trade

Click the **"+" button** in the top left or navigate to `/trades/new/`:

![New Trade Form](../assets/images/trade_new.png)

### Step-by-Step Entry:
1. **Trade Type**: Choose **Outright**, **Calendar Spread**, **Butterfly**, or **Inter-Product Spread**.
2. **Strategy Template**: If selecting a spread or fly, choose a preconfigured template (e.g., `1MS` for front-month vs. second-month spread) to automatically set leg ratios.
3. **Product & Legs**:
   - For an outright: Select symbol (e.g., `CL - Crude Oil`) and contract month (e.g., `Jun 2026`).
   - For a calendar spread: Select contract months for Leg 1 (Buy) and Leg 2 (Sell).
4. **Position Size & Price**: Enter contract quantity and initial fill price.
5. **Psychology & Thesis**: Record your entering emotion (`Confident`, `Aggressive`, `Fear`, etc.) and tag analysis sources (`Seasonality`, `Price action`, `Fundamentals`).
6. **Save**: Click **Submit Trade**.

---

## 3. Scaling & Adjusting Positions

Positions are managed dynamically from the **Trades** screen (`/trades/`):

![Trades Log](../assets/images/trades.png)

To adjust an open trade:
1. Locate the trade in the **Open Positions** section.
2. Click the **Adjust** button:
   - **Add**: Scale into the position by adding lots at a new price level. The platform automatically computes the new volume-weighted average entry price.
   - **Reduce**: Partially close a portion of the open contracts. Realized PnL is computed and locked in immediately for those contracts.
   - **Close**: Liquidate all remaining contracts. The trade is marked `Closed`, and final Net PnL is attributed to your cumulative performance curve.

---

## 4. Exploring Market Intelligence

Check CFTC positioning before entering futures positions by navigating to `/cot/`:

![COT Report](../assets/images/cot_report.png)

1. Select your commodity market (e.g., *Corn*, *WTI Crude Oil*, *Live Cattle*, *Sugar*).
2. The interactive chart will render:
   - **Total Open Interest**
   - **Commercial Hedgers** (Net Long vs. Net Short)
   - **Non-Commercial Speculators** (Managed money positioning trends)
3. Click **Sync Markets** to query the latest updates directly from the CFTC database.

# Trade Journal 📈

An **institutional-grade Commodity & Futures Trading Journal, Multi-Leg Strategy Manager, and Fundamental Market Intelligence Platform**.

Designed specifically for professional commodity traders, quant analysts, and futures prop traders who trade outrights, calendar spreads, flies, and inter-product spreads across global derivatives exchanges (CME, CBOT, NYMEX, ICE, Euronext, and BMD).

---

## 🌟 Key Highlights

- **Multi-Leg Derivative Strategies**: Native execution and ratio tracking for Outrights, Calendar Spreads (e.g., `CL 1MS`), Butterflies (`1MF [1, -2, 1]`), Double Flies (`[1, -3, 3, -1]`), Inter-Product Spreads (`CL` vs `BZ`), and Spread-vs-Spread.
- **Event-Sourced Position Auditing**: Rather than simple static records, trade position sizing is tracked via immutable `PositionAdjustment` events (`Open`, `Add`, `Reduce`, `Close`). Supports scaling in, partial exits, and accurate volume-weighted average entry prices.
- **Institutional Fee & Multiplier Modeling**: Reads contract specifications, tick sizes, point values, display factors, and FX rates from `Products.xlsx`. Accurately calculates cash PnL and models Pre-Rebate vs. Post-Rebate exchange/broker transaction costs.
- **CFTC Commitments of Traders (COT)**: Direct integration with US CFTC API (`publicreporting.cftc.gov`) with automated market discovery and caching for over 1,300+ markets across Agriculture, Energy, Metals, Currencies, and Financials.
- **Palm Oil (FCPO) Fundamentals**: Dedicated dashboard for Bursa Malaysia Derivatives (BMD) Crude Palm Oil featuring forward price curves, Malaysian Palm Oil Board (MPOB) statistics, and high-frequency surveyor export estimates (SGS, ITS, AmSpec).
- **Interactive Calendar & Trade Planning**: Schedule setups across recurring cycles (`Once`, `Monthly`, `Yearly`, `Specific Months`) with chart screenshots and an interactive monthly activity calendar.
- **Executive Dark UI with Privacy Mode**: Glassmorphism dark-mode interface built with Bootstrap 5 and Chart.js, featuring one-click privacy toggle to blur sensitive monetary balances during presentations or streaming.

---

## 🏗️ Project Architecture

```
trade_journal/
├── config/                  # Django project settings & URL routing
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── journal/                 # Core trade journal application
│   ├── models.py            # Relational models (Trades, Legs, Adjustments, COT, FCPO)
│   ├── services.py          # Domain service layer (PnL, Multipliers, State recalculation)
│   ├── views.py             # HTTP request handlers & view logic
│   ├── urls.py              # Application endpoints & JSON APIs
│   ├── cot_service.py       # CFTC API ingestion & caching service
│   ├── utils.py             # Contract calendar generator & Products.xlsx parser
│   └── templates/journal/   # UI templates (Dashboard, Trades, COT, Palm Oil, Calendar)
├── Products.xlsx            # Master product reference sheet (ticks, values, fees, FX)
├── cftc_markets_cache.json  # Cached metadata for 1,300+ CFTC markets
├── manage.py                # Django CLI entrypoint
└── requirements.txt         # Project dependencies
```

---

## 📊 Core Modules

### 1. Multi-Leg Trade Life Cycle & Accounting

- **Weighted Average Entry**: Accurately handles progressive scale-ins (`Add` actions) across varying price levels.
- **Cash PnL Calculation**: Scales price ticks by each product's contractual multiplier:
  $$\text{Multiplier} = \left(\frac{\text{PointValue}}{\text{DisplayFactor}}\right) \times \text{FXRate}$$
- **Transaction Costs**: Calculates gross and net realized PnL, factoring in pre-rebate exchange fees and post-rebate execution costs.

### 2. CFTC Commitments of Traders (COT)

- Ingests weekly legacy futures reports.
- Categorizes positions across:
  - **Commercial (Hedgers)**: Producer/Merchant/Processor/User & Swap Dealers
  - **Non-Commercial (Speculators)**: Managed Money & Other Reportables
  - **Non-Reportable**: Small retail traders
- Tracks historical changes in Net Positions and Total Open Interest.

### 3. Crude Palm Oil (FCPO) Fundamental Intelligence

- Forward price curves and open interest by contract month.
- Monthly MPOB balance sheets (Production, Imports, Exports, Local Disappearance, Ending Stocks).
- 10-day, 15-day, 20-day, and full-month surveyor export numbers.

---

## 🚀 Quick Start Guide

### 1. Prerequisites

- Python 3.10 or higher
- Git

### 2. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/nansari-0134/trade_journal.git
cd trade_journal

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Initialization

```bash
# Run migrations
python manage.py migrate

# (Optional) Create superuser for admin panel access
python manage.py createsuperuser
```

### 4. Run the Development Server

```bash
python manage.py runserver 127.0.0.1:8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.

---

## ⚙️ Configuration & Reference Data

### Adding Products

All product contract sizes, currencies, exchanges, and fee schedules are maintained in [`Products.xlsx`](Products.xlsx). The columns include:

- `Product`: Contract symbol (e.g., `CL`, `FCPO`, `ZS`, `ES`)
- `ProductGroup`: Commodity sector (Energy, Agriculture, Equity Indices, etc.)
- `Exchange`: NYMEX, CBOT, CME, ICE, Euronext, BMD
- `TickSize` & `TickValue`: Minimum price fluctuation and its cash value
- `PointValue` & `DisplayFactor`: Multiplier scaling factors
- `FXRate`: Currency translation to USD
- `TC_PreRebate` & `TC_PostRebate`: Transaction costs per contract

### Strategy Templates

Define common strategy structures in `/strategies/` or seed via `StrategyTemplate` models (e.g., calendar spreads, 3-leg flies, double-flies).

---

## 🗺️ Roadmap

- [ ] Comprehensive documentation with MkDocs & Material theme
- [ ] Integration with live WebSocket/REST market data feeds
- [ ] Exportable tax and performance reports (PDF/Excel)
- [ ] Advanced curve seasonality overlays

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

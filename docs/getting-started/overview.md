# Overview & Architecture

Trade Journal is built with a decoupled, service-oriented architecture inside Django. Rather than placing business logic directly into HTTP request handlers (views), all operations are orchestrated through a dedicated service layer.

---

## Technical Stack

- **Backend Framework**: [Django 5.2](https://www.djangoproject.com/)
- **Programming Language**: [Python 3.10+](https://www.python.org/)
- **Data Persistence**: SQLite (expandable to PostgreSQL via `DATABASE_URL`)
- **Data Analysis & Reference Parsing**: [Pandas](https://pandas.pydata.org/) & [OpenPyXL](https://openpyxl.readthedocs.io/)
- **External API Ingestion**: [Requests](https://requests.readthedocs.io/) with CFTC Socrata endpoint integration
- **Frontend Layer**: Vanilla HTML5/CSS3, [Bootstrap 5.3](https://getbootstrap.com/), [FontAwesome 6](https://fontawesome.com/), and [Chart.js](https://www.chartjs.org/)

---

## Directory Organization

```
trade_journal/
├── config/                  # Django project root configuration
│   ├── settings.py          # Application settings & middleware
│   ├── urls.py              # Root routing table
│   └── wsgi.py              # WSGI server entry point
├── journal/                 # Core domain application
│   ├── models.py            # Relational database models
│   ├── services.py          # Business logic & atomic financial calculations
│   ├── views.py             # View controllers and JSON endpoints
│   ├── urls.py              # Sub-application routes
│   ├── cot_service.py       # CFTC API ingestion & caching service
│   ├── utils.py             # Reference data loaders (Products.xlsx)
│   ├── management/commands/ # Data seeders & maintenance CLI commands
│   └── templates/journal/   # Jinja2 / Django dark-mode templates
├── docs/                    # MkDocs documentation source
├── Products.xlsx            # Master product reference sheet
├── cftc_markets_cache.json  # Cached metadata for 1,300+ CFTC markets
├── manage.py                # Django CLI management executable
├── requirements.txt         # Production and development dependencies
└── mkdocs.yml               # MkDocs configuration
```

---

## Key Design Principles

### 1. Service Layer Pattern
All financial state transitions (opening positions, scaling in, reducing, and closing) reside in `journal/services.py`. All database mutations are wrapped inside `@transaction.atomic` blocks to guarantee consistency:

```python
@transaction.atomic
def open_trade(trade_type, direction, legs, size, price, ...):
    # 1. Create master trade record
    # 2. Expand inter-product pairs if needed
    # 3. Create constituent TradeLeg instances
    # 4. Record initial 'Open' PositionAdjustment
    ...
```

### 2. Event Sourced Position Lifecycle
Positions are never modified via destructively overwriting size fields. Every state change produces an immutable `PositionAdjustment` record. This allows:
- Volume-weighted average entry price recalculation.
- Historical auditability of execution dates, slippage, and prices.
- Dynamic recalculation of realized PnL across sequential trade reductions.

### 3. Dynamic Product Multiplier Resolution
Contracts trade in disparate units (e.g., Crude Oil in barrels, Corn in bushels, Palm Oil in metric tonnes). The system resolves the cash conversion multiplier on the fly:

$$\text{Multiplier} = \left(\frac{\text{PointValue}}{\text{DisplayFactor}}\right) \times \text{FXRate}$$

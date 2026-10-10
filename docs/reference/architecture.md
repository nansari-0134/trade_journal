# Relational Models & Schemas

The Trade Journal data layer is modeled using Django's Object-Relational Mapping (ORM).

---

## 1. Entity-Relationship Overview

```mermaid
erDiagram
    TRADE ||--|{ TRADE_LEG : "contains"
    TRADE ||--|{ POSITION_ADJUSTMENT : "audited by"
    STRATEGY_TEMPLATE ||--o{ TRADE : "templates"
    
    TRADE {
        UUID id PK
        string trade_type
        string direction
        string status
        string strategy_label
        date trade_date
        time trade_time
        json analysis
        string emotion
        float market_price
        float stoploss
        float target
    }
    
    TRADE_LEG {
        UUID id PK
        UUID trade_id FK
        string product
        string contract_month
        string direction
        float ratio
    }
    
    POSITION_ADJUSTMENT {
        UUID id PK
        UUID trade_id FK
        datetime timestamp
        string action
        float size_change
        float price
        float pnl
    }
    
    STRATEGY_TEMPLATE {
        UUID id PK
        string name
        string category
        json leg_ratios
        int usage_count
    }
    
    INTER_PRODUCT_PAIR {
        UUID id PK
        string name
        string product_1
        string product_2
    }
```

---

## 2. Model Definitions

### `Trade`
The root parent model representing a trade ticket. Holds directional stance (`Long`, `Short`), status (`Open`, `PartiallyReduced`, `Closed`), psychology metadata, and targets.

### `TradeLeg`
Represents an individual leg inside a multi-leg trade. Contains the product symbol, contract expiration month (e.g., `Jun 2026`), leg direction (`Buy` or `Sell`), and ratio multiplier.

### `PositionAdjustment`
The audit trail event record. Every mutation (`Open`, `Add`, `Reduce`, `Close`) creates a timestamped record storing `size_change`, `price`, and calculated `pnl`.

### `CotReport`
Local cache of US CFTC Commitments of Traders data. Indexed by `(report_date, market_code)` to prevent duplication.

### `PalmOilPriceAndOI`, `MPOBData`, `ExportSurveyorData`
Specialized physical commodity fundamental tables storing forward prices, open interest curves, MPOB balance sheets, and cargo surveyor export estimates.

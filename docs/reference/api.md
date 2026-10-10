# Trading Bot REST API Reference

The Trade Journal exposes a RESTful JSON API designed for automated trading bots, algorithmic execution systems, and external webhook integrations.

---

## 1. Authentication & Headers

By default, local API requests require **zero authentication** to facilitate friction-free local bot development.

If remote security is desired, configure an API key in your environment:
```bash
export TRADE_JOURNAL_API_KEY="your-secret-api-token"
```

When enabled, bots must include the token in either header:
```http
X-API-Key: your-secret-api-token
# Or standard Bearer token:
Authorization: Bearer your-secret-api-token
```

All `POST`, `PUT`, `PATCH`, and `DELETE` requests use `Content-Type: application/json`. CSRF protection is exempted on bot API routes.

---

## 2. API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/trades/` | List and filter trade entries |
| `POST` | `/api/trades/` | Open a new trade entry (Outright or Multi-Leg) |
| `GET` | `/api/trades/{trade_id}/` | Get full trade state with position adjustment audit log |
| `PATCH` | `/api/trades/{trade_id}/` | Update mutable trade metadata (targets, stops, notes) |
| `POST` | `/api/trades/{trade_id}/adjust/` | Scale into position (`Add`), take profit (`Reduce`), or `Close` |
| `DELETE` | `/api/trades/{trade_id}/` | Delete trade and cascaded legs/adjustments |

---

## 3. Creating a Trade (`POST /api/trades/`)

### A. Single-Leg / Outright Trade (Shorthand)
```json
{
  "account": "Apex 50K #1",
  "trade_type": "Outright",
  "direction": "Long",
  "size": 2.0,
  "price": 71.50,
  "product": "CL",
  "contract_month": "Apr 2026",
  "strategy_label": "Bot Breakout CL",
  "stoploss": 70.00,
  "target": 74.00,
  "notes": "Automated signal from 15m RSI breakout"
}
```

### B. Multi-Leg Strategy (Calendar Spread, Butterfly, etc.)
```json
{
  "account": "Apex 50K #1",
  "trade_type": "CalendarSpread",
  "direction": "Long",
  "size": 3.0,
  "price": 0.45,
  "strategy_label": "CL 1MS Apr/May Spread",
  "legs": [
    {
      "product": "CL",
      "contract_month": "Apr 2026",
      "direction": "Buy",
      "ratio": 1.0
    },
    {
      "product": "CL",
      "contract_month": "May 2026",
      "direction": "Sell",
      "ratio": 1.0
    }
  ]
}
```

### Response (`201 Created`)
```json
{
  "success": true,
  "message": "Trade opened successfully.",
  "trade": {
    "id": "59284614-1199-45d9-9337-5cb40bc4f75d",
    "account": {
      "id": "c7a8...",
      "name": "Apex 50K #1",
      "currency": "USD"
    },
    "trade_type": "Outright",
    "direction": "Long",
    "status": "Open",
    "strategy_label": "Bot Breakout CL",
    "open_size": 2.0,
    "avg_entry_price": 71.50,
    "market_price": null,
    "stoploss": 70.0,
    "target": 74.0,
    "realized_pnl": 0.0,
    "unrealized_pnl": 0.0,
    "net_pnl": -3.48,
    "fees": {
      "commission_pre_rebate": 3.48,
      "fees_post_rebate": 3.48,
      "rebate": 0.0
    },
    "legs": [
      {
        "product": "CL",
        "contract_month": "Apr 2026",
        "direction": "Buy",
        "ratio": 1.0
      }
    ],
    "created_at": "2026-10-10T17:48:10Z"
  }
}
```

---

## 4. Querying Trades (`GET /api/trades/`)

Supports the following URL query parameters:
- `?status=Open` (or `PartiallyReduced`, `Closed`)
- `?account=Apex 50K #1` (matches name or UUID)
- `?direction=Long` (or `Short`)
- `?product=CL` (matches trades containing this product leg)
- `?trade_type=CalendarSpread`
- `?limit=50&offset=0` (pagination)

```bash
curl -X GET "http://127.0.0.1:8000/api/trades/?status=Open&product=CL"
```

---

## 5. Position Adjustments (`POST /api/trades/{trade_id}/adjust/`)

Used by bots to scale into an existing position, take partial profits, or close out.

### Scale In (`Add`)
```json
{
  "action": "Add",
  "size": 1.0,
  "price": 72.00,
  "notes": "Pyramid add on confirmation"
}
```

### Partial Profit / Scale Out (`Reduce`)
```json
{
  "action": "Reduce",
  "size": 1.0,
  "price": 74.00,
  "notes": "Take profit on 50% size"
}
```

### Full Liquidation (`Close`)
```json
{
  "action": "Close",
  "price": 74.50,
  "notes": "Target hit"
}
```

---

## 6. Python Bot Example (`requests`)

```python
import requests

BASE_URL = "http://127.0.0.1:8000/api/trades"
HEADERS = {"Content-Type": "application/json"}

# 1. Bot sends new trade
order = {
    "account": "Apex 50K #1",
    "trade_type": "Outright",
    "direction": "Long",
    "size": 2.0,
    "price": 71.25,
    "product": "CL",
    "contract_month": "Apr 2026",
    "strategy_label": "Bot Alpha Momentum",
    "stoploss": 70.25,
    "target": 73.50,
}
resp = requests.post(f"{BASE_URL}/", json=order, headers=HEADERS)
trade_id = resp.json()["trade"]["id"]
print("Created trade:", trade_id)

# 2. Scale-out 1 contract at profit target
requests.post(f"{BASE_URL}/{trade_id}/adjust/", json={
    "action": "Reduce",
    "size": 1.0,
    "price": 72.75,
    "notes": "Partial profit booked"
}, headers=HEADERS)

# 3. Close remaining contracts on trend reversal
requests.post(f"{BASE_URL}/{trade_id}/adjust/", json={
    "action": "Close",
    "price": 73.10,
    "notes": "Final exit"
}, headers=HEADERS)
```

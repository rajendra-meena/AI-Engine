# MarketMind AI — Broker Integration Guide

## Architecture

Brokers are implemented using the **Adapter Pattern**. Each broker has its own adapter class that implements the `BaseBroker` interface.

```
┌──────────────────┐
│   Trading App     │
└────────┬─────────┘
         │
┌────────▼─────────┐
│   BaseBroker      │  ← Abstract interface
│   (ABC)           │
└────────┬─────────┘
         │
    ┌────┼────┬────┬────┬────┐
    ▼    ▼    ▼    ▼    ▼    ▼
  ZD   ANG   FY   UP   DH   ...
```

## Adding a New Broker

### 1. Implement the Interface

Create a new file in `backend/broker/adapters/`:

```python
from ..base import BaseBroker, BrokerOrder, BrokerPosition, BrokerHolding, BrokerFunds, BrokerOrderStatus

class MyBroker(BaseBroker):
    def __init__(self, api_key: str = "", secret: str = ""):
        self.api_key = api_key
        self.secret = secret

    async def connect(self) -> bool:
        # Implement connection logic
        return True

    async def place_order(self, order: BrokerOrder) -> BrokerOrder:
        # Implement order placement
        return order

    # ... implement all other methods
```

### 2. Register the Adapter

Add to `backend/broker/adapters/__init__.py`:
```python
from .mybroker import MyBroker
```

### 3. Required Methods

Every broker adapter must implement:

| Method | Returns | Description |
|--------|---------|-------------|
| `connect()` | bool | Establish API connection |
| `login()` | bool | Authenticate session |
| `logout()` | bool | End session |
| `place_order(order)` | BrokerOrder | Place new order |
| `modify_order(id, order)` | BrokerOrder | Modify existing order |
| `cancel_order(id)` | bool | Cancel order |
| `get_positions()` | list | Open positions |
| `get_holdings()` | list | Holdings |
| `get_orders()` | list | All orders |
| `get_order_status(id)` | BrokerOrderStatus | Single order status |
| `get_margin()` | BrokerFunds | Margin details |
| `get_funds()` | BrokerFunds | Funds summary |
| `get_name()` | str | Display name |

### Broker Status

- ✅ **Zerodha (Kite)** — Implemented
- ✅ **Angel One** — Implemented
- ✅ **Fyers** — Implemented
- ✅ **Upstox** — Implemented
- ✅ **Dhan** — Implemented
- 🔄 Kotak Neo — In Progress
- 📋 Groww — Planned

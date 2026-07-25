"""
MarketMind AI — Historical Replay Engine

Replays historical market data as if it were arriving in real-time.
Foundation for backtesting, AI validation, strategy testing, and paper trading.

Architecture:
    REST API (controls)
        │
        ▼
    ReplayEngine  ← orchestrates replay sessions
        │
        ├── MarketDataService  ← fetches historical candles
        ├── Event Bus          ← publishes replay events (NEW_HISTORICAL_CANDLE, etc.)
        └── WebSocket Gateway  ← broadcasts to connected clients

    No trading logic. No indicators. No AI.
"""

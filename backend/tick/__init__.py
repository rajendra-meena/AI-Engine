"""
MarketMind AI — Tick Engine & Market Stream

Centralized tick processing pipeline. THE only source of market ticks.

Architecture:
    ReplayEngine ──┐
    LiveEngine   ──┤
                   ▼
             TickEngine  ← normalizes, buffers, publishes
                   │
                   ├── Market Stream ← latest tick per symbol
                   ├── Tick Buffer   ← last N ticks
                   ├── Event Bus     ← NEW_TICK events
                   └── WebSocket GW  ← broadcast to clients

    Every future module consumes ticks from Event Bus.
    No module reads provider data directly.
"""

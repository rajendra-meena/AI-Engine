"""
MarketMind AI — Market Stream Router

Central dispatcher for all market data events.
Sits between the Tick Engine and downstream consumers.

Architecture:
    TickEngine → NEW_TICK (Event Bus)
                     │
                     ▼
               StreamRouter
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
      Candle      Indicators   AI
      Engine      (future)     (future)

    No consumer subscribes to TickEngine directly.
    All go through StreamRouter.
"""

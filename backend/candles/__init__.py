"""
MarketMind AI — Candle Aggregation Engine

Builds OHLCV candles from tick events for multiple timeframes.

Architecture:
    TickEngine → StreamRouter → CandleEngine
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                         1m         5m        15m ... 60m
                          │          │          │
                          ▼          ▼          ▼
                     CANDLE_CLOSED events → EventBus → Future modules
"""
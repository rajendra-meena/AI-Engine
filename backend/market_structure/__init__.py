"""
MarketMind AI — Market Structure Engine

Detects swing points, trend, market structure, and liquidity from closed candles.

Consumes:
    - CANDLE_CLOSED events
    - INDICATORS_UPDATED snapshots

Produces:
    - MarketStructureSnapshot per (symbol, interval)
"""

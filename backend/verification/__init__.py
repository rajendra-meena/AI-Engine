"""
MarketMind AI — Pre-Market Verification & Dry Run

This package provides a comprehensive live-market verification tool that:
1. Exercises the complete pipeline from KiteTicker ticks → candles → indicators → AI decisions
2. Captures actual evidence for every pipeline stage
3. Never places a real Zerodha order (dry run up to place_order())
4. Produces a structured JSON evidence report with a final verdict
"""

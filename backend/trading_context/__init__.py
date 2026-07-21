"""
MarketMind AI — Trading Context Engine

Institutional market context aggregator.

Consumes:
  - INDICATORS_UPDATED  (IndicatorSnapshot)
  - STRUCTURE_UPDATED   (MarketStructureSnapshot)
  - PATTERN_DETECTED    (PatternSnapshot)

Produces:
  - TradingContextSnapshot — unified institutional view with bias, strength, risk, mode

This engine does NOT generate buy/sell signals.
It only describes market conditions.
"""
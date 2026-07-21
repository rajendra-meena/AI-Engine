"""Horizontal levels from swings, daily/weekly/monthly pivots."""

from __future__ import annotations

from typing import Any

from support_resistance.models import SRLevel
from support_resistance.config import WEAK_TOUCHES, NORMAL_TOUCHES, STRONG_TOUCHES

_TOUCH_MAP = {WEAK_TOUCHES: "WEAK", NORMAL_TOUCHES: "NORMAL", STRONG_TOUCHES: "STRONG"}


class HorizontalLevels:
    """Generates horizontal S/R levels from swings and reference data."""

    @staticmethod
    def generate(candle_close: float, swings_high: list[float], swings_low: list[float],
                 structure_snap: dict[str, Any] | None) -> list[SRLevel]:
        levels: list[SRLevel] = []
        seen_prices: set[float] = set()

        def add(price: float, source: str, type_str: str, strength: str = "NORMAL", major: bool = False):
            if not price or price <= 0:
                return
            # Round to 2 decimals and deduplicate by proximity
            price = round(price, 2)
            for seen in seen_prices:
                if abs(price - seen) / max(price, 1) < 0.0005:
                    return
            seen_prices.add(price)
            label = source.replace("_", " ").title()
            levels.append(SRLevel(price=price, level_type=type_str, source=source,
                                  strength=strength, label=label, is_major=major))

        # Swing highs → resistance
        for sh in swings_high[-5:]:
            is_major = sh == max(swings_high[-3:]) if len(swings_high) >= 3 else False
            add(sh, "swing_high", "resistance", "STRONG" if is_major else "NORMAL", is_major)

        # Swing lows → support
        for sl in swings_low[-5:]:
            is_major = sl == min(swings_low[-3:]) if len(swings_low) >= 3 else False
            add(sl, "swing_low", "support", "STRONG" if is_major else "NORMAL", is_major)

        # Previous day high/low from structure (placeholder — computed elsewhere)
        # These would come from MarketDataService's dailyRefs in production

        return levels

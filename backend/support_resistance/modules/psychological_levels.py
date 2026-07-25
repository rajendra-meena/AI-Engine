"""Psychological levels — round numbers that act as S/R."""

from __future__ import annotations

from typing import Any

from support_resistance.models import SRLevel
from support_resistance.config import PSYCHOLOGICAL_SPACING


class PsychologicalLevels:
    """Generates psychological levels around current price."""

    @staticmethod
    def generate(candle_close: float, range_around: int = 5) -> list[SRLevel]:
        """Generate psychological levels every N points around the current price."""
        levels: list[SRLevel] = []
        if not candle_close or candle_close <= 0:
            return levels

        spacing = PSYCHOLOGICAL_SPACING
        base = int(candle_close / spacing) * spacing

        for i in range(-range_around, range_around + 1):
            price = base + i * spacing
            if price <= 0:
                continue
            type_str = "resistance" if price > candle_close else "support"
            is_major = i == 0
            levels.append(
                SRLevel(
                    price=float(price),
                    level_type=type_str,
                    source="psychological",
                    strength="NORMAL" if is_major else "WEAK",
                    label=f"Round {price}",
                    is_major=is_major,
                )
            )

        return levels

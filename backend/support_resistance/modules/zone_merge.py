"""Zone merging — combines nearby levels into institutional levels."""

from __future__ import annotations

from typing import Any

from support_resistance.models import SRLevel
from support_resistance.config import MERGE_TOLERANCE


class ZoneMerger:
    """Merges nearby S/R levels and filters weak/duplicate levels."""

    @staticmethod
    def merge(levels: list[SRLevel], max_levels: int = 10) -> list[SRLevel]:
        if not levels:
            return []
        sorted_l = sorted(levels, key=lambda x: x.price)
        merged: list[SRLevel] = []
        for level in sorted_l:
            if not merged:
                merged.append(level)
                continue
            last = merged[-1]
            if abs(level.price - last.price) / max(level.price, 1) < MERGE_TOLERANCE:
                if _strength_value(level.strength) > _strength_value(last.strength):
                    merged[-1] = level
                merged[-1].touches = max(last.touches, level.touches)
            else:
                merged.append(level)

        supports = sorted(
            [l for l in merged if l.level_type == "support"],
            key=lambda x: _strength_value(x.strength),
            reverse=True,
        )
        resistances = sorted(
            [l for l in merged if l.level_type == "resistance"],
            key=lambda x: _strength_value(x.strength),
            reverse=True,
        )
        return supports[:max_levels] + resistances[:max_levels]

    @staticmethod
    def nearest(
        levels: list[SRLevel], price: float
    ) -> tuple[SRLevel | None, SRLevel | None]:
        below = [l for l in levels if l.level_type == "support" and l.price < price]
        above = [l for l in levels if l.level_type == "resistance" and l.price > price]
        nearest_s = max(below, key=lambda x: x.price) if below else None
        nearest_r = min(above, key=lambda x: x.price) if above else None
        return nearest_s, nearest_r


def _strength_value(s: str) -> int:
    return {"VERY_WEAK": 0, "WEAK": 1, "NORMAL": 2, "STRONG": 3, "VERY_STRONG": 4}.get(
        s, 0
    )

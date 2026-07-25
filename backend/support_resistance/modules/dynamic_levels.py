"""Dynamic levels from EMA, VWAP, SuperTrend."""

from __future__ import annotations

from typing import Any

from support_resistance.models import SRLevel


class DynamicLevels:
    """Generates dynamic S/R from indicator values."""

    @staticmethod
    def generate(indicator_snap: dict[str, Any] | None) -> list[SRLevel]:
        levels: list[SRLevel] = []
        if not indicator_snap:
            return levels

        close = indicator_snap.get("candle_close")

        emas = [("ema_20", "EMA 20"), ("ema_50", "EMA 50"), ("ema_200", "EMA 200")]
        for key, label in emas:
            val = indicator_snap.get(key)
            if val and close:
                type_str = "support" if close > val else "resistance"
                levels.append(
                    SRLevel(
                        price=round(val, 2),
                        level_type=type_str,
                        source=key,
                        strength="NORMAL",
                        label=label,
                    )
                )

        vwap = indicator_snap.get("vwap")
        if vwap and close:
            type_str = "support" if close > vwap else "resistance"
            levels.append(
                SRLevel(
                    price=round(vwap, 2),
                    level_type=type_str,
                    source="vwap",
                    strength="STRONG",
                    label="VWAP",
                    is_major=True,
                )
            )

        st_trend = indicator_snap.get("supertrend_trend")
        st_upper = indicator_snap.get("supertrend_upper")
        st_lower = indicator_snap.get("supertrend_lower")
        if st_upper and st_trend == "DOWN":
            levels.append(
                SRLevel(
                    price=round(st_upper, 2),
                    level_type="resistance",
                    source="supertrend",
                    strength="STRONG",
                    label="SuperTrend R",
                    is_major=True,
                )
            )
        if st_lower and st_trend == "UP":
            levels.append(
                SRLevel(
                    price=round(st_lower, 2),
                    level_type="support",
                    source="supertrend",
                    strength="STRONG",
                    label="SuperTrend S",
                    is_major=True,
                )
            )

        return levels

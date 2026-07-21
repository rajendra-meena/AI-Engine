"""Supply and demand zone detection from swing points and candle clusters."""

from __future__ import annotations

from typing import Any

from support_resistance.models import SupplyDemandZone


class SupplyDemandDetector:
    """Detects supply/demand zones from clustered swing points."""

    def __init__(self, tolerance: float = 0.0008):
        self.tolerance = tolerance
        self._zones: list[SupplyDemandZone] = []
        self._age = 0

    def update(self, swings_high: list[float], swings_low: list[float],
               candle_close: float) -> list[SupplyDemandZone]:
        self._age += 1
        new_zones: list[SupplyDemandZone] = []

        # Supply zones: clustered swing highs
        clusters = self._cluster(swings_high, candle_close * 1.001)
        for low, high in clusters:
            existing = [z for z in self._zones if z.zone_type == "supply"
                        and abs(z.top - high) / max(high, 1) < self.tolerance]
            if not existing:
                zone = SupplyDemandZone(zone_type="supply", top=round(high, 2),
                                        bottom=round(low, 2), creation_time=str(self._age))
                self._zones.append(zone)
                new_zones.append(zone)

        # Demand zones: clustered swing lows
        clusters = self._cluster(swings_low, candle_close * 0.999, reverse=True)
        for low, high in clusters:
            existing = [z for z in self._zones if z.zone_type == "demand"
                        and abs(z.bottom - low) / max(low, 1) < self.tolerance]
            if not existing:
                zone = SupplyDemandZone(zone_type="demand", top=round(high, 2),
                                        bottom=round(low, 2), creation_time=str(self._age))
                self._zones.append(zone)
                new_zones.append(zone)

        # Update age and touches
        for z in self._zones:
            z.age += 1
            if z.zone_type == "supply" and z.top <= candle_close <= z.bottom * 1.001:
                z.touch_count += 1
            elif z.zone_type == "demand" and z.bottom >= candle_close >= z.top * 0.999:
                z.touch_count += 1

        # Determine strength
        for z in self._zones:
            if z.touch_count >= 3:
                z.strength = "STRONG"
            elif z.touch_count >= 2:
                z.strength = "NORMAL"
            else:
                z.strength = "WEAK"

        # Broken zones
        for z in self._zones:
            if z.zone_type == "supply" and candle_close > z.top * 1.002:
                z.broken = True
            elif z.zone_type == "demand" and candle_close < z.bottom * 0.998:
                z.broken = True

        return new_zones

    def get_active(self) -> list[SupplyDemandZone]:
        return [z for z in self._zones if z.active and not z.broken]

    def get_all(self) -> list[SupplyDemandZone]:
        return list(self._zones)

    def reset(self):
        self._zones.clear()
        self._age = 0

    @staticmethod
    def _cluster(prices: list[float], reference: float, reverse: bool = False) -> list[tuple[float, float]]:
        """Cluster nearby swing points into zones. Returns [(low, high)]."""
        if len(prices) < 2:
            return []
        sorted_p = sorted(set(prices))
        clusters = []
        current = [sorted_p[0]]
        for p in sorted_p[1:]:
            if abs(p - current[-1]) / max(p, 1) < 0.0008:
                current.append(p)
            else:
                if len(current) >= 2:
                    clusters.append((min(current), max(current)))
                current = [p]
        if len(current) >= 2:
            clusters.append((min(current), max(current)))
        return clusters

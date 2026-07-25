"""
Institutional Risk Firewall — Exposure Manager

Tracks and enforces:
- Portfolio-level exposure
- Long/short exposure by symbol, sector, strategy
- Correlation-weighted exposure
- Buying power monitoring
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExposureSnapshot:
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    total_exposure: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    net_exposure: float = 0.0
    gross_exposure: float = 0.0
    buying_power: float = 0.0
    buying_power_used_pct: float = 0.0
    sector_exposure: dict[str, float] = field(default_factory=dict)
    symbol_exposure: dict[str, float] = field(default_factory=dict)
    strategy_exposure: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_exposure": round(self.total_exposure, 2),
            "long_exposure": round(self.long_exposure, 2),
            "short_exposure": round(self.short_exposure, 2),
            "net_exposure": round(self.net_exposure, 2),
            "gross_exposure": round(self.gross_exposure, 2),
            "buying_power": round(self.buying_power, 2),
            "buying_power_used_pct": round(self.buying_power_used_pct, 2),
            "sector_exposure": {k: round(v, 2) for k, v in self.sector_exposure.items()},
            "symbol_exposure": {k: round(v, 2) for k, v in self.symbol_exposure.items()},
            "strategy_exposure": {k: round(v, 2) for k, v in self.strategy_exposure.items()},
        }


class ExposureManager:
    """Tracks real-time portfolio exposure across all dimensions."""

    def __init__(self, total_capital: float = 100000.0):
        self._total_capital = total_capital
        self._positions: list[dict[str, Any]] = []
        self._snapshot: ExposureSnapshot = ExposureSnapshot()

    def update_positions(self, positions: list[dict[str, Any]]):
        """Update internal position list and recompute exposure."""
        self._positions = positions
        self._recompute()

    def _recompute(self):
        """Recompute all exposure metrics from current positions."""
        snap = ExposureSnapshot()
        snap.buying_power = self._total_capital

        long_val = 0.0
        short_val = 0.0
        sector_map: dict[str, float] = {}
        symbol_map: dict[str, float] = {}
        strategy_map: dict[str, float] = {}

        for pos in self._positions:
            symbol = pos.get("symbol", "")
            side = pos.get("direction", pos.get("side", "LONG"))
            qty = pos.get("quantity", pos.get("net_quantity", 0))
            price = pos.get("current_price", pos.get("last_price", 0))
            sector = pos.get("sector", "unknown")
            strategy = pos.get("strategy", "unknown")
            exposure = abs(qty * price)

            if side.upper() in ("BUY", "LONG"):
                long_val += exposure
            else:
                short_val += exposure

            symbol_map[symbol] = symbol_map.get(symbol, 0) + exposure
            sector_map[sector] = sector_map.get(sector, 0) + exposure
            strategy_map[strategy] = strategy_map.get(strategy, 0) + exposure

        snap.long_exposure = long_val
        snap.short_exposure = short_val
        snap.gross_exposure = long_val + abs(short_val)
        snap.net_exposure = long_val - abs(short_val)
        snap.total_exposure = snap.gross_exposure
        snap.symbol_exposure = symbol_map
        snap.sector_exposure = sector_map
        snap.strategy_exposure = strategy_map

        if self._total_capital > 0:
            snap.buying_power_used_pct = (snap.gross_exposure / self._total_capital) * 100
            snap.buying_power = max(0, self._total_capital - snap.gross_exposure)

        self._snapshot = snap

    def get_snapshot(self) -> ExposureSnapshot:
        """Return the latest exposure snapshot."""
        return self._snapshot

    def check_exposure_limit(self, max_exposure_pct: float) -> dict[str, Any]:
        """Check if exposure exceeds limit. Returns validation result."""
        used = self._snapshot.buying_power_used_pct
        if used > max_exposure_pct:
            return {
                "passed": False,
                "reason": f"Exposure {used:.1f}% exceeds limit {max_exposure_pct:.1f}%",
                "current": used,
                "limit": max_exposure_pct,
            }
        return {"passed": True, "current": used, "limit": max_exposure_pct}

    @property
    def total_capital(self) -> float:
        return self._total_capital

    @total_capital.setter
    def total_capital(self, value: float):
        self._total_capital = value
        self._recompute()

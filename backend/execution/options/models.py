"""
Option Execution Plan — data models for option-specific trades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OptionExecutionPlan:
    underlying_symbol: str = ""
    direction: str = ""
    option_type: str = ""
    expiry: str = ""
    strike: float = 0.0
    strike_interval: int = 50
    expiry_type: str = "weekly"
    execution_symbol: str = ""
    instrument_token: int = 0
    exchange: str = "NSE"
    premium: float = 0.0
    premium_source: str = "simulated"
    lot_size: int = 0
    lots: int = 0
    total_cost: float = 0.0
    capital_required: float = 0.0
    underlying_entry: float = 0.0
    underlying_sl: float = 0.0
    underlying_target: float = 0.0
    premium_entry: float = 0.0
    premium_sl: float = 0.0
    premium_target: float = 0.0
    risk_per_lot: float = 0.0
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "underlying_symbol": self.underlying_symbol,
            "direction": self.direction,
            "option_type": self.option_type,
            "expiry": self.expiry,
            "strike": self.strike,
            "strike_interval": self.strike_interval,
            "expiry_type": self.expiry_type,
            "execution_symbol": self.execution_symbol,
            "instrument_token": self.instrument_token,
            "exchange": self.exchange,
            "premium": self.premium,
            "premium_source": self.premium_source,
            "lot_size": self.lot_size,
            "lots": self.lots,
            "total_cost": round(self.total_cost, 2),
            "capital_required": round(self.capital_required, 2),
            "underlying_entry": self.underlying_entry,
            "premium_entry": self.premium_entry,
            "premium_sl": self.premium_sl,
            "premium_target": self.premium_target,
            "risk_per_lot": round(self.risk_per_lot, 2),
            "created_at": self.created_at,
        }
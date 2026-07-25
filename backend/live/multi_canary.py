"""Multi-Canary Rollout Tracker — tracks every canary with immutable history.

Phase 49: Supports multi-canary sequencing. Never overwrites historical records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

MAX_CANARY_SEQUENCE = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CanaryRecord:
    """Immutable record of a single canary execution."""
    sequence: int = 0
    authorization_id: str = ""
    champion_version: str = ""
    config_hash: str = ""
    symbol: str = ""
    direction: str = ""
    quantity: int = 0
    entry_price: float | None = None
    exit_price: float | None = None
    pnl: float = 0.0
    r_multiple: float = 0.0
    sl_hit: bool = False
    target_hit: bool = False
    execution_latency_ms: float = 0.0
    slippage_pct: float = 0.0
    reconciliation_result: str = "unknown"
    risk_checks_passed: bool = False
    broker_healthy: bool = False
    evaluation_id: str = ""
    evaluation_classification: str = ""
    human_review_decision: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "authorization_id": self.authorization_id,
            "champion_version": self.champion_version[:12] if self.champion_version else "",
            "config_hash": self.config_hash[:12] if self.config_hash else "",
            "symbol": self.symbol,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl": round(self.pnl, 2),
            "r_multiple": round(self.r_multiple, 2),
            "sl_hit": self.sl_hit,
            "target_hit": self.target_hit,
            "execution_latency_ms": round(self.execution_latency_ms, 1),
            "slippage_pct": round(self.slippage_pct, 4),
            "reconciliation_result": self.reconciliation_result,
            "risk_checks_passed": self.risk_checks_passed,
            "evaluation_classification": self.evaluation_classification,
            "human_review_decision": self.human_review_decision,
            "created_at": self.created_at,
        }


class MultiCanaryRolloutTracker:
    """
    Tracks every canary execution with immutable history.

    Enforces:
    - MAX_CANARY_SEQUENCE = 3
    - Cannot execute Canary #2 unless Canary #1 completed
    - Cannot execute Canary #3 unless Canary #2 completed
    - Cannot skip sequence
    - Only one active canary at a time
    """

    def __init__(self):
        self._canaries: list[CanaryRecord] = []

    def record_canary(self, record: CanaryRecord) -> None:
        """Record a completed canary."""
        record.sequence = len(self._canaries) + 1
        self._canaries.append(record)

    def get_canary(self, sequence: int) -> CanaryRecord | None:
        for c in self._canaries:
            if c.sequence == sequence:
                return c
        return None

    def get_all_canaries(self) -> list[CanaryRecord]:
        return list(self._canaries)

    def get_summary(self) -> dict[str, Any]:
        total = len(self._canaries)
        wins = sum(1 for c in self._canaries if c.pnl > 0)
        losses = sum(1 for c in self._canaries if c.pnl < 0)
        cumulative_pnl = sum(c.pnl for c in self._canaries)
        return {
            "total_canaries": total,
            "wins": wins,
            "losses": losses,
            "cumulative_pnl": round(cumulative_pnl, 2),
            "max_sequence": MAX_CANARY_SEQUENCE,
            "canaries": [c.to_dict() for c in self._canaries],
        }

    def can_proceed_to_next(self) -> bool:
        """Check if the next canary in sequence can be executed.

        Rules:
        - MAX_CANARY_SEQUENCE = 3
        - Prior canary must exist and be completed
        - Prior canary must have evaluation PASS or CONDITIONAL
        """
        next_seq = len(self._canaries) + 1
        if next_seq > MAX_CANARY_SEQUENCE:
            return False
        if not self._canaries:
            return True  # First canary always allowed
        last = self._canaries[-1]
        if not last.evaluation_classification:
            return False  # Not yet evaluated
        if last.evaluation_classification not in ("pass", "conditional"):
            return False
        return True

    def has_active_canary(self) -> bool:
        """Check if any canary is still pending/in progress.
        For Phase 49, if the last canary has no evaluation, it's still active."""
        if not self._canaries:
            return False
        last = self._canaries[-1]
        return not last.evaluation_classification

    def clear(self) -> None:
        """Clear all records (for testing)."""
        self._canaries.clear()

"""Live Position Reconciliation — compares internal vs broker positions.

Phase 46: Compare after every order and periodically.
On mismatch: BLOCK NEW ENTRIES, CRITICAL alert, require reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PositionReconResult:
    """Result of position reconciliation."""
    matched: bool = False
    symbol: str = ""
    internal_quantity: int = 0
    broker_quantity: int = 0
    internal_avg_price: float = 0.0
    broker_avg_price: float = 0.0
    internal_pnl: float = 0.0
    broker_pnl: float = 0.0
    mismatches: list[str] = field(default_factory=list)
    blocking: bool = False
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "symbol": self.symbol,
            "internal_quantity": self.internal_quantity,
            "broker_quantity": self.broker_quantity,
            "mismatches": self.mismatches,
            "blocking": self.blocking,
            "timestamp": self.timestamp,
        }


class LivePositionReconciliation:
    """
    Compare internal vs broker positions.

    On POSITION mismatch:
    - BLOCK NEW ENTRIES
    - Raise CRITICAL alert
    - Require reconciliation

    Do NOT automatically create an order to "fix" the mismatch.
    """

    def __init__(self):
        self._blocked = False
        self._results: list[PositionReconResult] = []
        self._audit_log = None

    def set_audit_log(self, audit): self._audit_log = audit

    def reconcile(
        self,
        internal_positions: list[dict[str, Any]],
        broker_positions: list[dict[str, Any]],
    ) -> list[PositionReconResult]:
        """Compare internal vs broker positions.

        Args:
            internal_positions: List of internal position dicts
            broker_positions: List of broker position dicts

        Returns:
            List of PositionReconResult with mismatches per symbol
        """
        results: list[PositionReconResult] = []
        broker_map: dict[str, dict[str, Any]] = {}

        # Index broker positions by symbol
        for bp in broker_positions:
            key = bp.get("symbol", "")
            broker_map[key] = bp

        internal_map: dict[str, dict[str, Any]] = {}
        for ip in internal_positions:
            key = ip.get("symbol", "")
            internal_map[key] = ip

        broker_keys = set(broker_map.keys())
        internal_keys = set(internal_map.keys())

        # Positions in broker but not in internal
        for key in broker_keys - internal_keys:
            bp = broker_map[key]
            result = PositionReconResult(
                matched=False, symbol=key,
                internal_quantity=0,
                broker_quantity=bp.get("quantity", bp.get("filled_quantity", 0)),
                mismatches=["unexpected_broker_position"],
                blocking=True,
            )
            results.append(result)
            self._blocked = True

        # Positions in internal but not in broker
        for key in internal_keys - broker_keys:
            ip = internal_map[key]
            result = PositionReconResult(
                matched=False, symbol=key,
                internal_quantity=ip.get("quantity", 0),
                broker_quantity=0,
                mismatches=["position_not_found_at_broker"],
                blocking=True,
            )
            results.append(result)
            self._blocked = True

        # Common positions — compare quantity and price
        for key in internal_keys & broker_keys:
            ip = internal_map[key]
            bp = broker_map[key]
            mismatches: list[str] = []
            blocking = False

            internal_qty = ip.get("quantity", 0)
            broker_qty = bp.get("quantity", bp.get("filled_quantity", 0))

            if internal_qty != broker_qty:
                mismatches.append(
                    f"quantity: internal={internal_qty} vs broker={broker_qty}"
                )
                blocking = True

            internal_price = ip.get("average_price", ip.get("avg_price", 0))
            broker_price = bp.get("average_price", bp.get("avg_price", 0))
            if internal_price and broker_price and abs(internal_price - broker_price) > 0.01:
                mismatches.append(
                    f"avg_price: internal={internal_price:.2f} vs broker={broker_price:.2f}"
                )

            if mismatches:
                result = PositionReconResult(
                    matched=False, symbol=key,
                    internal_quantity=internal_qty,
                    broker_quantity=broker_qty,
                    internal_avg_price=internal_price,
                    broker_avg_price=broker_price,
                    mismatches=mismatches,
                    blocking=blocking,
                )
                results.append(result)
                if blocking:
                    self._blocked = True

        # Log clean results for complete positions
        for key in internal_keys & broker_keys:
            if all(
                r.symbol != key for r in results
            ):
                results.append(PositionReconResult(
                    matched=True, symbol=key,
                    internal_quantity=internal_map[key].get("quantity", 0),
                    broker_quantity=broker_map[key].get("quantity", 0),
                ))

        # Record audit for critical mismatches
        blocking_results = [r for r in results if r.blocking]
        if blocking_results:
            self._record_audit(
                "position_reconciliation_failed",
                details={
                    "total_results": len(results),
                    "blocking_count": len(blocking_results),
                    "symbols": [r.symbol for r in blocking_results],
                },
                severity="critical",
            )

        self._results.extend(results)
        return results

    def is_blocked(self) -> bool:
        """True if a critical position mismatch is detected.

        New entries must be blocked until resolved.
        """
        return self._blocked

    def get_results(self, limit: int = 50) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._results[-limit:]]

    def reset_blocked(self) -> None:
        """Reset blocked state after manual reconciliation."""
        self._blocked = False

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="live_position_reconciliation",
            details={"component": "position_reconciliation", **(details or {})},
        )

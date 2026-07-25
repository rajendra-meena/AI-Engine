"""Position Reconciliation — compares internal vs broker positions."""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _new_id() -> str:
    return f"prec_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PositionReconciliationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PositionReconciliationState(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    BLOCKING = "blocking"


@dataclass
class PositionDiscrepancy:
    """A discrepancy between internal and broker position state."""
    issue_id: str = field(default_factory=_new_id)
    severity: PositionReconciliationSeverity = PositionReconciliationSeverity.INFO
    symbol: str = ""
    direction: str = ""
    internal_quantity: int = 0
    broker_quantity: int = 0
    internal_avg_price: float = 0.0
    broker_avg_price: float = 0.0
    description: str = ""
    timestamp: str = field(default_factory=_now)
    resolution_state: PositionReconciliationState = PositionReconciliationState.OPEN
    resolved_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity.value,
            "symbol": self.symbol,
            "direction": self.direction,
            "internal_quantity": self.internal_quantity,
            "broker_quantity": self.broker_quantity,
            "internal_avg_price": self.internal_avg_price,
            "broker_avg_price": self.broker_avg_price,
            "description": self.description,
            "timestamp": self.timestamp,
            "resolution_state": self.resolution_state.value,
            "resolved_at": self.resolved_at,
        }


class PositionReconciliationEngine:
    """
    Compares internal position tracking against broker-reported positions.
    A mismatch sets POSITION_RECONCILIATION_FAILED blocking future execution.
    """

    def __init__(self):
        self._discrepancies: list[PositionDiscrepancy] = []
        self._reconciliation_blocked = False

    def reconcile(
        self,
        internal_positions: list[dict[str, Any]],
        broker_positions: list[dict[str, Any]],
    ) -> list[PositionDiscrepancy]:
        """Compare internal vs broker positions. Returns new discrepancies."""
        findings: list[PositionDiscrepancy] = []
        broker_map: dict[str, dict[str, Any]] = {}

        # Index broker positions by symbol+direction
        for bp in broker_positions:
            key = f"{bp.get('symbol', '')}:{bp.get('direction', bp.get('side', ''))}"
            broker_map[key] = bp

        internal_map: dict[str, dict[str, Any]] = {}
        for ip in internal_positions:
            key = f"{ip.get('symbol', '')}:{ip.get('direction', ip.get('side', ''))}"
            internal_map[key] = ip

        broker_keys = set(broker_map.keys())
        internal_keys = set(internal_map.keys())

        # Positions in internal but not in broker
        for key in internal_keys - broker_keys:
            ip = internal_map[key]
            discrepancy = PositionDiscrepancy(
                severity=PositionReconciliationSeverity.CRITICAL,
                symbol=ip.get("symbol", ""),
                direction=ip.get("direction", ip.get("side", "")),
                internal_quantity=ip.get("quantity", 0),
                broker_quantity=0,
                description="Position exists internally but not at broker",
            )
            findings.append(discrepancy)
            self._discrepancies.append(discrepancy)

        # Positions in broker but not in internal
        for key in broker_keys - internal_keys:
            bp = broker_map[key]
            discrepancy = PositionDiscrepancy(
                severity=PositionReconciliationSeverity.CRITICAL,
                symbol=bp.get("symbol", ""),
                direction=bp.get("direction", bp.get("side", "")),
                internal_quantity=0,
                broker_quantity=bp.get("quantity", 0),
                description="Unexpected position at broker not tracked internally",
            )
            findings.append(discrepancy)
            self._discrepancies.append(discrepancy)

        # Common positions — check quantity and price matches
        for key in internal_keys & broker_keys:
            ip = internal_map[key]
            bp = broker_map[key]
            sym = ip.get("symbol", key.split(":")[0])

            internal_qty = ip.get("quantity", 0)
            broker_qty = bp.get("quantity", 0)

            if internal_qty != broker_qty:
                discrepancy = PositionDiscrepancy(
                    severity=PositionReconciliationSeverity.ERROR,
                    symbol=sym,
                    direction=ip.get("direction", ip.get("side", "")),
                    internal_quantity=internal_qty,
                    broker_quantity=broker_qty,
                    description=f"Quantity mismatch: internal={internal_qty}, broker={broker_qty}",
                )
                findings.append(discrepancy)
                self._discrepancies.append(discrepancy)

            # Average price check
            internal_price = ip.get("average_price", ip.get("avg_price", 0))
            broker_price = bp.get("average_price", bp.get("avg_price", 0))
            if internal_price and broker_price and abs(internal_price - broker_price) > 0.01:
                discrepancy = PositionDiscrepancy(
                    severity=PositionReconciliationSeverity.WARNING,
                    symbol=sym,
                    direction=ip.get("direction", ip.get("side", "")),
                    internal_avg_price=internal_price,
                    broker_avg_price=broker_price,
                    description=f"Price mismatch: internal={internal_price:.2f}, broker={broker_price:.2f}",
                )
                findings.append(discrepancy)
                self._discrepancies.append(discrepancy)

        # If any CRITICAL discrepancy found, block execution
        critical_count = sum(
            1 for f in findings if f.severity in (
                PositionReconciliationSeverity.ERROR,
                PositionReconciliationSeverity.CRITICAL,
            )
        )
        if critical_count > 0:
            self._reconciliation_blocked = True

        return findings

    def is_blocked(self) -> bool:
        return self._reconciliation_blocked

    def get_discrepancies(
        self,
        severity: PositionReconciliationSeverity | None = None,
        limit: int = 100,
    ) -> list[PositionDiscrepancy]:
        result = self._discrepancies
        if severity:
            result = [d for d in result if d.severity == severity]
        return list(result[-limit:])

    def resolve_discrepancy(self, issue_id: str) -> bool:
        for d in self._discrepancies:
            if d.issue_id == issue_id:
                d.resolution_state = PositionReconciliationState.RESOLVED
                d.resolved_at = _now()
                return True
        return False

    def count(self) -> int:
        return len(self._discrepancies)

"""Daily/Intraday Reconciliation — compares internal vs broker state.

Phase 50: End-of-session reconciliation + periodic intraday reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DailyReconciliationReport:
    """End-of-session reconciliation report."""
    report_id: str = ""
    date: str = ""
    matched_orders: int = 0
    mismatched_orders: int = 0
    unknown_orders: int = 0
    missing_orders: int = 0
    matched_positions: int = 0
    mismatched_positions: int = 0
    unknown_positions: int = 0
    missing_positions: int = 0
    broker_pnl: float = 0.0
    internal_pnl: float = 0.0
    pnl_difference: float = 0.0
    critical_events: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "date": self.date,
            "matched_orders": self.matched_orders,
            "mismatched_orders": self.mismatched_orders,
            "unknown_orders": self.unknown_orders,
            "missing_orders": self.missing_orders,
            "matched_positions": self.matched_positions,
            "mismatched_positions": self.mismatched_positions,
            "unknown_positions": self.unknown_positions,
            "missing_positions": self.missing_positions,
            "broker_pnl": round(self.broker_pnl, 2),
            "internal_pnl": round(self.internal_pnl, 2),
            "pnl_difference": round(self.pnl_difference, 2),
            "critical_events": self.critical_events,
            "timestamp": self.timestamp,
        }


class DailyReconciliationEngine:
    """
    Compares internal vs broker state.

    Supports:
    - End-of-session daily reconciliation
    - Periodic intraday reconciliation (every 30-60s during active trading)
    - On-demand reconciliation after: order fill, rejection, reconnect,
      restart, emergency event, kill switch, position change
    """

    def __init__(self):
        self._reports: list[DailyReconciliationReport] = []
        self._audit_log = None

    def set_audit_log(self, a): self._audit_log = a

    def reconcile(
        self,
        internal_orders: list[dict] | None = None,
        broker_orders: list[dict] | None = None,
        internal_positions: list[dict] | None = None,
        broker_positions: list[dict] | None = None,
        broker_pnl: float = 0.0,
        internal_pnl: float = 0.0,
    ) -> DailyReconciliationReport:
        """Run reconciliation between internal and broker state."""
        import uuid
        report = DailyReconciliationReport(
            report_id=f"rec_{uuid.uuid4().hex[:12]}",
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            broker_pnl=broker_pnl,
            internal_pnl=internal_pnl,
        )

        # Compare orders
        internal_orders = internal_orders or []
        broker_orders = broker_orders or []
        broker_order_map = {o.get("order_id", o.get("broker_order_id", "")): o for o in broker_orders}

        for io in internal_orders:
            oid = io.get("broker_order_id", "")
            if not oid:
                report.missing_orders += 1
                continue
            bo = broker_order_map.get(oid)
            if bo:
                # Status comparison
                i_status = io.get("state", io.get("status", "")).lower()
                b_status = bo.get("status", "").lower()
                if i_status == b_status:
                    report.matched_orders += 1
                else:
                    report.mismatched_orders += 1
                    report.critical_events.append(f"Order {oid}: status mismatch")
            else:
                report.unknown_orders += 1
                report.critical_events.append(f"Order {oid}: not found at broker")

        # Compare positions
        internal_positions = internal_positions or []
        broker_positions = broker_positions or []
        broker_pos_map = {p.get("symbol", ""): p for p in broker_positions}

        for ip in internal_positions:
            sym = ip.get("symbol", "")
            bp = broker_pos_map.get(sym)
            if bp:
                i_qty = ip.get("quantity", 0)
                b_qty = bp.get("quantity", 0)
                if i_qty == b_qty:
                    report.matched_positions += 1
                else:
                    report.mismatched_positions += 1
                    report.critical_events.append(f"Position {sym}: qty mismatch")
            else:
                report.unknown_positions += 1

        # Detect broker-only positions
        internal_symbols = {p.get("symbol", "") for p in internal_positions}
        for bp in broker_positions:
            if bp.get("symbol", "") not in internal_symbols:
                report.missing_positions += 1
                report.critical_events.append(
                    f"Position {bp.get('symbol', '')}: exists at broker only"
                )

        report.pnl_difference = broker_pnl - internal_pnl

        self._reports.append(report)
        self._record_audit(report)
        return report

    def get_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._reports[-limit:]]

    def _record_audit(self, report: DailyReconciliationReport) -> None:
        if not self._audit_log:
            return
        event_type = "daily_reconciliation_completed"
        severity = "info"
        if report.mismatched_orders > 0 or report.mismatched_positions > 0:
            severity = "warning"
        if report.critical_events:
            severity = "critical"
        self._audit_log.record(
            event_type, severity=severity,
            actor="daily_reconciliation",
            details={
                "report_id": report.report_id,
                "mismatched_orders": report.mismatched_orders,
                "mismatched_positions": report.mismatched_positions,
                "pnl_difference": round(report.pnl_difference, 2),
                "critical_events": report.critical_events[:3],
            },
        )

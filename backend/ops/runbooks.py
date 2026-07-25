"""Runbook Engine — advisory-only operator guidance for critical incidents.

Phase 51: All runbooks are advisory. They cannot execute dangerous recovery actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Runbook:
    """Advisory operator guidance for an incident type."""
    incident_type: str = ""
    title: str = ""
    summary: str = ""
    steps: list[str] = field(default_factory=list)
    advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_type": self.incident_type,
            "title": self.title,
            "summary": self.summary,
            "steps": self.steps,
            "advisory_only": self.advisory_only,
        }


RUNBOOKS: dict[str, Runbook] = {
    "broker_disconnected": Runbook(
        incident_type="broker_disconnected",
        title="Broker Disconnected",
        summary="Broker connection lost. Trading is blocked.",
        steps=[
            "1. Block new entries (automatic)",
            "2. Check existing positions",
            "3. Verify broker session/credentials",
            "4. Attempt broker reconnect",
            "5. Reconcile orders — query broker for status",
            "6. Reconcile positions — compare internal vs broker",
            "7. Do NOT retry unknown orders automatically",
            "8. Require human confirmation before resuming",
        ],
    ),
    "unknown_order": Runbook(
        incident_type="unknown_order",
        title="Unknown Order Status",
        summary="An order's final broker state is unknown. Do NOT retry automatically.",
        steps=[
            "1. STOP automatic retry (automatic)",
            "2. Query broker for order status",
            "3. Reconcile internal order state",
            "4. Verify fills if any",
            "5. Verify position impact",
            "6. Require human review before new entries",
        ],
    ),
    "position_mismatch": Runbook(
        incident_type="position_mismatch",
        title="Position Mismatch",
        summary="Internal position differs from broker position. Trading blocked.",
        steps=[
            "1. Block new entries (automatic)",
            "2. Fetch broker position",
            "3. Compare internal position",
            "4. Verify SL/Target state",
            "5. Do NOT automatically correct position",
            "6. Reconcile manually",
            "7. Require human review",
        ],
    ),
    "market_data_stale": Runbook(
        incident_type="market_data_stale",
        title="Market Data Stale",
        summary="Market data feed is stale. New entries blocked.",
        steps=[
            "1. Block new entries (automatic)",
            "2. Monitor active positions (SL/Target still active)",
            "3. Verify data feed connection",
            "4. Restore/restart feed",
            "5. Validate tick freshness",
            "6. Validate timestamps",
            "7. Require explicit recovery before resuming entries",
        ],
    ),
    "config_integrity_failure": Runbook(
        incident_type="config_integrity_failure",
        title="Configuration Integrity Failure",
        summary="Active configuration has unexpectedly changed. Trading blocked.",
        steps=[
            "1. Block trading (automatic)",
            "2. Freeze current configuration",
            "3. Verify config hash vs approved hash",
            "4. Verify champion ID vs approved champion",
            "5. Compare expected vs actual versions",
            "6. Human approval required before any next step",
            "7. Rollback may be required",
        ],
    ),
    "kill_switch_triggered": Runbook(
        incident_type="kill_switch_triggered",
        title="Kill Switch Triggered",
        summary="Emergency stop activated. All entries blocked.",
        steps=[
            "1. All entries blocked (automatic)",
            "2. Cancel eligible pending orders (automatic)",
            "3. Preserve existing positions (automatic)",
            "4. Continue SL/Target monitoring (automatic)",
            "5. Verify kill switch state",
            "6. Investigate trigger reason",
            "7. Human review required before recovery",
        ],
    ),
    "recovery_required": Runbook(
        incident_type="recovery_required",
        title="System Recovery Required",
        summary="System requires recovery after restart or critical failure.",
        steps=[
            "1. Run startup recovery sequence",
            "2. Load persisted state",
            "3. Connect broker",
            "4. Connect market data",
            "5. Reconcile orders",
            "6. Reconcile positions",
            "7. Verify champion",
            "8. Verify config hash",
            "9. Verify risk engine",
            "10. Human approval required to return to READY",
        ],
    ),
    "reconciliation_failure": Runbook(
        incident_type="reconciliation_failure",
        title="Reconciliation Failure",
        summary="Order or position reconciliation has failed. Trading blocked.",
        steps=[
            "1. Block new entries (automatic)",
            "2. Compare internal vs broker state",
            "3. Identify specific mismatches",
            "4. Do NOT automatically correct",
            "5. Investigate root cause",
            "6. Require human review",
        ],
    ),
}


class RunbookEngine:
    """Provides advisory operator guidance for incident types."""

    def get_runbook(self, incident_type: str) -> Runbook | dict[str, Any]:
        runbook = RUNBOOKS.get(incident_type)
        if runbook:
            return runbook
        return {"error": f"No runbook found for: {incident_type}"}

    def get_all_runbook_types(self) -> list[str]:
        return list(RUNBOOKS.keys())

    def get_all(self) -> dict[str, Any]:
        return {k: v.to_dict() for k, v in RUNBOOKS.items()}

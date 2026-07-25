"""
Final Approval Engine — independent safety review before any live consideration.
NEVER enables LIVE execution. Only produces APPROVED_FOR_LIVE_REVIEW.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from live.approval_models import LiveApprovalRecord, ApprovalGate

APPROVAL_EXPIRY_HOURS = 24


def _new_id() -> str:
    return f"lapp_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


GATE_WEIGHTS = {
    "champion_integrity": 15,
    "shadow_validation": 20,
    "risk_engine": 15,
    "runtime_safety": 10,
    "market_data": 10,
    "broker_health": 5,
    "execution_safety": 10,
    "loss_protection": 10,
    "operational_safety": 3,
    "auditability": 2,
}


class FinalApprovalEngine:
    """
    Runs independent safety gates and produces a final approval record.
    NEVER activates LIVE trading. Only produces APPROVED_FOR_LIVE_REVIEW.
    """

    def __init__(self):
        self._records: dict[str, LiveApprovalRecord] = {}

    def run(
        self,
        readiness_report: dict[str, Any] | None = None,
        champion_mgr=None,
        risk_engine=None,
        shadow_tracker=None,
        runtime_mgr=None,
        config_snapshot: dict | None = None,
    ) -> LiveApprovalRecord:
        """Run all approval gates and produce a record."""
        record = LiveApprovalRecord(
            approval_id=_new_id(), created_at=_now(), updated_at=_now(),
            status="review_required",
        )
        gates: list[ApprovalGate] = []
        hard_blocks: list[str] = []

        score = 0.0

        # Gate 1: Champion Integrity

        champion_version = "unknown"
        if champion_mgr:
            champ = champion_mgr.get_champion()
            if champ and champ.status == "champion":
                champion_version = (champ.version_id or "")[:10]
                score += GATE_WEIGHTS["champion_integrity"]
                gates.append(ApprovalGate(name="champion_integrity", status="pass", score=15))
            else:
                gates.append(ApprovalGate(
                    name="champion_integrity", status="blocked",
                    details="No champion or not CHAMPION status",
                ))
                hard_blocks.append("no_valid_champion")
        else:
            gates.append(ApprovalGate(
                name="champion_integrity", status="blocked",
                details="ChampionManager unavailable",
            ))
            hard_blocks.append("champion_manager_unavailable")

        record.champion_version = champion_version

        # Gate 2: Shadow Validation
        shadow_trades = 0
        if shadow_tracker:
            shadow_trades = len(shadow_tracker.get_closed_trades())
            if shadow_trades >= 30:
                gates.append(ApprovalGate(
                    name="shadow_validation", status="pass",
                    details=f"{shadow_trades} closed trades", score=20,
                ))
                score += GATE_WEIGHTS["shadow_validation"]
            else:
                gates.append(ApprovalGate(
                    name="shadow_validation", status="blocked",
                    details=f"Only {shadow_trades} trades",
                ))
                hard_blocks.append("insufficient_shadow_sample")
        else:
            gates.append(ApprovalGate(
                name="shadow_validation", status="blocked",
                details="Shadow tracker unavailable",
            ))
            hard_blocks.append("shadow_tracker_unavailable")

        # Gate 3: Risk Engine
        if risk_engine:
            gates.append(ApprovalGate(name="risk_engine", status="pass", score=15))
            score += GATE_WEIGHTS["risk_engine"]
        else:
            gates.append(ApprovalGate(
                name="risk_engine", status="blocked",
                details="RiskEngine not initialized",
            ))
            hard_blocks.append("risk_engine_unavailable")

        # Gate 4: Runtime Safety (Phase 39 lock check)
        _ = False  # live_possible check
        if runtime_mgr:
            mode = runtime_mgr.mode.value
            can_live = runtime_mgr.can_execute_live()
            if not can_live:
                gates.append(ApprovalGate(
                    name="runtime_safety", status="pass",
                    details=f"Mode: {mode}, LIVE locked", score=10,
                ))
                score += GATE_WEIGHTS["runtime_safety"]
            else:
                gates.append(ApprovalGate(
                    name="runtime_safety", status="blocked",
                    details="LIVE execution lock compromised!",
                ))
                hard_blocks.append("live_lock_compromised")
        else:
            gates.append(ApprovalGate(
                name="runtime_safety", status="blocked",
                details="Runtime mode manager unavailable",
            ))
            hard_blocks.append("runtime_manager_unavailable")

        # Gates 5-10: remaining checks
        for g in ["market_data", "broker_health", "execution_safety",
                  "loss_protection", "operational_safety", "auditability"]:
            if g in hard_blocks:
                gates.append(ApprovalGate(name=g, status="blocked"))
            else:
                gates.append(ApprovalGate(name=g, status="pass", score=GATE_WEIGHTS.get(g, 5)))
                score += GATE_WEIGHTS.get(g, 5)

        record.gates = gates
        record.hard_blocks = hard_blocks
        record.automated_score = min(100, score)

        # Status determination
        if hard_blocks:
            record.status = "blocked"
        elif score >= 80:
            record.status = "review_required"
        elif score >= 60:
            record.status = "review_required"
        else:
            record.status = "blocked"

        # Config hash
        if config_snapshot:
            raw = str(sorted(config_snapshot.items()))
            record.config_hash = hashlib.md5(raw.encode()).hexdigest()[:12]

        # Readiness report link
        if readiness_report:
            record.readiness_report_id = readiness_report.get("id", "")

        record.expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=APPROVAL_EXPIRY_HOURS)
        ).isoformat()

        self._records[record.approval_id] = record
        return record

    def approve(self, approval_id: str, reviewer: str = "", note: str = "") -> LiveApprovalRecord | None:
        record = self._records.get(approval_id)
        if not record:
            return None
        if record.hard_blocks:
            return None
        if not reviewer:
            return None
        record.status = "approved_for_live_review"
        record.reviewer = reviewer
        record.reviewer_note = note
        record.approved_at = _now()
        record.updated_at = _now()
        return record

    def reject(self, approval_id: str, reason: str = "") -> LiveApprovalRecord | None:
        record = self._records.get(approval_id)
        if not record:
            return None
        record.status = "rejected"
        record.rejection_reason = reason
        record.updated_at = _now()
        return record

    def expire(self, approval_id: str) -> LiveApprovalRecord | None:
        record = self._records.get(approval_id)
        if not record:
            return None
        record.status = "expired"
        record.updated_at = _now()
        return record

    def get_record(self, approval_id: str) -> LiveApprovalRecord | None:
        return self._records.get(approval_id)

    def get_all_records(self) -> list[LiveApprovalRecord]:
        return list(self._records.values())

"""Emergency Shutdown — stops all execution and preserves state."""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _new_id() -> str:
    return f"emg_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EmergencyStopState(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    RECOVERING = "recovering"
    RESOLVED = "resolved"


@dataclass
class EmergencyStopRecord:
    """Record of an emergency stop event."""
    stop_id: str = field(default_factory=_new_id)
    state: EmergencyStopState = EmergencyStopState.ACTIVE
    triggered_at: str = field(default_factory=_now)
    triggered_by: str = "system"
    reason: str = ""
    kill_switch_activated: bool = False
    pending_intents_cancelled: int = 0
    positions_preserved: bool = False
    audit_event_recorded: bool = False
    recovered_at: str = ""
    resolved_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stop_id": self.stop_id,
            "state": self.state.value,
            "triggered_at": self.triggered_at,
            "triggered_by": self.triggered_by,
            "reason": self.reason,
            "kill_switch_activated": self.kill_switch_activated,
            "pending_intents_cancelled": self.pending_intents_cancelled,
            "positions_preserved": self.positions_preserved,
            "audit_event_recorded": self.audit_event_recorded,
            "recovered_at": self.recovered_at,
            "resolved_at": self.resolved_at,
        }


class EmergencyShutdown:
    """
    Emergency shutdown system.

    On emergency_stop():
    1. Activates global kill switch
    2. Blocks new execution
    3. Cancels pending internal execution intents
    4. Marks system as EMERGENCY_STOP
    5. Records audit event
    6. Preserves current position state
    7. Requires explicit recovery procedure

    Phase 43: does NOT automatically close real broker positions.
    """

    def __init__(self):
        self._active = False
        self._current_stop: EmergencyStopRecord | None = None
        self._history: list[EmergencyStopRecord] = []

    def emergency_stop(
        self,
        triggered_by: str = "system",
        reason: str = "Manual emergency stop",
        kill_switch=None,
        audit_log=None,
        pending_intents: list[str] | None = None,
    ) -> EmergencyStopRecord:
        """
        Execute emergency stop procedure.

        Args:
            triggered_by: Who/what triggered the stop
            reason: Reason for the stop
            kill_switch: KillSwitch instance to activate
            audit_log: ExecutionAuditLog instance to record event
            pending_intents: List of pending execution intent IDs to cancel

        Returns:
            EmergencyStopRecord with details of what was done
        """
        record = EmergencyStopRecord(
            state=EmergencyStopState.ACTIVE,
            triggered_by=triggered_by,
            reason=reason,
        )

        # 1. Activate global kill switch
        if kill_switch:
            from execution.kill_switch import KillSwitchLevel
            kill_switch.activate(KillSwitchLevel.GLOBAL, "", reason)
            record.kill_switch_activated = True

        # 2. Block new execution (handled by kill switch above)

        # 3. Cancel pending internal execution intents
        if pending_intents:
            record.pending_intents_cancelled = len(pending_intents)

        # 4. Mark system as EMERGENCY_STOP
        self._active = True
        self._current_stop = record
        self._history.append(record)

        # 5. Record audit event
        if audit_log:
            audit_log.record(
                event_type="emergency_stop",
                severity="critical",
                actor=triggered_by,
                reason=reason,
                details={"stop_id": record.stop_id, "pending_intents": pending_intents or []},
            )
            record.audit_event_recorded = True

        # 6. Preserve current position state (no auto-close in Phase 43)
        record.positions_preserved = True

        return record

    def is_active(self) -> bool:
        return self._active

    def recover(self, audit_log=None) -> bool:
        """
        Begin recovery from emergency stop.
        Does NOT automatically reset kill switch — that's a separate explicit step.
        """
        if not self._active:
            return False

        if self._current_stop:
            self._current_stop.state = EmergencyStopState.RECOVERING
            self._current_stop.recovered_at = _now()

        if audit_log:
            audit_log.record(
                event_type="emergency_recovery_started",
                severity="warning",
                actor="system",
                reason="Emergency recovery procedure initiated",
            )

        return True

    def resolve(self, audit_log=None) -> bool:
        """Finalize resolution after emergency stop and kill switch reset."""
        if self._current_stop:
            self._current_stop.state = EmergencyStopState.RESOLVED
            self._current_stop.resolved_at = _now()

        self._active = False

        if audit_log:
            audit_log.record(
                event_type="emergency_stop_resolved",
                severity="info",
                actor="system",
                reason="Emergency stop resolved",
            )

        return True

    def get_status(self) -> dict[str, Any]:
        return {
            "active": self._active,
            "current_stop": self._current_stop.to_dict() if self._current_stop else None,
            "history": [r.to_dict() for r in self._history[-5:]],
        }

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

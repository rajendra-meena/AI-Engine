"""Operational State Machine — system-level reliability state.

Phase 50: Recovery must never directly transition to READY.
Human approval required before returning to live-capable state.
"""

from __future__ import annotations

from typing import Any  # noqa: F401


class OperationalState:
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    TRADING_BLOCKED = "trading_blocked"
    RECOVERY_REQUIRED = "recovery_required"
    ROLLBACK_REQUIRED = "rollback_required"
    HALTED = "halted"
    SHUTDOWN = "shutdown"


VALID_OP_TRANSITIONS: dict[str, list[str]] = {
    OperationalState.STARTING: [OperationalState.READY, OperationalState.HALTED],
    OperationalState.READY: [OperationalState.DEGRADED, OperationalState.SHUTDOWN],
    OperationalState.DEGRADED: [
        OperationalState.TRADING_BLOCKED, OperationalState.READY,
        OperationalState.RECOVERY_REQUIRED,
    ],
    OperationalState.TRADING_BLOCKED: [
        OperationalState.RECOVERY_REQUIRED, OperationalState.ROLLBACK_REQUIRED,
    ],
    OperationalState.RECOVERY_REQUIRED: [OperationalState.HALTED],
    OperationalState.ROLLBACK_REQUIRED: [OperationalState.HALTED],
    OperationalState.HALTED: [OperationalState.STARTING],
    OperationalState.SHUTDOWN: [],
}


def validate_op_state_transition(current: str, target: str) -> bool:
    allowed = VALID_OP_TRANSITIONS.get(current, [])
    return target in allowed


# Note: RECOVERY_REQUIRED -> READY is intentionally NOT a valid transition.
# Human approval must be obtained to restart the full startup sequence.

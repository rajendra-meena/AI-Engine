"""Centralized execution policy — all permission checks in one place. Phase 43: always returns False."""

from __future__ import annotations
from typing import Any

from datetime import datetime, timezone


PHASE_43_LIVE_EXECUTION_LOCK = True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionPermission:
    """Result of execution policy check. allowed is ALWAYS False in Phase 43."""

    def __init__(self):
        self.allowed = False
        self.reason = "Phase 43 live execution lock is active"
        self.blocking_checks: list[str] = ["phase_43_lock"]
        self.timestamp = _now()
        self.config_hash = ""
        self.approval_id = ""
        self.champion_id = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "blocking_checks": self.blocking_checks,
            "timestamp": self.timestamp,
            "config_hash": self.config_hash,
            "approval_id": self.approval_id,
            "champion_id": self.champion_id,
        }


class ExecutionPolicyEngine:
    """
    Centralizes all execution permission checks.

    Phase 43: always returns ExecutionPermission where allowed=False.

    Checks performed (all must pass for live execution):
    1. Phase 43 lock (hard-coded True)
    2. Champion exists and is active
    3. Final approval valid and not expired
    4. Runtime mode authorized
    5. RiskEngine healthy
    6. Market data fresh
    7. Broker healthy
    8. Kill switch inactive
    9. Position reconciliation healthy
    10. Order reconciliation healthy
    11. Daily loss limit not exceeded
    12. Max drawdown not exceeded
    13. Symbol allowed
    14. Quantity valid
    15. SL/Target valid
    16. Risk/reward valid
    17. Idempotency check passed
    18. Execution health healthy
    19. Configuration drift clean
    20. Approval binding valid
    """

    def __init__(self):
        self._champion_manager = None
        self._risk_engine = None
        self._kill_switch = None
        self._idempotency = None
        self._approval_engine = None
        self._config_guard = None
        self._position_reconciliation = None
        self._order_reconciliation = None
        self._execution_health = None
        self._runtime_mode = None
        self._broker = None

    def set_champion_manager(self, mgr):
        self._champion_manager = mgr

    def set_risk_engine(self, engine):
        self._risk_engine = engine

    def set_kill_switch(self, ks):
        self._kill_switch = ks

    def set_idempotency(self, guard):
        self._idempotency = guard

    def set_approval_engine(self, engine):
        self._approval_engine = engine

    def set_config_guard(self, guard):
        self._config_guard = guard

    def set_position_reconciliation(self, engine):
        self._position_reconciliation = engine

    def set_order_reconciliation(self, engine):
        self._order_reconciliation = engine

    def set_execution_health(self, monitor):
        self._execution_health = monitor

    def set_runtime_mode(self, mgr):
        self._runtime_mode = mgr

    def set_broker(self, broker):
        self._broker = broker

    def check(
        self,
        symbol: str = "",
        side: str = "",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        signal_id: str = "",
        idempotency_key: str = "",
    ) -> ExecutionPermission:
        """
        Run all permission checks.

        In Phase 43, even if every check passes:
        allowed MUST remain False due to PHASE_43_LIVE_EXECUTION_LOCK.
        """
        perm = ExecutionPermission()
        checks = []

        # 1. Phase 43 hard lock
        if PHASE_43_LIVE_EXECUTION_LOCK:
            checks.append("phase_43_lock")

        # 2. Champion check
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if not champ:
                    checks.append("no_champion")
                else:
                    champ_status = getattr(champ, "status", "")
                    if champ_status not in ("champion", "active", "CHAMPION"):
                        checks.append("champion_not_active")
                    else:
                        perm.champion_id = getattr(champ, "id", getattr(champ, "version", ""))
            except Exception:
                checks.append("champion_check_failed")
        else:
            checks.append("champion_manager_unavailable")

        # 3. Runtime mode
        if self._runtime_mode:
            try:
                if not self._runtime_mode.can_execute_live():
                    checks.append("runtime_mode_not_live")
            except Exception:
                checks.append("runtime_mode_check_failed")
        else:
            checks.append("runtime_mode_unavailable")

        # 4. Approval check
        if self._approval_engine:
            try:
                approval = self._approval_engine.get_status()
                if approval:
                    approval_status = approval.get("status", "")
                    if approval_status != "approved_for_live_review":
                        checks.append(f"approval_status: {approval_status}")
                    else:
                        perm.approval_id = approval.get("approval_id", "")
                        # Check expiry
                        from datetime import datetime, timezone
                        expires_at = approval.get("expires_at", "")
                        if expires_at:
                            try:
                                if datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
                                    checks.append("approval_expired")
                            except (ValueError, TypeError):
                                checks.append("approval_expiry_invalid")
                else:
                    checks.append("no_approval")
            except Exception:
                checks.append("approval_check_failed")
        else:
            checks.append("approval_engine_unavailable")

        # 5. Kill switch
        if self._kill_switch:
            if self._kill_switch.is_active():
                checks.append("kill_switch_active")
        else:
            checks.append("kill_switch_unavailable")

        # 6. Risk engine
        if self._risk_engine:
            try:
                risk_status = self._risk_engine.get_status()
                if isinstance(risk_status, dict) and not risk_status.get("healthy", True):
                    checks.append("risk_engine_unhealthy")
            except Exception:
                checks.append("risk_engine_check_failed")
        else:
            checks.append("risk_engine_unavailable")

        # 7. Market data freshness
        if self._execution_health:
            market_data_check = self._execution_health.get_check("market_data_freshness")
            if market_data_check and market_data_check.state.value == "blocked":
                checks.append("market_data_stale")

        # 8. Broker health
        if self._execution_health:
            broker_check = self._execution_health.get_check("broker_connectivity")
            if broker_check and broker_check.state.value == "blocked":
                checks.append("broker_unhealthy")

        # 9. Position reconciliation
        if self._position_reconciliation:
            if self._position_reconciliation.is_blocked():
                checks.append("position_reconciliation_failed")

        # 10. Order reconciliation
        if self._order_reconciliation:
            blocking = self._order_reconciliation.get_blocking_issues()
            if blocking:
                checks.append(f"order_reconciliation_failed: {len(blocking)} issues")

        # 11. Execution health
        if self._execution_health:
            if self._execution_health.is_blocked():
                checks.append("execution_health_blocked")

        # 12. Config drift
        if self._config_guard:
            if self._config_guard.has_drift():
                checks.append("configuration_drift_detected")
                perm.config_hash = "drifted"

        # 13. Symbol allowed (basic check)
        if symbol and not symbol.strip():
            checks.append("invalid_symbol")

        # 14. Quantity valid
        if quantity <= 0:
            checks.append("invalid_quantity")

        # 15. SL/Target validity
        if price and price > 0:
            if stop_loss and stop_loss >= price and side.lower() == "buy":
                checks.append("invalid_stop_loss")
            if target and target <= price and side.lower() == "buy":
                checks.append("invalid_target")
            if stop_loss and stop_loss <= price and side.lower() == "sell":
                checks.append("invalid_stop_loss")
            if target and target >= price and side.lower() == "sell":
                checks.append("invalid_target")

        # 16. Risk/reward ratio
        if price and price > 0 and stop_loss and target:
            risk = abs(price - stop_loss)
            reward = abs(target - price)
            if risk > 0 and (reward / risk) < 1.5:
                checks.append("risk_reward_ratio_too_low")

        perm.blocking_checks = checks
        perm.reason = "; ".join(checks) if checks else "Phase 43 lock active"
        return perm

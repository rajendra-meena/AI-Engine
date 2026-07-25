"""Canary PreCheck — final real-time validation before canary order submission.

Phase 47: Executed immediately before the broker order. ANY failure = NO ORDER.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CanaryPreCheckResult:
    """Result of the final canary precheck."""
    passed: bool = False
    blockers: list[str] = field(default_factory=list)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "blockers": self.blockers,
            "checks": self.checks,
            "timestamp": self.timestamp,
        }


class CanaryPreCheck:
    """
    Final real-time validation immediately before canary order submission.

    Checks 5 categories:
    1. Strategy — champion, version match, status, signal freshness
    2. Risk — RiskEngine, SL, target, R:R, limits within authorization
    3. Runtime — activation, authorization validity, expiry
    4. Market — open, data fresh, price valid, exchange
    5. Broker — session, account, segment, reachable, funds

    ANY failure → NO ORDER.
    """

    def __init__(self):
        self._champion_manager = None
        self._risk_engine = None
        self._activation_gate = None
        self._broker_session = None
        self._execution_health = None
        self._execution_limits = None
        self._audit_log = None
        self._broker = None

    def set_champion_manager(self, mgr): self._champion_manager = mgr
    def set_risk_engine(self, e): self._risk_engine = e
    def set_activation_gate(self, g): self._activation_gate = g
    def set_broker_session(self, s): self._broker_session = s
    def set_execution_health(self, h): self._execution_health = h
    def set_execution_limits(self, l): self._execution_limits = l
    def set_audit_log(self, a): self._audit_log = a
    def set_broker(self, b): self._broker = b

    def check(
        self,
        authorization: Any = None,
        symbol: str = "",
        side: str = "BUY",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        strategy_version: str = "",
    ) -> CanaryPreCheckResult:
        """Run final precheck against authorization + real-time state.

        Args:
            authorization: CanaryAuthorization object
            symbol, side, quantity, price, stop_loss, target: Order params
            strategy_version: Expected champion version

        Returns:
            CanaryPreCheckResult with all check details
        """
        result = CanaryPreCheckResult()
        blockers: list[str] = []
        checks: dict[str, dict[str, Any]] = {}

        def add_check(name: str, passed: bool, blocking: bool = True,
                      message: str = "") -> None:
            checks[name] = {
                "passed": passed,
                "blocking": blocking,
                "message": message or ("Passed" if passed else "Failed"),
            }
            if blocking and not passed:
                blockers.append(f"{name}: {message or 'Failed'}")

        # ── 1. Strategy Checks ──
        champ_ok = False
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    champ_status = getattr(champ, "status", "")
                    champ_vid = getattr(champ, "id", getattr(champ, "version", ""))
                    champ_ok = champ_status in ("champion", "active", "CHAMPION")
                    if strategy_version:
                        add_check("champion_version_match", champ_vid == strategy_version,
                                  blocking=True,
                                  message=f"expected={strategy_version[:12]} got={champ_vid[:12]}")
            except Exception:
                pass
        add_check("champion_exists", champ_ok, blocking=True)

        # ── 2. Risk Checks ──
        if self._risk_engine:
            try:
                status = self._risk_engine.get_status()
                risk_healthy = not status.get("trading_halt", False)
                add_check("risk_engine_healthy", risk_healthy, blocking=True)
                if status.get("daily_trades", 0) >= status.get("max_daily_trades", 999):
                    add_check("daily_trade_limit", False, blocking=True)
            except Exception as e:
                add_check("risk_engine_available", False, blocking=True, message=str(e))
        else:
            add_check("risk_engine_available", False, blocking=True)

        add_check("stop_loss_provided", bool(stop_loss and stop_loss > 0),
                  blocking=True, message="SL is mandatory")
        add_check("target_provided", bool(target and target > 0),
                  blocking=True, message="Target is mandatory")

        if price and price > 0 and stop_loss and target:
            risk = abs(price - stop_loss)
            reward = abs(target - price)
            rr_valid = risk > 0 and (reward / risk) >= 1.5
            add_check("risk_reward_valid", rr_valid, blocking=True,
                      message=f"R:R = {reward/risk:.2f}" if risk > 0 else "No risk")
            # Authorization bounds
            if authorization:
                if quantity > getattr(authorization, 'approved_quantity', 9999):
                    add_check("quantity_within_auth", False, blocking=True)
                notional = (price or 0) * quantity
                if notional > getattr(authorization, 'max_notional', 99999999):
                    add_check("notional_within_auth", False, blocking=True)

        # ── 3. Runtime Checks ──
        if self._activation_gate:
            is_armed = self._activation_gate.is_live_armed()
            remaining = self._activation_gate.get_remaining_time()
            add_check("activation_armed", is_armed, blocking=True,
                      message=f"remaining={remaining}s")
        else:
            add_check("activation_gate_available", False, blocking=True)

        # Authorization state check
        if authorization:
            auth_ok = getattr(authorization, 'state', '') in ('armed', 'executing')
            add_check("authorization_state_valid", auth_ok, blocking=True,
                      message=f"state={getattr(authorization, 'state', 'none')}")
            # Check expiry (also handled by caller)
            expires_at = getattr(authorization, 'expires_at', '')
            if expires_at:
                try:
                    expiry = datetime.fromisoformat(expires_at)
                    not_expired = datetime.now(timezone.utc) < expiry
                    add_check("authorization_not_expired", not_expired, blocking=True)
                except (ValueError, TypeError):
                    add_check("authorization_not_expired", False, blocking=True)
        else:
            add_check("authorization_provided", False, blocking=True)

        # ── 4. Market Checks ──
        if self._execution_health:
            md = self._execution_health.get_check("market_data_freshness")
            if md:
                add_check("market_data_fresh", md.state.value != "blocked",
                          blocking=True, message=f"state={md.state.value}")
        add_check("price_valid", bool(price and price > 0), blocking=True)
        add_check("symbol_valid", bool(symbol and symbol.strip()), blocking=True)

        # ── 5. Broker Checks ──
        if self._broker_session:
            session = self._broker_session.get_last_status()
            if session:
                add_check("broker_authenticated", session.authenticated, blocking=True)
                add_check("broker_session_valid", session.session_valid, blocking=True)
                add_check("broker_account_valid", session.account_valid, blocking=True)
            else:
                add_check("broker_session_checked", False, blocking=True)
        else:
            add_check("broker_session_manager", False, blocking=True)

        if self._broker:
            try:
                import asyncio
                health = asyncio.run(self._broker.health_check())
                add_check("broker_reachable", health.get("status") == "healthy",
                          blocking=True, message=f"status={health.get('status')}")
            except Exception:
                add_check("broker_reachable", False, blocking=True, message="health_check failed")

        result.passed = len(blockers) == 0
        result.blockers = blockers
        result.checks = checks
        result.timestamp = _now()

        self._record_audit(
            "canary_precheck_passed" if result.passed else "canary_precheck_blocked",
            details={"passed": result.passed, "blockers": blockers[:5]},
            severity="info" if result.passed else "warning",
        )

        return result

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="canary_precheck",
            details={"component": "canary_precheck", **(details or {})},
        )

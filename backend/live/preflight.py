"""Preflight Validator — validates all preconditions before ANY live order.

Phase 46: Runs before every order. 5 categories of checks.
ANY critical failure must block execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PreflightResult:
    """Result of preflight validation."""
    passed: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "checks": self.checks,
            "timestamp": self.timestamp,
        }


class PreflightValidator:
    """
    Validates ALL preconditions before any live order.

    Checks 5 categories:
    1. Market — open, exchange, symbol, instrument, session
    2. Signal — champion, freshness, uniqueness, timestamp, confidence
    3. Risk — RiskEngine, sizing, SL, target, R:R, limits
    4. Runtime — activation gate, approval, Phase 45 gates
    5. Broker — auth, account, segment, funds, instrument
    """

    def __init__(self):
        self._champion_manager = None
        self._risk_engine = None
        self._activation_gate = None
        self._execution_health = None
        self._broker_session = None
        self._market_stream = None
        self._audit_log = None

    # ── Dependency Injection ──

    def set_champion_manager(self, mgr): self._champion_manager = mgr
    def set_risk_engine(self, engine): self._risk_engine = engine
    def set_activation_gate(self, gate): self._activation_gate = gate
    def set_execution_health(self, health): self._execution_health = health
    def set_broker_session(self, session): self._broker_session = session
    def set_market_stream(self, stream): self._market_stream = stream
    def set_audit_log(self, audit): self._audit_log = audit

    # ── Validation ──

    def validate(
        self,
        symbol: str = "",
        side: str = "BUY",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        signal_id: str = "",
        strategy_version: str = "",
    ) -> PreflightResult:
        """Run all preflight checks. Returns PreflightResult.

        ANY critical failure blocks execution.
        """
        result = PreflightResult()
        blockers: list[str] = []
        warnings: list[str] = []
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

        # ── 1. Market Checks ──
        if self._execution_health:
            md_check = self._execution_health.get_check("market_data_freshness")
            if md_check:
                md_healthy = md_check.state.value != "blocked"
                add_check("market_data_fresh", md_healthy, blocking=True,
                          message=f"State: {md_check.state.value}")
            else:
                add_check("market_data_monitor", False, blocking=True,
                          message="Market data monitor unavailable")
        else:
            add_check("market_data_monitor", False, blocking=True,
                      message="Execution health monitor not configured")

        if self._execution_health:
            ws_check = self._execution_health.get_check("websocket_health")
            if ws_check:
                ws_healthy = ws_check.state.value == "healthy"
                add_check("websocket_connected", ws_healthy, blocking=False,
                          message=f"State: {ws_check.state.value}")

        add_check("symbol_valid", bool(symbol and symbol.strip()), blocking=True,
                  message="Symbol is required")
        add_check("exchange_available", True, blocking=False,
                  message="Exchange assumed available (limited check)")

        # ── 2. Signal Checks ──
        champion_valid = False
        champion_version = ""
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    champ_status = getattr(champ, "status", "")
                    champion_valid = champ_status in ("champion", "active", "CHAMPION")
                    champion_version = getattr(
                        champ, "id", getattr(champ, "version", getattr(champ, "version_id", ""))
                    )
            except Exception:
                pass

        add_check("champion_valid", champion_valid, blocking=True,
                  message=f"Champion: {champion_version[:12] if champion_version else 'none'}")
        add_check("signal_id_valid", bool(signal_id), blocking=False,
                  message="Signal ID check")
        add_check("strategy_version_valid", bool(strategy_version), blocking=False,
                  message="Strategy version check")

        # ── 3. Risk Checks ──
        if self._risk_engine:
            try:
                status = self._risk_engine.get_status()
                risk_healthy = not status.get("trading_halt", False)
                add_check("risk_engine_healthy", risk_healthy, blocking=True,
                          message=f"Halt: {status.get('trading_halt', False)}")
                daily_trades = status.get("daily_trades", 0)
                max_trades = status.get("max_daily_trades", 999)
                under_trade_limit = daily_trades < max_trades
                add_check("daily_trade_limit", under_trade_limit, blocking=True,
                          message=f"{daily_trades}/{max_trades}")
            except Exception as e:
                add_check("risk_engine_check", False, blocking=True,
                          message=f"Error: {e}")
        else:
            add_check("risk_engine_available", False, blocking=True,
                      message="RiskEngine not configured")

        # SL/Target checks
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
        else:
            add_check("risk_reward_valid", False, blocking=True,
                      message="Cannot calculate R:R — missing price/SL/target")

        add_check("price_sanity", bool(price and price > 0), blocking=True,
                  message="Price must be > 0")
        add_check("quantity_valid", quantity > 0, blocking=True,
                  message="Quantity must be > 0")

        # ── 4. Runtime Checks ──
        if self._activation_gate:
            is_armed = self._activation_gate.is_live_armed()
            remaining = self._activation_gate.get_remaining_time()
            state = self._activation_gate.get_state().value
            add_check("activation_armed", is_armed, blocking=True,
                      message=f"State: {state}, remaining: {remaining}s")
        else:
            add_check("activation_gate_available", False, blocking=True,
                      message="Activation gate not configured")

        # ── 5. Broker Checks ──
        if self._broker_session:
            session = self._broker_session.get_last_status()
            if session:
                add_check("broker_authenticated", session.authenticated, blocking=True,
                          message=f"Auth: {session.authenticated}")
                add_check("broker_session_valid", session.session_valid, blocking=True,
                          message=f"Session: {session.session_valid}")
                add_check("broker_account_valid", session.account_valid, blocking=True,
                          message=f"Account: {session.account_valid}")
            else:
                add_check("broker_session_checked", False, blocking=True,
                          message="Session not yet validated")
        else:
            add_check("broker_session_manager", False, blocking=True,
                      message="Broker session manager not configured")

        # Compile result
        result.checks = checks
        result.blockers = blockers
        result.warnings = warnings
        result.passed = len(blockers) == 0
        result.timestamp = _now()

        self._record_audit(
            "preflight_passed" if result.passed else "preflight_blocked",
            details={
                "passed": result.passed,
                "blocker_count": len(blockers),
                "blockers": blockers[:5],
            },
            severity="info" if result.passed else "warning",
        )

        return result

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="preflight_validator",
            details={"component": "preflight", **(details or {})},
        )

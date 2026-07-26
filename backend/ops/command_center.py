"""Command Center Engine — aggregates all system state into a unified snapshot.

Phase 52: Orchestration only. Delegates to existing components.
Never contains secrets.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ops.command_snapshot import (
    CommandCenterSnapshot, SystemSnapshot, MarketSnapshot, BrokerSnapshot,
    ExecutionSnapshot, PositionSnapshot, RiskSnapshot, CanarySnapshot,
    RolloutSnapshot, ReconciliationSnapshot, IncidentSummarySnapshot,
    RecoverySnapshot, IntegritySnapshot, SafetySnapshot, ApprovalSnapshot,
    MetricsSnapshot, RealLiveSnapshot, UnifiedStatus, UNIFIED_STATUS_PRIORITY,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CommandCenterEngine:
    """
    Aggregates all system state into a unified CommandCenterSnapshot.

    All dependencies optional. Engine degrades gracefully if
    components are not configured.
    No secrets in snapshot.
    """

    def __init__(self):
        # DI slots
        self._health_monitor = None
        self._heartbeat = None
        self._market_data_wd = None
        self._broker_wd = None
        self._execution_wd = None
        self._alert_mgr = None
        self._incident_mgr = None
        self._event_bus = None
        self._recovery_mgr = None
        self._daily_rec = None
        self._config_monitor = None
        self._rollout_engine = None
        self._canary_lifecycle = None
        self._activation_gate = None
        self._runtime_mgr = None
        self._metrics = None
        self._risk_engine = None
        self._champion_manager = None
        self._controlled_live = None

    # ── DI Setters ──

    def set_health_monitor(self, m): self._health_monitor = m
    def set_heartbeat(self, h): self._heartbeat = h
    def set_market_data_watchdog(self, w): self._market_data_wd = w
    def set_broker_watchdog(self, w): self._broker_wd = w
    def set_execution_watchdog(self, w): self._execution_wd = w
    def set_alert_manager(self, a): self._alert_mgr = a
    def set_incident_manager(self, i): self._incident_mgr = i
    def set_event_bus(self, b): self._event_bus = b
    def set_recovery_manager(self, r): self._recovery_mgr = r
    def set_daily_reconciliation(self, r): self._daily_rec = r
    def set_config_monitor(self, c): self._config_monitor = c
    def set_rollout_engine(self, r): self._rollout_engine = r
    def set_canary_lifecycle(self, c): self._canary_lifecycle = c
    def set_activation_gate(self, g): self._activation_gate = g
    def set_runtime_mgr(self, m): self._runtime_mgr = m
    def set_metrics(self, m): self._metrics = m
    def set_risk_engine(self, r): self._risk_engine = r
    def set_champion_manager(self, c): self._champion_manager = c
    def set_controlled_live(self, c): self._controlled_live = c

    # ── Snapshot Builder ──

    def build_snapshot(self) -> CommandCenterSnapshot:
        """Build a complete unified snapshot from all components."""
        snap = CommandCenterSnapshot()

        # System
        snap.system = self._build_system()
        snap.market = self._build_market()
        snap.broker = self._build_broker()
        snap.execution = self._build_execution()
        snap.positions = self._build_positions()
        snap.risk = self._build_risk()
        snap.canary = self._build_canary()
        snap.rollout = self._build_rollout()
        snap.reconciliation = self._build_reconciliation()
        snap.incidents = self._build_incidents()
        snap.recovery = self._build_recovery()
        snap.integrity = self._build_integrity()
        snap.safety = self._build_safety()
        snap.approval = self._build_approval()
        snap.metrics = self._build_metrics()
        snap.real_live = self._build_real_live()
        snap.unified_status = self._compute_unified_status(snap)

        return snap

    def _compute_unified_status(self, snap: CommandCenterSnapshot) -> str:
        """Compute overall status using safety-first priority ordering."""
        conditions = []

        if snap.system.halted:
            conditions.append(UnifiedStatus.HALTED)
        if snap.recovery.recovery_required:
            conditions.append(UnifiedStatus.RECOVERY_REQUIRED)
        if snap.rollout.rollback_active:
            conditions.append(UnifiedStatus.ROLLBACK_ACTIVE)
        if snap.system.trading_blocked or snap.risk.risk_blocked:
            conditions.append(UnifiedStatus.TRADING_BLOCKED)
        if snap.incidents.critical_count > 0 or snap.incidents.emergency_count > 0:
            conditions.append(UnifiedStatus.INCIDENT_ACTIVE)
        if snap.system.degraded:
            conditions.append(UnifiedStatus.DEGRADED)

        # Return highest priority condition, or HEALTHY
        for status in UNIFIED_STATUS_PRIORITY:
            if status in conditions:
                return status
        return UnifiedStatus.HEALTHY

    def _build_system(self) -> SystemSnapshot:
        s = SystemSnapshot()
        if self._health_monitor:
            try:
                snap = self._health_monitor.snapshot()
                s.operational_state = snap.get("status", "unknown")
                s.health_score = 100.0 if snap.get("status") == "healthy" else 50.0
                s.uptime_seconds = snap.get("uptime_seconds", 0)
                s.degraded = snap.get("status") in ("degraded", "warning")
                s.trading_blocked = snap.get("status") in ("critical", "halted")
                s.halted = snap.get("status") == "halted"
                s.recovery_required = snap.get("status") == "recovery_required"
            except Exception:
                pass
        if self._recovery_mgr:
            try:
                rs = self._recovery_mgr.get_state()
                if rs == "recovery_required":
                    s.recovery_required = True
                elif rs == "shutdown" or rs == "halted":
                    s.halted = True
            except Exception:
                pass
        return s

    def _build_market(self) -> MarketSnapshot:
        m = MarketSnapshot()
        if self._market_data_wd:
            try:
                health = self._market_data_wd.get_health()
                m.connected = health.websocket_connected
                m.last_tick = health.last_tick_timestamp
                m.tick_age_ms = health.tick_age_ms
                m.stale = health.state in ("stale", "disconnected", "blocked")
                m.data_quality = health.state
            except Exception:
                pass
        return m

    def _build_broker(self) -> BrokerSnapshot:
        b = BrokerSnapshot()
        if self._broker_wd:
            try:
                health = self._broker_wd.get_health()
                b.connected = health.state not in ("disconnected", "not_configured")
                b.authenticated = health.authenticated
                b.session_valid = health.session_valid
                b.api_health = health.state
            except Exception:
                pass
        return b

    def _build_execution(self) -> ExecutionSnapshot:
        e = ExecutionSnapshot()
        if self._execution_wd:
            try:
                health = self._execution_wd.get_health()
                e.blocked = health.state != "healthy"
                e.unknown_orders = health.unknown_orders
                e.duplicate_attempts = health.duplicate_attempts
                e.execution_health = health.state
            except Exception:
                pass
        return e

    def _build_positions(self) -> PositionSnapshot:
        p = PositionSnapshot()
        if self._risk_engine:
            try:
                status = self._risk_engine.get_status()
                if isinstance(status, dict):
                    p.open_positions = status.get("open_positions", 0)
                    p.total_exposure = status.get("total_exposure", 0)
                    p.realized_pnl = status.get("realized_pnl", 0)
                    p.unrealized_pnl = status.get("unrealized_pnl", 0)
                    p.net_pnl = p.realized_pnl + p.unrealized_pnl
            except Exception:
                pass
        return p

    def _build_risk(self) -> RiskSnapshot:
        r = RiskSnapshot()
        if self._risk_engine:
            try:
                status = self._risk_engine.get_status()
                if isinstance(status, dict):
                    r.risk_engine_available = not status.get("trading_halt", True)
                    r.daily_loss = abs(status.get("daily_loss", 0))
                    r.daily_loss_limit = status.get("max_daily_loss", 0)
                    r.drawdown_pct = status.get("drawdown", 0)
                    r.exposure = status.get("total_exposure", 0)
                    r.risk_blocked = r.risk_blocked or status.get("trading_halt", False)
            except Exception:
                pass
        if self._alert_mgr:
            try:
                alerts = self._alert_mgr.get_active()
                for a in alerts:
                    if a.severity in ("critical", "emergency"):
                        r.risk_blocked = True
            except Exception:
                pass
        # Kill switch check
        if self._activation_gate:
            try:
                pass  # Covered in safety section
            except Exception:
                pass
        return r

    def _build_canary(self) -> CanarySnapshot:
        c = CanarySnapshot()
        if self._canary_lifecycle:
            try:
                status = self._canary_lifecycle.get_status()
                c.active = status.get("active_count", 0) > 0
                auths = self._canary_lifecycle.get_all_authorizations()
                if auths:
                    last = auths[-1]
                    c.current_canary = last.authorization_id
                    c.authorization_state = last.state
                    # Find evaluation
                    if self._incident_mgr:
                        c.evaluation_status = "pending"
                if status.get("completed_count", 0) > 0:
                    c.evaluation_status = "evaluated"
            except Exception:
                pass
        return c

    def _build_rollout(self) -> RolloutSnapshot:
        r = RolloutSnapshot()
        if self._rollout_engine:
            try:
                status = self._rollout_engine.get_status()
                r.current_stage = status.get("current_stage", "")
                r.rollback_active = status.get("current_stage") == "rollback"
                r.rollback_reason = status.get("rollback_reason", "")
                r.pending_review = status.get("rollback_active", False)
            except Exception:
                pass
        return r

    def _build_reconciliation(self) -> ReconciliationSnapshot:
        r = ReconciliationSnapshot()
        if self._daily_rec:
            try:
                reports = self._daily_rec.get_reports(limit=1)
                if reports:
                    last = reports[0]
                    r.mismatches = last.get("mismatched_orders", 0) + last.get("mismatched_positions", 0)
                    r.orders_ok = last.get("mismatched_orders", 0) == 0
                    r.positions_ok = last.get("mismatched_positions", 0) == 0
                    r.last_reconciliation = last.get("timestamp", "")
            except Exception:
                pass
        return r

    def _build_incidents(self) -> IncidentSummarySnapshot:
        i = IncidentSummarySnapshot()
        if self._incident_mgr:
            try:
                i.open_count = len(self._incident_mgr.get_open())
                criticals = self._incident_mgr.get_critical()
                i.critical_count = len([c for c in criticals if c.severity == "critical"])
                i.emergency_count = len([c for c in criticals if c.severity == "emergency"])
                all_incidents = self._incident_mgr.get_all()
                if all_incidents:
                    i.latest_incident = all_incidents[-1].title
            except Exception:
                pass
        return i

    def _build_recovery(self) -> RecoverySnapshot:
        r = RecoverySnapshot()
        if self._recovery_mgr:
            try:
                state = self._recovery_mgr.get_state()
                r.recovery_required = state in ("recovery_required",)
                r.recovery_state = state
                r.auto_resume_allowed = False  # Always false by design
            except Exception:
                pass
        return r

    def _build_integrity(self) -> IntegritySnapshot:
        i = IntegritySnapshot()
        if self._config_monitor:
            try:
                result = self._config_monitor.check_integrity()
                i.config_match = result.config_hash_unchanged
                i.champion_match = result.champion_unchanged
                i.integrity_status = "valid" if result.passed else "failure"
            except Exception:
                pass
        return i

    def _build_safety(self) -> SafetySnapshot:
        s = SafetySnapshot()
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        s.phase43_lock = bool(PHASE_43_LIVE_EXECUTION_LOCK)

        if self._runtime_mgr:
            try:
                s.can_execute_live = self._runtime_mgr.can_execute_live()
            except Exception:
                pass
        if self._activation_gate:
            try:
                gate_state = self._activation_gate.get_state().value
                s.activation_state = gate_state
            except Exception:
                pass
        safe = s.phase43_lock and not s.can_execute_live
        safe = safe and s.activation_state == "locked"
        s.all_safety_gates_passed = bool(safe)
        s.overall_safety_status = "locked" if s.all_safety_gates_passed else "warning"
        return s

    def _build_approval(self) -> ApprovalSnapshot:
        a = ApprovalSnapshot()
        from live.final_approval import FinalApprovalEngine
        try:
            engine = FinalApprovalEngine()
            records = engine.get_all_records()
            if records:
                last = records[-1]
                a.latest_approval = getattr(last, "approval_id", "")
                a.approval_state = getattr(last, "status", "")
                a.reviewer = getattr(last, "reviewer", "")
                a.expires_at = getattr(last, "expires_at", "")
        except Exception:
            pass
        return a

    def _build_metrics(self) -> MetricsSnapshot:
        m = MetricsSnapshot()
        if self._metrics:
            try:
                data = self._metrics.get_metrics()
                m.uptime_hours = data.get("uptime_hours", 0)
                m.mtta_seconds = data.get("mean_time_to_acknowledge_seconds", 0)
                m.mttr_seconds = data.get("mean_time_to_resolve_seconds", 0)
                m.heartbeat_rate = data.get("heartbeat_success_rate", 100)
                m.incident_count = data.get("incident_count", 0)
                m.rollback_count = data.get("rollback_count", 0)
                m.recovery_count = data.get("recovery_count", 0)
                m.health_score = self._metrics.get_health_score()
            except Exception:
                pass
        return m

    def _build_real_live(self) -> RealLiveSnapshot:
        """Phase 55: Build real live status snapshot."""
        rl = RealLiveSnapshot()

        if self._controlled_live:
            try:
                status = self._controlled_live.get_status()
                rl.controlled_live_active = status.get("state") == "active"
                rl.trades_remaining = status.get("trades_remaining", 0)
                rl.current_symbol = status.get("execution_snapshot", {}).get("symbol", "")
                rl.broker_status = status.get("broker_status", "")
                rl.order_status = status.get("broker_status", "")
                rl.reconciliation_status = (
                    "reconciled" if status.get("position_reconciled") else "pending"
                )
                rl.protective_order_status = status.get("protective_order_status", "not_verified")
                rl.sl_status = "present" if status.get("execution_snapshot", {}).get("stop_loss") else "missing"
                rl.target_status = "present" if status.get("execution_snapshot", {}).get("target") else "missing"

                # Post-trade evaluation
                try:
                    post = self._controlled_live.get_post_trade_evaluation()
                    rl.post_trade_evaluation = post
                except Exception:
                    pass

                # Authorization info
                try:
                    real = self._controlled_live.get_real_status()
                    rl.authorization_status = real.get("state", "")
                    rl.authorization_expiry = real.get("completed_at", "")
                except Exception:
                    pass

                rl.next_authorization_required = rl.trades_remaining <= 0
            except Exception:
                pass

        # Kill switch check
        if self._activation_gate:
            try:
                gate_status = self._activation_gate.get_status()
                rl.kill_switch = gate_status.get("state") in ("kill_switched",)
            except Exception:
                pass

        # Incident check
        if self._incident_mgr:
            try:
                open_incidents = self._incident_mgr.get_open()
                if open_incidents:
                    rl.incident_status = f"{len(open_incidents)} open incidents"
            except Exception:
                pass

        return rl

    # ── Section Builders (for per-section API endpoints) ──

    def get_system_status(self) -> dict[str, Any]:
        return self._build_system().to_dict()

    def get_trading_status(self) -> dict[str, Any]:
        snap = self.build_snapshot()
        return {
            "unified_status": snap.unified_status,
            "market": snap.market.to_dict(),
            "broker": snap.broker.to_dict(),
            "execution": snap.execution.to_dict(),
            "positions": snap.positions.to_dict(),
        }

    def get_safety_status(self) -> dict[str, Any]:
        return self._build_safety().to_dict()

    def get_risk_status(self) -> dict[str, Any]:
        return self._build_risk().to_dict()

    def get_incident_summary(self) -> dict[str, Any]:
        return self._build_incidents().to_dict()

    def get_rollout_status(self) -> dict[str, Any]:
        return self._build_rollout().to_dict()

    def get_reconciliation_status(self) -> dict[str, Any]:
        return self._build_reconciliation().to_dict()

    def get_recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._event_bus:
            return self._event_bus.get_recent(limit=limit)
        return []

    def get_operational_summary(self) -> dict[str, Any]:
        snap = self.build_snapshot()
        return {
            "unified_status": snap.unified_status,
            "system": snap.system.to_dict(),
            "safety": snap.safety.to_dict(),
            "risk": snap.risk.to_dict(),
            "incidents": snap.incidents.to_dict(),
            "recovery": snap.recovery.to_dict(),
            "metrics": snap.metrics.to_dict(),
        }

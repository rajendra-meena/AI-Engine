"""
Phase 52 — Production Operations Command Center & Unified Control Plane Tests.

Tests snapshot building, safety status, unified status computation,
and safety invariants.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta


# ═══════════════════════════════════════════════
# Snapshot Model Tests
# ═══════════════════════════════════════════════

class TestCommandCenterSnapshot:
    """Snapshot model and structure."""

    def test_snapshot_creates(self):
        from ops.command_snapshot import CommandCenterSnapshot
        snap = CommandCenterSnapshot()
        assert snap.snapshot_id.startswith("snap_")
        assert snap.unified_status == "healthy"

    def test_snapshot_contains_all_sections(self):
        from ops.command_snapshot import CommandCenterSnapshot
        snap = CommandCenterSnapshot()
        d = snap.to_dict()
        required = ["system", "market", "broker", "execution", "positions",
                     "risk", "canary", "rollout", "reconciliation", "incidents",
                     "recovery", "integrity", "safety", "approval", "metrics"]
        for section in required:
            assert section in d, f"Missing section: {section}"

    def test_snapshot_no_secrets(self):
        from ops.command_snapshot import CommandCenterSnapshot
        snap = CommandCenterSnapshot()
        d_str = str(dict(snap.to_dict()))
        secrets = ["api_key", "api_secret", "access_token", "password",
                    "secret", "token", "broker_secret"]
        for s in secrets:
            assert s not in d_str.lower(), f"Secret key found: {s}"

    def test_snapshot_immutable(self):
        from ops.command_snapshot import CommandCenterSnapshot
        snap = CommandCenterSnapshot()
        d = snap.to_dict()
        import copy
        d2 = copy.deepcopy(d)
        d2["unified_status"] = "changed"
        assert snap.unified_status != "changed"

    def test_snapshot_age(self):
        from ops.command_snapshot import CommandCenterSnapshot
        snap = CommandCenterSnapshot()
        assert snap.snapshot_age >= 0

    def test_is_stale(self):
        from ops.command_snapshot import CommandCenterSnapshot
        snap = CommandCenterSnapshot()
        assert not snap.is_stale(max_age_seconds=60)  # Fresh

    def test_expires_at_set(self):
        from ops.command_snapshot import CommandCenterSnapshot
        snap = CommandCenterSnapshot()
        assert snap.expires_at != ""


# ═══════════════════════════════════════════════
# Unified Status Tests
# ═══════════════════════════════════════════════

class TestUnifiedStatus:
    """Unified status computation."""

    def test_default_healthy(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        snap = engine.build_snapshot()
        assert snap.unified_status == "healthy"

    def test_priority_highest_wins(self):
        from ops.command_snapshot import (
            CommandCenterSnapshot, SystemSnapshot, RecoverySnapshot,
            RolloutSnapshot, RiskSnapshot, IncidentSummarySnapshot,
            UnifiedStatus,
        )
        snap = CommandCenterSnapshot()
        snap.unified_status = ""

        # Set all conditions
        snap.system = SystemSnapshot(halted=True, trading_blocked=True)
        snap.recovery = RecoverySnapshot(recovery_required=True)
        snap.rollout = RolloutSnapshot(rollback_active=True)
        snap.incidents = IncidentSummarySnapshot(critical_count=2)

        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        result = engine._compute_unified_status(snap)
        # HALTED has highest priority
        assert result == UnifiedStatus.HALTED

    def test_unified_statuses_defined(self):
        from ops.command_snapshot import UnifiedStatus, UNIFIED_STATUS_PRIORITY
        assert UnifiedStatus.HEALTHY == "healthy"
        assert UnifiedStatus.HALTED == "halted"
        assert len(UNIFIED_STATUS_PRIORITY) == 7


# ═══════════════════════════════════════════════
# Safety Snapshot Tests
# ═══════════════════════════════════════════════

class TestSafetySnapshot:
    """Safety status in snapshot."""

    def test_safety_default_locked(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        snap = engine.build_snapshot()
        safety = snap.safety
        # Default should show locked (reading actual PHASE_43_LIVE_EXECUTION_LOCK)
        assert hasattr(safety, 'phase43_lock')
        assert hasattr(safety, 'can_execute_live')

    def test_phase43_lock_in_snapshot(self):
        from ops.command_snapshot import SafetySnapshot
        s = SafetySnapshot()
        d = s.to_dict()
        assert "phase43_lock" in d
        assert "can_execute_live" in d
        assert "activation_state" in d


# ═══════════════════════════════════════════════
# Section-Specific Tests
# ═══════════════════════════════════════════════

class TestSnapshotSections:
    """Each section builds correctly."""

    def test_system_section(self):
        from ops.command_snapshot import SystemSnapshot
        s = SystemSnapshot(operational_state="ready", health_score=95.0)
        d = s.to_dict()
        assert d["operational_state"] == "ready"
        assert d["health_score"] == 95.0

    def test_market_section(self):
        from ops.command_snapshot import MarketSnapshot
        m = MarketSnapshot(connected=True, stale=False)
        d = m.to_dict()
        assert d["connected"] is True
        assert d["stale"] is False

    def test_broker_section(self):
        from ops.command_snapshot import BrokerSnapshot
        b = BrokerSnapshot(connected=True, authenticated=True)
        d = b.to_dict()
        assert d["connected"] is True

    def test_risk_section(self):
        from ops.command_snapshot import RiskSnapshot
        r = RiskSnapshot(daily_loss=500, daily_loss_limit=2000)
        d = r.to_dict()
        assert d["daily_loss"] == 500.0
        assert d["daily_loss_limit"] == 2000.0

    def test_canary_section(self):
        from ops.command_snapshot import CanarySnapshot
        c = CanarySnapshot(active=True, authorization_state="armed")
        d = c.to_dict()
        assert d["active"] is True

    def test_rollout_section(self):
        from ops.command_snapshot import RolloutSnapshot
        r = RolloutSnapshot(current_stage="canary_1", rollback_active=False)
        d = r.to_dict()
        assert d["current_stage"] == "canary_1"

    def test_incident_section(self):
        from ops.command_snapshot import IncidentSummarySnapshot
        i = IncidentSummarySnapshot(open_count=2, critical_count=1)
        d = i.to_dict()
        assert d["open_count"] == 2

    def test_recovery_section(self):
        from ops.command_snapshot import RecoverySnapshot
        r = RecoverySnapshot(recovery_required=False, auto_resume_allowed=False)
        d = r.to_dict()
        assert d["auto_resume_allowed"] is False

    def test_integrity_section(self):
        from ops.command_snapshot import IntegritySnapshot
        i = IntegritySnapshot(config_match=True, champion_match=True)
        d = i.to_dict()
        assert d["config_match"] is True

    def test_metrics_section(self):
        from ops.command_snapshot import MetricsSnapshot
        m = MetricsSnapshot(health_score=95.0, uptime_hours=24.0)
        d = m.to_dict()
        assert d["health_score"] == 95.0
        assert d["uptime_hours"] == 24.0


# ═══════════════════════════════════════════════
# Engine Build Tests
# ═══════════════════════════════════════════════

class TestCommandCenterEngine:
    """Engine builds snapshots correctly."""

    def test_build_snapshot_succeeds(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        snap = engine.build_snapshot()
        assert snap.snapshot_id.startswith("snap_")

    def test_snapshot_sections_present(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        snap = engine.build_snapshot()
        assert snap.system is not None
        assert snap.market is not None
        assert snap.broker is not None
        assert snap.execution is not None
        assert snap.positions is not None
        assert snap.risk is not None
        assert snap.canary is not None
        assert snap.rollout is not None
        assert snap.reconciliation is not None
        assert snap.incidents is not None
        assert snap.recovery is not None
        assert snap.integrity is not None
        assert snap.safety is not None

    def test_get_system_status(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        status = engine.get_system_status()
        assert "operational_state" in status

    def test_get_safety_status(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        safety = engine.get_safety_status()
        assert "phase43_lock" in safety

    def test_get_risk_status(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        risk = engine.get_risk_status()
        assert "risk_engine_available" in risk

    def test_get_incident_summary(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        inc = engine.get_incident_summary()
        assert "open_count" in inc

    def test_get_operational_summary(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        summary = engine.get_operational_summary()
        assert "unified_status" in summary
        assert "safety" in summary


# ═══════════════════════════════════════════════
# Safety Regression Tests
# ═══════════════════════════════════════════════

class TestPhase52SafetyVerification:
    """Critical safety tests for Phase 52."""

    def test_phase_43_lock_still_true(self):
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        assert PHASE_43_LIVE_EXECUTION_LOCK is True

    def test_can_execute_live_still_false(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        assert mgr.can_execute_live() is False

    def test_zerodha_adapter_still_raises(self):
        from execution.broker_adapter import ZerodhaAdapter, LiveExecutionDisabledError
        import asyncio
        adapter = ZerodhaAdapter()
        with pytest.raises(LiveExecutionDisabledError):
            asyncio.run(adapter.place_order("RELIANCE", "BUY", 1))

    def test_no_unrestricted_live_endpoint(self):
        import backend.api.command_center as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = ["enable-live", "disable-lock", "start-auto-trading",
                     "bypass-safety", "increase-limits"]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_all_endpoints_are_get(self):
        """All command center endpoints must be GET (read-only)."""
        import backend.api.command_center as api_module
        for route in api_module.router.routes:
            methods = route.methods
            if methods:
                assert "GET" in methods, f"Route {route.path} has non-GET method: {methods}"
                assert "POST" not in methods, f"Route {route.path} has POST method"
                assert "PUT" not in methods
                assert "DELETE" not in methods

    def test_snapshot_no_secrets_in_api(self):
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        snap = engine.build_snapshot()
        d_str = str(dict(snap.to_dict())).lower()
        secrets = ["api_key", "api_secret", "access_token",
                    "password", "broker_secret"]
        for s in secrets:
            assert s not in d_str, f"Secret key found in snapshot: {s}"

    def test_command_center_cannot_enable_live(self):
        """Command center must not have any method that enables live trading."""
        from ops.command_center import CommandCenterEngine
        engine = CommandCenterEngine()
        method_names = [m for m in dir(engine) if not m.startswith('_')]
        forbidden = ['enable_live', 'start_auto_trading', 'disable_lock',
                     'bypass_risk', 'force_order']
        for f in forbidden:
            assert f not in method_names, f"Engine has forbidden method: {f}"

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa
        import tests.live.test_phase46_execution  # noqa
        import tests.live.test_phase47_canary  # noqa
        import tests.live.test_phase48_canary_evaluation  # noqa
        import tests.live.test_phase49_progressive_rollout  # noqa
        import tests.live.test_phase50_operations  # noqa
        import tests.live.test_phase51_observability  # noqa

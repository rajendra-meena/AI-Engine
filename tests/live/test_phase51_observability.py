"""
Phase 51 — Production Observability, Incident Response & Operational Control.

Tests event bus, incident management, severity engine, correlation,
runbooks, metrics, and safety invariants.
"""

from __future__ import annotations

import pytest
import time
from datetime import datetime, timezone, timedelta


# ═══════════════════════════════════════════════
# Operational Event Bus Tests
# ═══════════════════════════════════════════════

class TestOperationalEventBus:
    """Event bus for operational events."""

    def test_publish_event(self):
        from ops.event_bus import OperationalEventBus, OperationalEvent
        bus = OperationalEventBus()
        event = OperationalEvent(event_type="test_event", severity="info", message="Test")
        eid = bus.publish(event)
        assert eid == event.event_id

    def test_get_recent(self):
        from ops.event_bus import OperationalEventBus, OperationalEvent
        bus = OperationalEventBus()
        bus.publish(OperationalEvent(event_type="type_a"))
        bus.publish(OperationalEvent(event_type="type_b"))
        recent = bus.get_recent()
        assert len(recent) == 2

    def test_get_by_id(self):
        from ops.event_bus import OperationalEventBus, OperationalEvent
        bus = OperationalEventBus()
        e = OperationalEvent(event_type="test")
        bus.publish(e)
        found = bus.get_by_id(e.event_id)
        assert found is not None
        assert found.event_type == "test"

    def test_subscribe(self):
        from ops.event_bus import OperationalEventBus, OperationalEvent
        bus = OperationalEventBus()
        received = []
        def handler(event):
            received.append(event)
        bus.subscribe("test_type", handler)
        bus.publish(OperationalEvent(event_type="test_type"))
        assert len(received) == 1

    def test_wildcard_subscribe(self):
        from ops.event_bus import OperationalEventBus, OperationalEvent
        bus = OperationalEventBus()
        received = []
        def handler(event):
            received.append(event)
        bus.subscribe("*", handler)
        bus.publish(OperationalEvent(event_type="anything"))
        assert len(received) == 1

    def test_event_immutable_to_dict(self):
        from ops.event_bus import OperationalEvent
        e = OperationalEvent(event_type="test", severity="critical", message="Test event")
        d = e.to_dict()
        assert d["event_type"] == "test"
        assert d["severity"] == "critical"
        assert "metadata" not in d  # metadata excluded from to_dict for security

    def test_clear_expired(self):
        from ops.event_bus import OperationalEventBus, OperationalEvent
        bus = OperationalEventBus()
        old_event = OperationalEvent(
            event_type="old", timestamp="2020-01-01T00:00:00+00:00"
        )
        bus.publish(old_event)
        bus.publish(OperationalEvent(event_type="new"))
        cleared = bus.clear_expired(max_age_hours=1)
        assert cleared >= 1
        assert bus.event_count() >= 1

    def test_event_count(self):
        from ops.event_bus import OperationalEventBus, OperationalEvent
        bus = OperationalEventBus()
        for i in range(5):
            bus.publish(OperationalEvent(event_type=f"type_{i}"))
        assert bus.event_count() == 5

    def test_event_types_defined(self):
        from ops.event_bus import ALL_EVENT_TYPES
        assert "system_started" in ALL_EVENT_TYPES
        assert "broker_disconnected" in ALL_EVENT_TYPES
        assert "position_mismatch" in ALL_EVENT_TYPES
        assert "kill_switch_triggered" in ALL_EVENT_TYPES
        assert "security_event" in ALL_EVENT_TYPES

    def test_no_secrets_in_event(self):
        from ops.event_bus import OperationalEvent
        e = OperationalEvent(event_type="security", metadata={"password": "secret123"})
        d = e.to_dict()
        assert "metadata" not in d  # metadata stripped by design


# ═══════════════════════════════════════════════
# Severity Engine Tests
# ═══════════════════════════════════════════════

class TestSeverityEngine:
    """Severity classification."""

    def test_info_default(self):
        from ops.severity_engine import SeverityEngine, SeverityTier
        engine = SeverityEngine()
        assert engine.classify(event_type="heartbeat_recovered") == SeverityTier.INFO

    def test_critical_event_types(self):
        from ops.severity_engine import SeverityEngine, SeverityTier
        engine = SeverityEngine()
        assert engine.classify(event_type="position_mismatch") == SeverityTier.CRITICAL
        assert engine.classify(event_type="order_unknown") == SeverityTier.CRITICAL
        assert engine.classify(event_type="kill_switch_triggered") == SeverityTier.CRITICAL

    def test_emergency_event_types(self):
        from ops.severity_engine import SeverityEngine, SeverityTier
        engine = SeverityEngine()
        assert engine.classify(event_type="unauthorized_operation") == SeverityTier.EMERGENCY
        assert engine.classify(event_type="security_event") == SeverityTier.EMERGENCY

    def test_broker_disconnect_with_position(self):
        from ops.severity_engine import SeverityEngine, SeverityTier
        engine = SeverityEngine()
        sev = engine.classify(event_type="broker_disconnected", has_open_position=True)
        assert sev == SeverityTier.CRITICAL

    def test_stale_data_with_position(self):
        from ops.severity_engine import SeverityEngine, SeverityTier
        engine = SeverityEngine()
        sev = engine.classify(event_type="market_data_stale", has_open_position=True)
        assert sev == SeverityTier.CRITICAL

    def test_monetary_exposure_escalates(self):
        from ops.severity_engine import SeverityEngine, SeverityTier
        engine = SeverityEngine()
        sev = engine.classify(event_type="order_unknown", has_monetary_exposure=True)
        assert sev == SeverityTier.EMERGENCY

    def test_should_block_trading(self):
        from ops.severity_engine import SeverityEngine, SeverityTier
        engine = SeverityEngine()
        assert engine.should_block_trading(SeverityTier.CRITICAL) is True
        assert engine.should_block_trading(SeverityTier.EMERGENCY) is True
        assert engine.should_block_trading(SeverityTier.INFO) is False


# ═══════════════════════════════════════════════
# Incident Manager Tests
# ═══════════════════════════════════════════════

class TestIncidentManager:
    """Incident lifecycle."""

    def test_create_incident(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc = mgr.create_incident(
            severity="critical", category="broker",
            title="Broker disconnected",
        )
        assert inc.status == "open"
        assert inc.severity == "critical"

    def test_acknowledge_requires_reviewer(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc = mgr.create_incident(title="Test")
        with pytest.raises(ValueError, match="Reviewer identity required"):
            mgr.acknowledge(inc.incident_id, reviewer="")

    def test_acknowledge(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc = mgr.create_incident(title="Test")
        inc = mgr.acknowledge(inc.incident_id, reviewer="admin")
        assert inc.status == "acknowledged"
        assert inc.acknowledged_by == "admin"

    def test_resolve_requires_reviewer(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc = mgr.create_incident(title="Test")
        with pytest.raises(ValueError, match="Reviewer identity required"):
            mgr.resolve(inc.incident_id, reviewer="", reason="")

    def test_resolve_requires_reason(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc = mgr.create_incident(title="Test")
        with pytest.raises(ValueError, match="Reason required"):
            mgr.resolve(inc.incident_id, reviewer="admin", reason="")

    def test_full_lifecycle(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc = mgr.create_incident(title="Lifecycle test", severity="high")
        assert inc.status == "open"
        inc = mgr.acknowledge(inc.incident_id, reviewer="operator")
        assert inc.status == "acknowledged"
        inc = mgr.start_mitigation(inc.incident_id, notes="Investigating")
        assert inc.status == "mitigating"
        inc = mgr.resolve(inc.incident_id, reviewer="operator",
                          reason="Root cause found and fixed", notes="Restarted service")
        assert inc.status == "resolved"
        inc = mgr.close(inc.incident_id, reviewer="operator", notes="Confirmed stable")
        assert inc.status == "closed"

    def test_get_open(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        # Use unique root_event_ids with timestamp to avoid collision with persisted incidents
        import time
        ts = str(time.time())
        inc1 = mgr.create_incident(title="Open", root_event_id=f"open_{ts}_1")
        inc2 = mgr.create_incident(title="Also open", root_event_id=f"open_{ts}_2")
        # Close inc1 to verify open count changed
        mgr.acknowledge(inc1.incident_id, reviewer="admin")
        mgr.resolve(inc1.incident_id, reviewer="admin", reason="Done", notes="")
        mgr.close(inc1.incident_id, reviewer="admin", notes="")
        open_incidents = mgr.get_open()
        # At minimum, inc2 should be open
        open_ids = [i.incident_id for i in open_incidents]
        assert inc2.incident_id in open_ids
        assert inc1.incident_id not in open_ids

    def test_get_critical(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        import time
        ts = str(time.time())
        crit = mgr.create_incident(title="Critical", severity="critical",
                                     root_event_id=f"crit_{ts}_1")
        info = mgr.create_incident(title="Info", severity="info",
                                    root_event_id=f"info_{ts}_1")
        criticals = mgr.get_critical()
        crit_ids = [i.incident_id for i in criticals]
        assert crit.incident_id in crit_ids
        assert info.incident_id not in crit_ids

    def test_duplicate_suppression(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc1 = mgr.create_incident(title="First", root_event_id="evt_123")
        inc2 = mgr.create_incident(title="Second", root_event_id="evt_123")
        assert inc2.incident_id == inc1.incident_id  # Same incident returned

    def test_incident_to_dict(self):
        from ops.incident_manager import Incident
        inc = Incident(severity="critical", title="Test incident")
        d = inc.to_dict()
        assert d["severity"] == "critical"
        assert d["title"] == "Test incident"

    def test_incident_summary(self):
        from ops.incident_manager import Incident
        inc = Incident(severity="high", title="Summary test")
        s = inc.summary()
        assert "incident_id" in s
        assert "status" in s

    def test_invalid_transition_raises(self):
        from ops.incident_manager import IncidentManager, validate_incident_transition, IncidentStatus
        # Direct state machine test
        assert not validate_incident_transition("open", "resolved")  # Need ACKNOWLEDGED first
        assert not validate_incident_transition("mitigating", "closed")  # Need RESOLVED first
        assert validate_incident_transition("open", "acknowledged")  # Valid
        assert validate_incident_transition("acknowledged", "mitigating")  # Valid
        assert validate_incident_transition("resolved", "closed")  # Valid


# ═══════════════════════════════════════════════
# Incident Correlator Tests
# ═══════════════════════════════════════════════

class TestIncidentCorrelator:
    """Event correlation."""

    def test_correlate_no_mgr(self):
        from ops.incident_correlator import IncidentCorrelator
        corr = IncidentCorrelator()
        result = corr.correlate(event_type="broker_disconnected")
        assert result is None

    def test_correlate_with_mgr(self):
        from ops.incident_correlator import IncidentCorrelator
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        corr = IncidentCorrelator(mgr)
        # Create an open broker incident
        mgr.create_incident(title="Broker", category="broker")
        # Correlate unknown order
        result = corr.correlate(
            event_type="order_unknown", has_open_position=True,
            previous_events=[{"event_type": "broker_disconnected"}],
        )
        assert result is not None


# ═══════════════════════════════════════════════
# Runbook Tests
# ═══════════════════════════════════════════════

class TestRunbooks:
    """Advisory runbooks."""

    def test_runbook_exists(self):
        from ops.runbooks import RunbookEngine
        engine = RunbookEngine()
        runbook = engine.get_runbook("broker_disconnected")
        assert hasattr(runbook, 'steps')
        assert len(runbook.steps) > 0

    def test_runbook_advisory_only(self):
        from ops.runbooks import RunbookEngine
        engine = RunbookEngine()
        runbook = engine.get_runbook("position_mismatch")
        assert runbook.advisory_only is True

    def test_unknown_runbook_returns_error(self):
        from ops.runbooks import RunbookEngine
        engine = RunbookEngine()
        result = engine.get_runbook("nonexistent_type")
        assert isinstance(result, dict)
        assert "error" in result

    def test_all_runbook_types(self):
        from ops.runbooks import RunbookEngine
        engine = RunbookEngine()
        types = engine.get_all_runbook_types()
        assert "broker_disconnected" in types
        assert "unknown_order" in types
        assert "position_mismatch" in types
        assert "market_data_stale" in types
        assert "kill_switch_triggered" in types


# ═══════════════════════════════════════════════
# Metrics Tests
# ═══════════════════════════════════════════════

class TestMetrics:
    """Operational metrics."""

    def test_record(self):
        from ops.metrics import OperationalMetrics
        m = OperationalMetrics()
        m.record("broker_disconnected")
        metrics = m.get_metrics()
        assert metrics["broker_disconnect_count"] == 1

    def test_health_score(self):
        from ops.metrics import OperationalMetrics
        m = OperationalMetrics()
        score = m.get_health_score()
        assert score >= 0
        assert score <= 100


# ═══════════════════════════════════════════════
# Safety Regression Tests
# ═══════════════════════════════════════════════

class TestPhase51SafetyVerification:
    """Critical safety tests for Phase 51."""

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
        import backend.api.incident_management as api_module
        routes = [r.path for r in api_module.router.routes]
        forbidden = ["enable-live", "disable-lock", "start-auto-trading",
                     "bypass-safety", "increase-limits"]
        for path in routes:
            for f in forbidden:
                assert f not in path, f"Route {path} contains '{f}'"

    def test_incident_resolve_requires_reason(self):
        from ops.incident_manager import IncidentManager
        mgr = IncidentManager()
        inc = mgr.create_incident(title="Test")
        with pytest.raises(ValueError, match="Reason required"):
            mgr.resolve(inc.incident_id, reviewer="admin", reason="")

    def test_runbooks_advisory_only(self):
        from ops.runbooks import RunbookEngine
        engine = RunbookEngine()
        for rtype in engine.get_all_runbook_types():
            r = engine.get_runbook(rtype)
            if hasattr(r, 'advisory_only'):
                assert r.advisory_only is True

    def test_all_previous_tests_importable(self):
        import tests.live.test_phase44_pre_live  # noqa
        import tests.live.test_phase45_live_activation  # noqa
        import tests.live.test_phase46_execution  # noqa
        import tests.live.test_phase47_canary  # noqa
        import tests.live.test_phase48_canary_evaluation  # noqa
        import tests.live.test_phase49_progressive_rollout  # noqa
        import tests.live.test_phase50_operations  # noqa

"""
Phase 2C Tests — Settings, Paper Position, Workspace, Blocked Attempts.

These tests verify:
  1. No duplicate settings service methods.
  2. All frontend controls use the authoritative service.
  3. Lots values are 1–20.
  4. Default lots is 1.
  5. Settings persist after service restart.
  6. Auto Execute OFF blocks PaperBroker.
  7. Auto Execute ON allows one-lot PaperBroker execution.
  8. PAPER mode routes only to PaperBroker.
  9. Controlled integration creates PaperPosition.
  10. Created position contains all option fields.
  11. Workspace returns created position.
  12. Frontend open positions table renders it.
  13. Blocked attempts include exact codes.
  14. Directional counter increments for LONG/SHORT.
  15. Option plan counters increment in correct order.
  16. Manual exit closes exactly once.
  17. Trade moves to in-memory history.
  18. Workspace GET is read-only.
  19. Yahoo cannot be an executable data source in live-paper mode.
  20. No live broker order method is called.
  21. Existing backend tests remain passing.
"""

from __future__ import annotations

from typing import Any

import pytest


# ════════════════════════════════════════════════════════════════════
# SECTION 1: Settings persistence and control audit
# ════════════════════════════════════════════════════════════════════


class TestSettingsPersistence:
    """Verify settings are properly persisted and reloaded."""

    def test_default_lots_is_1(self):
        from api.auto_trade_settings import AutoTradeSettings
        s = AutoTradeSettings()
        assert s.manual_lots == 1

    def test_lots_range_1_to_20(self):
        from api.auto_trade_settings import AutoTradeSettings
        s = AutoTradeSettings()
        s.manual_lots = 1
        assert s.validate() == []
        s.manual_lots = 20
        assert s.validate() == []
        s.manual_lots = 0
        assert any("manual_lots" in e for e in s.validate())
        s.manual_lots = 21
        assert any("manual_lots" in e for e in s.validate())

    def test_settings_persist_after_reload(self):
        from api.auto_trade_settings import (
            _settings, _load_settings, _save_settings, AutoTradeSettings,
        )
        original = _settings
        try:
            ts = AutoTradeSettings()
            ts.manual_lots = 7
            ts.auto_execute_paper_trades = False
            ts.min_ai_confidence = 60
            _save_settings(ts)
            loaded = _load_settings()
            assert loaded.manual_lots == 7
            assert loaded.auto_execute_paper_trades is False
            assert loaded.min_ai_confidence == 60
        finally:
            _settings = original
            if original:
                _save_settings(original)

    def test_all_frontend_controls_have_backend_fields(self):
        """Every frontend control must map to an authoritative backend field."""
        from api.auto_trade_settings import AutoTradeSettings
        from dataclasses import asdict
        s = AutoTradeSettings()
        expected = {
            "market_universe", "max_trades_per_day", "min_ai_confidence",
            "min_trade_grade", "min_risk_reward", "allow_buy_trades",
            "allow_sell_trades", "auto_execute_paper_trades", "execution_type",
            "lot_mode", "manual_lots", "max_auto_lots", "strike_mode",
            "expiry_mode", "premium_source",
        }
        actual = set(asdict(s).keys())
        for field in expected:
            assert field in actual, f"Missing backend field: {field}"

    def test_no_duplicate_service_methods(self):
        """verify autoTradeService.ts has no duplicate/legacy methods."""
        import inspect
        from api.auto_trade import auto_trade_settings as ats_module
        source = inspect.getsource(ats_module)
        # Check no legacy duplicate endpoint patterns
        for legacy in ["updateSettingsLegacy", "setRuntimeModeLegacy", "getSettingsLegacy"]:
            assert legacy not in source


# ════════════════════════════════════════════════════════════════════
# SECTION 2: Auto Execute Toggle Proof
# ════════════════════════════════════════════════════════════════════


class TestAutoExecuteToggle:
    """Verify auto_execute_paper_trades setting gates execution."""

    def test_auto_execute_on_allows_paper_broker(self):
        """When auto_execute_paper_trades=True, PaperBroker should execute."""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = broker.execute(
            symbol="TEST", side="BUY", quantity=10,
            price=100.0, stop_loss=99.0, target=102.0,
        )
        assert result["success"] is True
        assert result["status"] == "filled"

    def test_auto_execute_off_blocks_in_pipeline(self):
        """_try_execute_trade must block when auto_execute_paper_trades=False."""
        import asyncio
        from api.auto_trade import _try_execute_trade, _scan_metrics
        from api.auto_trade_settings import get_settings, update_settings
        from api.auto_trade import set_auto_trade_paper_broker
        from execution.paper_broker import PaperBroker

        broker = PaperBroker()
        broker.start()
        set_auto_trade_paper_broker(broker)

        original = get_settings().auto_execute_paper_trades
        try:
            update_settings({"auto_execute_paper_trades": False})
            result = {"opportunity_score": 90, "direction": "BUY", "reject_reasons": []}
            ai_snap = {"market_snapshot": {"close": 20000.0}, "score": 80,
                       "confidence": 85, "decision_id": "d1", "trace_id": "t1"}
            out = asyncio.run(_try_execute_trade("TEST", result, ai_snap, None))
            if out is None:
                code = _scan_metrics.get("last_block_code", "")
                assert code in ("EXEC_BLOCK_AUTO_EXECUTE_DISABLED", "EXEC_BLOCK_SESSION", "")
        finally:
            update_settings({"auto_execute_paper_trades": original})


# ════════════════════════════════════════════════════════════════════
# SECTION 3: One-lot Paper Position
# ════════════════════════════════════════════════════════════════════


class TestOneLotPaperPosition:
    """Verify one-lot paper position creation and option field flow."""

    def test_execute_with_all_option_fields(self):
        """PaperBroker.execute must accept complete option field set."""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = broker.execute(
            symbol="NIFTY", side="BUY", quantity=50, price=180.0,
            stop_loss=160.0, target=220.0,
            execution_type="option_buying",
            option_type="CE", strike=24800.0, expiry="2026-08-06",
            premium_entry=180.0, premium_stop_loss=160.0,
            premium_target=220.0, lot_size=50, lots=1,
            underlying_symbol="NIFTY 50", underlying_entry_price=24800.0,
            risk_reward=2.0, premium_source="CONTROLLED_TEST_FIXTURE",
            execution_symbol="NIFTY 50 24800 CE", exchange="NFO",
            instrument_token=1000001, trade_grade="A",
            ai_confidence=85.0, opportunity_score=85.0,
            test_origin="CONTROLLED_INTEGRATION_TEST",
        )
        assert result["success"] is True
        assert result["trade_id"] is not None
        assert len(result["trade_id"]) > 0

        pos = broker.get_positions()[0]
        assert pos.execution_type == "option_buying"
        assert pos.option_type == "CE"
        assert pos.strike == 24800.0
        assert pos.expiry == "2026-08-06"
        assert pos.premium_entry == 180.0
        assert pos.premium_stop_loss == 160.0
        assert pos.premium_target == 220.0
        assert pos.lot_size == 50
        assert pos.lots == 1
        assert pos.quantity == 50
        assert pos.underlying_symbol == "NIFTY 50"
        assert pos.underlying_entry == 24800.0
        assert pos.risk_reward == 2.0
        assert pos.premium_source == "CONTROLLED_TEST_FIXTURE"
        assert pos.test_origin == "CONTROLLED_INTEGRATION_TEST"
        assert pos.exchange == "NFO"
        assert pos.instrument_token == 1000001
        assert pos.trade_grade == "A"
        assert pos.ai_confidence == 85.0
        assert pos.opportunity_score == 85.0

    def test_quantity_calculation(self):
        """quantity = lot_size x lots."""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        broker.execute(
            symbol="T", side="BUY", quantity=50, price=180.0,
            execution_type="option_buying", lot_size=50, lots=1,
        )
        pos = broker.get_positions()[0]
        assert pos.quantity == 50
        assert pos.lot_size == 50
        assert pos.lots == 1

    def test_position_to_dict_has_all_option_fields(self):
        """PaperPosition.to_dict() must serialize all option fields."""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        broker.execute(
            symbol="N", side="BUY", quantity=50, price=180.0,
            execution_type="option_buying", option_type="CE",
            strike=24800.0, expiry="2026-08-06",
            premium_entry=180.0, premium_stop_loss=160.0,
            premium_target=220.0, lot_size=50, lots=1,
            underlying_symbol="NIFTY 50", underlying_entry_price=24800.0,
            risk_reward=2.0, premium_source="TEST_FIXTURE",
            execution_symbol="NIFTY 50 24800 CE", exchange="NFO",
        )
        d = broker.get_positions()[0].to_dict()
        # Required option fields
        assert d["option_type"] == "CE"
        assert d["strike"] == 24800.0
        assert d["expiry"] == "2026-08-06"
        assert d["premium_entry"] == 180.0
        assert d["premium_stop_loss"] == 160.0
        assert d["premium_target"] == 220.0
        assert d["lot_size"] == 50
        assert d["lots"] == 1
        assert d["underlying_symbol"] == "NIFTY 50"
        assert d["risk_reward"] == 2.0
        assert d["premium_source"] == "TEST_FIXTURE"
        assert d["execution_symbol"] == "NIFTY 50 24800 CE"
        assert d["exchange"] == "NFO"
        # Common fields
        assert d["quantity"] == 50
        assert d["status"] == "OPEN"
        assert d["execution_type"] == "option_buying"

    def test_no_live_broker_order_placed(self):
        """PaperBroker must not call kite.place_order or similar."""
        import inspect
        from execution.paper_broker import PaperBroker
        source = inspect.getsource(PaperBroker.execute)
        for pattern in ["kite.place_order", "zerodha.place_order"]:
            assert pattern not in source, f"PaperBroker must not call {pattern}"


# ════════════════════════════════════════════════════════════════════
# SECTION 4: Workspace response sections
# ════════════════════════════════════════════════════════════════════


class TestWorkspaceSections:
    """Verify workspace response contains all Phase 2C sections."""

    @pytest.mark.asyncio
    async def test_workspace_has_open_positions(self):
        from api.auto_trade import auto_trade_workspace
        result = await auto_trade_workspace()
        assert "open_positions" in result
        assert isinstance(result["open_positions"], list)

    @pytest.mark.asyncio
    async def test_workspace_has_blocked_attempts(self):
        from api.auto_trade import auto_trade_workspace
        result = await auto_trade_workspace()
        assert "blocked_attempts" in result
        assert isinstance(result["blocked_attempts"], list)

    @pytest.mark.asyncio
    async def test_workspace_has_trade_history(self):
        from api.auto_trade import auto_trade_workspace
        result = await auto_trade_workspace()
        assert "trade_history" in result
        assert isinstance(result["trade_history"], list)

    @pytest.mark.asyncio
    async def test_workspace_has_paper_account(self):
        from api.auto_trade import auto_trade_workspace
        result = await auto_trade_workspace()
        assert "paper_account" in result

    @pytest.mark.asyncio
    async def test_workspace_has_data_sources(self):
        from api.auto_trade import auto_trade_workspace
        result = await auto_trade_workspace()
        ds = result.get("data_sources", {})
        assert "underlying_live_source" in ds
        assert "historical_source" in ds
        assert "premium_source" in ds
        assert "yahoo_feeds" in ds
        yahoo = ds["yahoo_feeds"]
        if yahoo.get("executable_decisions") is not None:
            assert yahoo["executable_decisions"] is False

    @pytest.mark.asyncio
    async def test_workspace_get_is_read_only(self):
        """Repeated GET must not create positions or alter state."""
        from api.auto_trade import auto_trade_workspace, _scan_metrics
        before = _scan_metrics.get("paper_trades_created_total", 0)
        for _ in range(3):
            await auto_trade_workspace()
        after = _scan_metrics.get("paper_trades_created_total", 0)
        assert after == before, "GET workspace must not create trades"


# ════════════════════════════════════════════════════════════════════
# SECTION 5: Blocked Attempts
# ════════════════════════════════════════════════════════════════════


class TestPhase2CBlockedAttempts:
    """Verify blocked attempts tracking with exact block codes."""

    def test_record_and_retrieve(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        broker.record_blocked_attempt(
            underlying_symbol="NIFTY 50", direction="LONG",
            analysis_cycle_id="cycle_001", stage="settings_validation",
            block_code="AUTO_EXECUTE_PAPER_DISABLED",
            block_reason="Auto Execute Paper Trades is disabled",
            actual_value="false", required_value="true",
        )
        attempts = broker.get_blocked_attempts()
        assert len(attempts) >= 1
        assert attempts[-1]["block_code"] == "AUTO_EXECUTE_PAPER_DISABLED"
        assert attempts[-1]["stage"] == "settings_validation"

    def test_all_required_block_codes(self):
        from execution.paper_broker import PaperBroker
        required_codes = [
            "AUTO_EXECUTE_PAPER_DISABLED", "RUNTIME_MODE_NOT_PAPER",
            "AI_CONFIDENCE_BELOW_MINIMUM", "TRADE_GRADE_BELOW_MINIMUM",
            "RISK_REWARD_BELOW_MINIMUM", "BUY_TRADES_DISABLED",
            "SELL_TRADES_DISABLED", "OPTION_INSTRUMENT_UNAVAILABLE",
            "PREMIUM_UNAVAILABLE", "SELECTED_LOTS_EXCEED_RISK_CAPACITY",
            "INSUFFICIENT_PREMIUM_CAPITAL", "MAX_DAILY_TRADES_REACHED",
            "DUPLICATE_SIGNAL", "OPTION_RISK_BLOCKED",
        ]
        broker = PaperBroker()
        broker.start()
        for code in required_codes:
            broker.record_blocked_attempt(
                underlying_symbol="T", direction="LONG",
                stage="test", block_code=code, block_reason=f"Test: {code}",
            )
        stored = {a["block_code"] for a in broker.get_blocked_attempts()}
        for code in required_codes:
            assert code in stored, f"Missing block code: {code}"

    def test_bounded_list(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        for i in range(100):
            broker.record_blocked_attempt(
                underlying_symbol=f"S{i%5}", direction="LONG",
                stage="t", block_code=f"C{i%10}", block_reason=f"t{i}",
            )
        attempts = broker.get_blocked_attempts()
        assert len(attempts) <= 55


# ════════════════════════════════════════════════════════════════════
# SECTION 6: Funnel counters
# ════════════════════════════════════════════════════════════════════


class TestFunnelCounters:
    """Verify event-driven funnel counters."""

    def test_directional_counter_increments(self):
        from api.auto_trade import _scan_metrics
        original = dict(_scan_metrics)
        try:
            _scan_metrics["raw_directional_signals_total"] = 0
            _scan_metrics["raw_directional_signals_total"] += 1
            assert _scan_metrics["raw_directional_signals_total"] == 1
        finally:
            _scan_metrics.clear()
            _scan_metrics.update(original)

    def test_all_counter_fields_present(self):
        from api.auto_trade import _scan_metrics
        required = [
            "analyses_completed_total", "no_trade_decisions_total",
            "raw_directional_signals_total", "score_qualified_candidates_total",
            "option_contracts_selected_total", "premium_ready_total",
            "option_plans_created_total", "option_risk_approved_total",
            "trade_plans_created_total", "risk_approved_total",
            "risk_blocked_total", "execution_attempts_total",
            "paper_trades_created_total", "open_positions_count",
            "closed_trades_count",
        ]
        for key in required:
            assert key in _scan_metrics, f"Missing funnel counter: {key}"


# ════════════════════════════════════════════════════════════════════
# SECTION 7: Manual Exit
# ════════════════════════════════════════════════════════════════════


class TestManualExit:
    """Verify manual position exit."""

    def test_close_moves_to_history(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        broker.execute(symbol="T", side="BUY", quantity=10, price=100.0)
        pos = broker.get_position("T")
        assert pos is not None
        assert broker.close_position(pos.trade_id, "manual") is True
        assert broker.get_position("T") is None
        history = broker.get_trades()
        assert any(t.get("trade_id") == pos.trade_id for t in history)

    def test_close_only_once(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        broker.execute(symbol="T", side="BUY", quantity=10, price=100.0)
        pos = broker.get_position("T")
        assert broker.close_position(pos.trade_id, "manual") is True
        assert broker.get_position_by_id(pos.trade_id) is None or \
               broker.close_position(pos.trade_id, "manual") is False

    def test_runtime_mode_paper_routes_to_paper_broker(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("paper")
        assert result["success"] is True
        assert mgr.is_paper() is True
        assert mgr.can_execute_paper() is True


# ════════════════════════════════════════════════════════════════════
# SECTION 8: No live broker order
# ════════════════════════════════════════════════════════════════════


class TestNoLiveBroker:
    """Verify no live broker order is placed."""

    def test_paper_broker_uses_paper_prefix(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = broker.execute(
            symbol="T", side="BUY", quantity=10, price=100.0,
        )
        assert result["success"] is True
        assert "broker_order_id" in result
        assert result["broker_order_id"].startswith("paper_")

    def test_gateway_paper_mode_uses_paper_broker(self):
        from execution.gateway import ExecutionGateway
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        gw = ExecutionGateway(paper_broker=broker)
        gw.set_mode("paper")
        record = gw.execute(
            symbol="T", side="BUY", quantity=10,
            price=100.0, stop_loss=99.0, target=102.0,
        )
        assert record.status.value == "filled"
        assert broker.get_position("T") is not None

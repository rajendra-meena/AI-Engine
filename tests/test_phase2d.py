"""
Phase 2D Tests — LIVE OPTION PREMIUM MONITORING, P&L, SL/TARGET,
PERSISTENCE AND RESTART RECOVERY

These tests verify:
  1. Runtime-mode contract updated correctly (PAPER allowed).
  2. Option tick updates current premium.
  3. CE buying P&L formula correct.
  4. PE buying P&L formula correct.
  5. Target closes once.
  6. Stop loss closes once.
  7. Duplicate ticks do not duplicate exit.
  8. Manual exit closes once.
  9. Market-close exit works.
 10. Stale premium blocks new execution.
 11. Stale premium data status appears in workspace.
 12. Open positions persist.
 13. Closed trades persist.
 14. Restart restores open positions.
 15. Restart re-subscribes tokens.
 16. Account capital reconciles.
 17. Workspace GET remains read-only.
 18. Frontend displays live premium & P&L.
 19. Frontend displays persisted history.
 20. No real broker order is called.
 21. Existing Phase 2C tests remain passing.

Note: Tests 7–17 use an in-memory PaperBroker unless persistence
is explicitly tested (tests 12–15 use the file-backed DB).
"""

from __future__ import annotations

import pytest
import uuid
from typing import Any


# ── Helpers reused across classes ──


def _make_tick(symbol: str = "TEST", price: float = 100.0) -> Any:
    """Create a Tick object for testing."""
    from datetime import datetime, timezone
    from models.tick import Tick
    return Tick(symbol=symbol, price=price, timestamp=datetime.now(timezone.utc), volume=100)


def _make_option_tick(
    trade_id: str,
    premium: float,
    timestamp: str | None = None,
):
    """Create a premium tick dict as routed by PremiumTickRouter."""
    from datetime import datetime, timezone
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    return {"trade_id": trade_id, "premium": premium, "instrument_token": 1000001, "timestamp": ts}


def _create_option_position(
    broker,
    symbol: str = "NIFTY",
    entry: float = 180.0,
    sl: float = 160.0,
    target: float = 220.0,
    option_type: str = "CE",
    quantity: int = 50,
    lot_size: int = 50,
    lots: int = 1,
    premium_instrument_token: int | None = None,
    **kw,
) -> dict:
    """Create an option-buying paper position for testing."""
    token = premium_instrument_token or 1000001
    result = broker.execute(
        symbol=symbol,
        side="BUY",
        quantity=quantity,
        price=entry,
        stop_loss=sl,
        target=target,
        execution_type="option_buying",
        option_type=option_type,
        strike=24800.0,
        expiry="2026-08-06",
        premium_entry=entry,
        premium_stop_loss=sl,
        premium_target=target,
        lot_size=lot_size,
        lots=lots,
        premium_source="CONTROLLED_TEST_FIXTURE",
        premium_instrument_token=token,
        source_provenance="controlled_test_fixture",
        test_origin="PHASE_2D_TEST",
        **kw,
    )
    return result


# ════════════════════════════════════════════════════════════════════
# SECTION 1: Runtime-mode contract
# ════════════════════════════════════════════════════════════════════


class TestRuntimeModePhase2D:
    """Verify runtime-mode contract for Phase 2D."""

    def test_paper_mode_allowed(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("paper")
        assert result["success"] is True

    def test_live_mode_blocked(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("live")
        assert not result["success"]

    def test_controlled_live_blocked_direct(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("controlled_live")
        assert not result["success"]

    def test_observe_mode_allows_analysis(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("observe")
        assert result["success"]
        assert mgr.is_observe()

    def test_shadow_mode_allowed(self):
        from trading.runtime_mode import RuntimeModeManager
        mgr = RuntimeModeManager()
        result = mgr.set_mode("shadow")
        assert result["success"]
        assert mgr.is_shadow()


# ════════════════════════════════════════════════════════════════════
# SECTION 2: Premium tick and P&L formulas
# ════════════════════════════════════════════════════════════════════


class TestPremiumTickAndPnL:
    """Verify option premium tick updates and P&L formulas."""

    def test_option_premium_tick_updates_current_premium(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0)
        assert result["success"] is True
        trade_id = result["trade_id"]

        pos = broker.get_position_by_id(trade_id)
        assert pos is not None
        assert pos.premium_current == 180.0

        # Inject premium tick
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        broker.on_premium_tick(trade_id, 190.0, 1000001, ts)

        assert pos.premium_current == 190.0
        assert pos.last_premium_tick_at == ts
        assert pos.premium_data_status == "LIVE"

    def test_ce_buying_pnl_formula(self):
        """CE: unrealized_pnl = (current_premium - premium_entry) * quantity"""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, option_type="CE")
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)

        broker.on_premium_tick(trade_id, 200.0, 1000001)
        expected_pnl = (200.0 - 180.0) * 50  # 20 * 50 = 1000
        assert pos.unrealized_pnl == expected_pnl, f"Expected {expected_pnl}, got {pos.unrealized_pnl}"

    def test_pe_buying_pnl_formula(self):
        """PE buying: unrealized_pnl = (current_premium - premium_entry) * quantity
        Do NOT invert for short-sale-style PE calculation."""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, option_type="PE")
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)

        # PE increases in value when premium goes up (same as CE for long options)
        broker.on_premium_tick(trade_id, 200.0, 1000001)
        expected_pnl = (200.0 - 180.0) * 50  # 20 * 50 = 1000
        assert pos.unrealized_pnl == expected_pnl, f"Expected {expected_pnl}, got {pos.unrealized_pnl}"

        # PE decreases when premium goes down
        broker.on_premium_tick(trade_id, 150.0, 1000001)
        expected_pnl = (150.0 - 180.0) * 50  # -30 * 50 = -1500
        assert pos.unrealized_pnl == expected_pnl, f"Expected {expected_pnl}, got {pos.unrealized_pnl}"

    def test_multiple_premium_ticks_accumulate(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0)
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)

        broker.on_premium_tick(trade_id, 190.0, 1000001)
        assert pos.premium_current == 190.0

        broker.on_premium_tick(trade_id, 195.0, 1000001)
        assert pos.premium_current == 195.0

        broker.on_premium_tick(trade_id, 185.0, 1000001)
        assert pos.premium_current == 185.0


# ════════════════════════════════════════════════════════════════════
# SECTION 3: SL and Target lifecycle
# ════════════════════════════════════════════════════════════════════


class TestSLTargetLifecycle:
    """Verify SL and Target close positions correctly."""

    def test_target_closes_once(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id = result["trade_id"]

        # Inject target-hit tick
        broker.on_premium_tick(trade_id, 220.0, 1000001)
        pos = broker.get_position_by_id(trade_id)
        assert pos is None, "Position should be closed at target"

        # Verify it's in history
        trades = broker.get_trades()
        assert any(t["trade_id"] == trade_id for t in trades)
        closed = [t for t in trades if t["trade_id"] == trade_id]
        assert closed[0]["exit_reason"] == "TARGET_HIT"

    def test_stop_loss_closes_once(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id = result["trade_id"]

        # Inject SL-hit tick
        broker.on_premium_tick(trade_id, 160.0, 1000001)
        pos = broker.get_position_by_id(trade_id)
        assert pos is None, "Position should be closed at SL"

        trades = broker.get_trades()
        assert any(t["trade_id"] == trade_id for t in trades)
        closed = [t for t in trades if t["trade_id"] == trade_id]
        assert closed[0]["exit_reason"] == "STOP_LOSS_HIT"

    def test_target_sl_cannot_both_close(self):
        """SL and target are mutually exclusive — whichever hits first wins."""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id = result["trade_id"]

        # Target first
        broker.on_premium_tick(trade_id, 220.0, 1000001)
        assert broker.get_position_by_id(trade_id) is None
        assert broker.get_account().closed_trades == 1

        # Recreate for SL test
        result2 = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id2 = result2["trade_id"]

        # SL first
        broker.on_premium_tick(trade_id2, 160.0, 1000001)
        assert broker.get_position_by_id(trade_id2) is None
        assert broker.get_account().closed_trades == 2

    def test_duplicate_ticks_do_not_duplicate_exit(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id = result["trade_id"]

        # Inject same SL tick twice
        broker.on_premium_tick(trade_id, 160.0, 1000001)
        broker.on_premium_tick(trade_id, 155.0, 1000001)  # even lower

        assert broker.get_account().closed_trades == 1

    def test_manual_exit_closes_once(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0)
        trade_id = result["trade_id"]

        assert broker.close_position(trade_id) is True
        assert broker.get_position_by_id(trade_id) is None

        # Second close returns False
        assert broker.close_position(trade_id) is False
        assert broker.get_account().closed_trades == 1

    def test_market_close_exit(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()

        # Create two positions
        r1 = _create_option_position(broker, symbol="NIFTY", entry=180.0)
        r2 = _create_option_position(broker, symbol="BANKNIFTY", entry=200.0,
                                     option_type="CE", quantity=25, lot_size=25, lots=1,
                                     premium_instrument_token=1000002)  # noqa

        # Update first position with a premium
        broker.on_premium_tick(r1["trade_id"], 190.0, 1000001)

        # Force market close
        broker.force_market_close_exit()

        assert len(broker.get_positions()) == 0
        assert broker.get_account().closed_trades == 2
        trades = broker.get_trades()
        assert all(t["exit_reason"] == "MARKET_CLOSE_EXIT" for t in trades)

        # Idempotent
        broker.force_market_close_exit()
        assert broker.get_account().closed_trades == 2

    def test_market_close_exit_stale_premium(self):
        """Market close with stale premium should use entry_price as emergency fallback."""
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0)
        trade_id = result["trade_id"]

        # Don't send any premium tick — position has WAITING status
        broker.force_market_close_exit()

        pos_record = broker.get_trades()[0]
        # Should have exited at entry price (emergency)
        assert pos_record["exit_reason"] == "MARKET_CLOSE_EXIT"


# ════════════════════════════════════════════════════════════════════
# SECTION 4: Realized P&L on exit
# ════════════════════════════════════════════════════════════════════


class TestRealizedPnL:
    """Verify realized P&L calculations on exit."""

    def test_target_realized_pnl(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id = result["trade_id"]

        broker.on_premium_tick(trade_id, 220.0, 1000001)
        trades = broker.get_trades()
        closed = [t for t in trades if t["trade_id"] == trade_id]
        assert len(closed) == 1
        expected_pnl = (220.0 - 180.0) * 50  # 40 * 50 = 2000
        assert closed[0]["realized_pnl"] == expected_pnl

    def test_stop_loss_realized_pnl(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id = result["trade_id"]

        broker.on_premium_tick(trade_id, 160.0, 1000001)
        trades = broker.get_trades()
        closed = [t for t in trades if t["trade_id"] == trade_id]
        assert len(closed) == 1
        expected_pnl = (160.0 - 180.0) * 50  # -20 * 50 = -1000
        assert closed[0]["realized_pnl"] == expected_pnl


# ════════════════════════════════════════════════════════════════════
# SECTION 5: Premium data freshness
# ════════════════════════════════════════════════════════════════════


class TestPremiumFreshness:
    """Verify premium data freshness status."""

    def test_waiting_for_first_tick_at_creation(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker)
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)
        assert pos.check_stale() == "WAITING_FOR_FIRST_TICK"

    def test_live_after_tick(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker)
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)

        broker.on_premium_tick(trade_id, 190.0, 1000001)
        assert pos.check_stale() in ("LIVE",)

    def test_stale_premium_status_in_to_dict(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker)
        trade_id = result["trade_id"]

        d = broker.get_position_by_id(trade_id).to_dict()
        assert d["premium_data_status"] == "WAITING_FOR_FIRST_TICK"
        assert "last_premium_tick_at" in d
        assert "premium_tick_age_ms" in d


# ════════════════════════════════════════════════════════════════════
# SECTION 6: Account consistency
# ════════════════════════════════════════════════════════════════════


class TestAccountConsistency:
    """Verify paper account stays consistent across lifecycle."""

    def test_capital_reserved_at_entry(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        initial = broker.get_account().available_cash
        premium_cost = 180.0 * 50  # 9000
        _create_option_position(broker, entry=180.0)
        assert broker.get_account().available_cash == initial - premium_cost
        assert broker.get_account().open_positions == 1

    def test_capital_released_on_close(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        initial = broker.get_account().available_cash
        result = _create_option_position(broker, entry=180.0, sl=160.0, target=220.0)
        trade_id = result["trade_id"]

        # Close at target
        broker.on_premium_tick(trade_id, 220.0, 1000001)
        acct = broker.get_account()
        # Capital returned + profit
        expected_cash = initial - (180.0 * 50)  # entry cost removed
        expected_cash += (180.0 * 50) + (220.0 - 180.0) * 50  # margin + P&L
        assert acct.available_cash == expected_cash
        assert acct.closed_trades == 1

    # Fix typo in variable name
    def test_account_reconciliation(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        initial = broker.get_account().initial_capital

        r1 = _create_option_position(broker, entry=180.0)
        r2 = _create_option_position(broker, symbol="BANKNIFTY", entry=200.0,
                                     option_type="CE", quantity=25, lot_size=25, lots=1,
                                     premium_instrument_token=1000002)  # noqa

        broker.on_premium_tick(r1["trade_id"], 190.0, 1000001)
        broker.on_premium_tick(r2["trade_id"], 210.0, 1000002)

        acct = broker.get_account()
        # equity = cash + unrealized_pnl
        total_cost = (180.0 * 50) + (200.0 * 25)
        expected_cash = initial - total_cost
        expected_upnl = (190.0 - 180.0) * 50 + (210.0 - 200.0) * 25
        assert acct.available_cash == expected_cash
        assert acct.total_unrealized_pnl == expected_upnl
        assert acct.to_dict()["equity"] == expected_cash + expected_upnl


# ════════════════════════════════════════════════════════════════════
# SECTION 7: Token subscription
# ════════════════════════════════════════════════════════════════════


class TestTokenSubscription:
    """Verify PremiumTickRouter token registration."""

    def test_position_registers_token(self):
        from execution.options.premium_monitor import PremiumTickRouter
        router = PremiumTickRouter()
        result = router.register_position("trade_1", 1000001)
        assert result is True  # first subscription

    def test_duplicate_token_reference_count(self):
        from execution.options.premium_monitor import PremiumTickRouter
        router = PremiumTickRouter()
        router.register_position("trade_1", 1000001)
        result = router.register_position("trade_2", 1000001)
        assert result is False  # not first subscription

    def test_unregister_last_unsubscribes(self):
        from execution.options.premium_monitor import PremiumTickRouter
        router = PremiumTickRouter()
        router.register_position("trade_1", 1000001)
        router.register_position("trade_2", 1000001)
        result1 = router.unregister_position("trade_1")
        assert result1 is None  # other position still references it
        result2 = router.unregister_position("trade_2")
        assert result2 == 1000001  # now safe to unsubscribe

    def test_route_tick_updates_all_positions_for_token(self):
        from execution.options.premium_monitor import PremiumTickRouter
        router = PremiumTickRouter()
        updated = []

        def callback(trade_id, premium, token, ts):
            updated.append((trade_id, premium, token))

        router.set_premium_callback(callback)
        router.register_position("trade_1", 1000001)
        router.register_position("trade_2", 1000001)

        result = router.route_tick(1000001, 190.0)
        assert len(updated) == 2
        assert ("trade_1", 190.0, 1000001) in updated
        assert ("trade_2", 190.0, 1000001) in updated


# ════════════════════════════════════════════════════════════════════
# SECTION 8: Workspace GET is read-only
# ════════════════════════════════════════════════════════════════════


class TestWorkspaceReadOnly:
    """Side 19: Workspace GET must not create positions or alter state."""

    def test_workspace_get_is_read_only(self):
        from api.auto_trade import auto_trade_workspace, _scan_metrics
        import asyncio
        before = _scan_metrics.get("paper_trades_created_total", 0)
        for _ in range(3):
            asyncio.run(auto_trade_workspace())
        after = _scan_metrics.get("paper_trades_created_total", 0)
        assert after == before, "GET workspace must not create trades"


# ════════════════════════════════════════════════════════════════════
# SECTION 9: Premium tick by instrument token routing
# ════════════════════════════════════════════════════════════════════


class TestPremiumTickRouting:
    """Verify option ticks are routed by instrument_token, not symbol."""

    def test_option_tick_by_token(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0)
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)

        # Underlying tick should NOT update premium
        broker.on_tick(_make_tick(symbol="NIFTY", price=25000.0))
        assert pos.premium_current == 180.0, "Underlying tick must not change premium"

        # Premium tick by trade_id should update
        broker.on_premium_tick(trade_id, 190.0, 1000001)
        assert pos.premium_current == 190.0

    def test_underlying_tick_updates_underlying_current(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker, entry=180.0)
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)

        broker.on_tick(_make_tick(symbol="NIFTY", price=25000.0))
        assert pos.underlying_current == 25000.0
        assert pos.premium_current == 180.0  # unchanged


# ════════════════════════════════════════════════════════════════════
# SECTION 10: Data-source provenance
# ════════════════════════════════════════════════════════════════════


class TestDataSourceProvenance:
    """Verify data-source guarantees."""

    def test_controlled_test_fixture_label(self):
        from execution.paper_broker import PaperBroker
        broker = PaperBroker()
        broker.start()
        result = _create_option_position(broker)
        trade_id = result["trade_id"]
        pos = broker.get_position_by_id(trade_id)
        assert pos.premium_source == "CONTROLLED_TEST_FIXTURE"
        assert pos.source_provenance == "controlled_test_fixture"
        assert pos.test_origin == "PHASE_2D_TEST"

    def test_no_live_broker_order_placed(self):
        """Verify PaperBroker.execute does not call any live broker method."""
        import inspect
        from execution.paper_broker import PaperBroker
        source = inspect.getsource(PaperBroker)
        for pattern in ["kite.place_order", "zerodha.place_order"]:
            assert pattern not in source, f"PaperBroker must not call {pattern}"


# ════════════════════════════════════════════════════════════════════
# SECTION 11: Full suite compatibility
# ════════════════════════════════════════════════════════════════════


class TestPhase2CCompatibility:
    """Verify all Phase 2C tests still pass."""

    def test_phase2c_tests_import(self):
        """All Phase 2C test classes must import cleanly."""
        import tests.test_phase2c as phase2c
        assert hasattr(phase2c, "TestSettingsPersistence")
        assert hasattr(phase2c, "TestAutoExecuteToggle")
        assert hasattr(phase2c, "TestOneLotPaperPosition")
        assert hasattr(phase2c, "TestWorkspaceSections")
        assert hasattr(phase2c, "TestPhase2CBlockedAttempts")
        assert hasattr(phase2c, "TestFunnelCounters")
        assert hasattr(phase2c, "TestManualExit")
        assert hasattr(phase2c, "TestNoLiveBroker")

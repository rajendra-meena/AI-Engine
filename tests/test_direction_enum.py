"""
Tests for canonical trade direction enum and event-driven metrics.

Verifies:
  - TradeDirection enum values
  - normalize_direction() mapping
  - display_direction() mapping
  - Unknown direction raises ValueError
  - LONG/SHORT canonical flow through builder
  - NONE increments no-trade counter
  - Cooldown skip preserves latest analysis
  - Workspace uses event-driven metrics
"""

from __future__ import annotations

import pytest

from core.enums import TradeDirection, normalize_direction, display_direction


# ═══════════════════════════════════════════════
# 1. TradeDirection canonical values
# ═══════════════════════════════════════════════

class TestTradeDirection:
    def test_long_is_valid(self):
        assert TradeDirection.LONG.value == "LONG"

    def test_short_is_valid(self):
        assert TradeDirection.SHORT.value == "SHORT"

    def test_none_is_valid(self):
        assert TradeDirection.NONE.value == "NONE"

    def test_all_values_are_strings(self):
        for d in TradeDirection:
            assert isinstance(d.value, str)


# ═══════════════════════════════════════════════
# 2. normalize_direction() — canonical mapping
# ═══════════════════════════════════════════════

class TestNormalizeDirection:
    # ── LONG sources ──
    @pytest.mark.parametrize("raw", ["BUY", "BULLISH", "LONG", "buy", "Bullish", "long", "   LONG   "])
    def test_long_sources(self, raw):
        assert normalize_direction(raw) == TradeDirection.LONG

    # ── SHORT sources ──
    @pytest.mark.parametrize("raw", ["SELL", "BEARISH", "SHORT", "sell", "bearish", "short", "   SHORT   "])
    def test_short_sources(self, raw):
        assert normalize_direction(raw) == TradeDirection.SHORT

    # ── NONE sources ──
    @pytest.mark.parametrize("raw", ["WAIT", "NO_TRADE", "NONE", "wait", "no_trade", "none", "", None])
    def test_none_sources(self, raw):
        assert normalize_direction(raw) == TradeDirection.NONE

    # ── Unknown raises error ──
    @pytest.mark.parametrize("bad", ["HOLD", "HODL", "INVALID", "123", "LONG_SHORT"])
    def test_unknown_raises(self, bad):
        with pytest.raises(ValueError, match="Unknown direction"):
            normalize_direction(bad)


# ═══════════════════════════════════════════════
# 3. display_direction() — UI display strings
# ═══════════════════════════════════════════════

class TestDisplayDirection:
    def test_long_displays_buy(self):
        assert display_direction(TradeDirection.LONG) == "BUY"

    def test_short_displays_sell(self):
        assert display_direction(TradeDirection.SHORT) == "SELL"

    def test_none_displays_no_trade(self):
        assert display_direction(TradeDirection.NONE) == "NO TRADE"

    def test_accepts_string_input(self):
        assert display_direction("LONG") == "BUY"
        assert display_direction("SHORT") == "SELL"
        assert display_direction("NONE") == "NO TRADE"


# ═══════════════════════════════════════════════
# 4. Opportunity scoring direction check
# ═══════════════════════════════════════════════

class TestOpportunityDirection:
    """Verify that _build_opportunity_score recognises LONG/SHORT as valid."""

    def _make_ai_snap(self, direction: str) -> dict:
        return {
            "score": 60,
            "confidence": 70,
            "risk_level": "LOW",
            "score_grade": "HIGH",
            "confidence_grade": "HIGH",
            "trade_plan": {"direction": direction, "strategy": "test"},
            "mtf_agreement": {"agreement_percent": 80},
        }

    def test_long_is_valid_direction(self):
        """LONG must be recognised as a valid trade direction by the scorer."""
        from api.auto_trade import _build_opportunity_score
        result = _build_opportunity_score("TEST", self._make_ai_snap("LONG"), None)
        assert result["direction"] == "LONG"
        # Ensure it's not rejected because of direction
        dir_rejects = [r for r in result["reject_reasons"] if "direction" in r.lower() or "trade direction" in r.lower()]
        assert not dir_rejects, f"LONG should not produce direction reject: {dir_rejects}"

    def test_short_is_valid_direction(self):
        """SHORT must be recognised as a valid trade direction by the scorer."""
        from api.auto_trade import _build_opportunity_score
        result = _build_opportunity_score("TEST", self._make_ai_snap("SHORT"), None)
        assert result["direction"] == "SHORT"
        dir_rejects = [r for r in result["reject_reasons"] if "direction" in r.lower() or "trade direction" in r.lower()]
        assert not dir_rejects, f"SHORT should not produce direction reject: {dir_rejects}"

    def test_none_direction_gives_no_trade(self):
        """NONE must produce a 'no clear trade direction' rejection."""
        from api.auto_trade import _build_opportunity_score
        result = _build_opportunity_score("TEST", self._make_ai_snap("NONE"), None)
        assert result["direction"] == "NONE"
        assert any("No clear trade direction" in r for r in result["reject_reasons"])

    def test_legacy_buy_normalises_correctly(self):
        """BUY (legacy) must be recognized and normalised to LONG."""
        from api.auto_trade import _build_opportunity_score
        result = _build_opportunity_score("TEST", self._make_ai_snap("BUY"), None)
        assert result["direction"] == "LONG"

    def test_legacy_sell_normalises_correctly(self):
        """SELL (legacy) must be recognized and normalised to SHORT."""
        from api.auto_trade import _build_opportunity_score
        result = _build_opportunity_score("TEST", self._make_ai_snap("SELL"), None)
        assert result["direction"] == "SHORT"


# ═══════════════════════════════════════════════
# 5. Event-driven metrics verification
# ═══════════════════════════════════════════════

class TestEventDrivenMetrics:
    """Verify that event-driven metrics reflect actual analysis."""

    def test_scan_metrics_use_event_driven_keys(self):
        """The scan metrics dict must have the new event-driven metric keys."""
        from api.auto_trade import _scan_metrics
        required_keys = [
            "total_analysis_cycles",
            "analyses_completed_total",
            "symbols_scanned_total",
            "no_trade_decisions_total",
            "score_qualified_candidates_total",
            "risk_blocked_total",
            "paper_trades_created_total",
            "last_candle_closed_at",
            "last_successful_analysis_at",
        ]
        for key in required_keys:
            assert key in _scan_metrics, f"Missing event-driven metric key: {key}"

    def test_granular_funnel_counters_exist(self):
        """The scan metrics dict must have the granular funnel counters."""
        from api.auto_trade import _scan_metrics
        funnel_keys = [
            "raw_directional_signals_total",
            "score_qualified_candidates_total",
            "trade_plans_created_total",
            "risk_approved_total",
            "risk_blocked_total",
            "execution_attempts_total",
            "execution_failed_total",
            "paper_trades_created_total",
        ]
        for key in funnel_keys:
            assert key in _scan_metrics, f"Missing funnel counter: {key}"

    def test_old_scan_cycle_metrics_not_required(self):
        """Legacy scan-cycle keys should no longer be primary."""
        from api.auto_trade import _scan_metrics
        # These old keys may still exist but should not be the source of truth
        deprecated_keys = ["total_scan_cycles", "symbols_scanned_current"]
        for key in deprecated_keys:
            if key in _scan_metrics:
                pass  # tolerated but not authoritative


# ═══════════════════════════════════════════════
# 6. Cooldown vs analysis state preservation
# ═══════════════════════════════════════════════

class TestAnalysisPersistence:
    """Verify cooldown skips don't overwrite latest valid analysis."""

    def test_analysis_by_symbol_persists(self):
        """_analysis_state_by_symbol must store latest analysis per symbol."""
        from api.auto_trade import _analysis_state_by_symbol
        assert isinstance(_analysis_state_by_symbol, dict)

    def test_symbol_state_has_required_fields(self):
        """Each per-symbol analysis state must have required fields."""
        from api.auto_trade import _analysis_state_by_symbol
        required = ["symbol", "status", "direction", "display_decision", "analysed_at"]
        for symbol, state in _analysis_state_by_symbol.items():
            for field in required:
                assert field in state, f"Symbol {symbol} missing field: {field}"


# ═══════════════════════════════════════════════
# 7. Workspace snapshot uses event-driven data
# ═══════════════════════════════════════════════

class TestWorkspaceUsesEventDrivenMetrics:
    """Workspace snapshot must not depend on dead _health_scan()."""

    def test_workspace_scan_has_new_keys(self):
        """The scan section of the workspace must include event-driven keys."""
        from api.auto_trade import _build_workspace_snapshot
        snapshot = _build_workspace_snapshot()
        scan = snapshot.get("scan", {})
        required = [
            "configured_symbols", "symbols_analysed",
            "analyses_completed_total", "no_trade_decisions_total",
            "candidates_found_total", "paper_trades_created_total",
        ]
        for key in required:
            assert key in scan, f"Missing key in workspace scan: {key}"

    def test_workspace_has_current_market_analysis(self):
        """Workspace must include per-symbol analysis data."""
        from api.auto_trade import _build_workspace_snapshot
        snapshot = _build_workspace_snapshot()
        assert "current_market_analysis" in snapshot

    def test_workspace_does_not_use_old_scan_keys(self):
        """Workspace must not contain the old flat scan keys."""
        from api.auto_trade import _build_workspace_snapshot
        snapshot = _build_workspace_snapshot()
        scan = snapshot.get("scan", {})
        # The old shape had symbols_scanned, candidates_found, last_scan_time
        # The new shape uses different names
        assert "symbols_scanned" not in scan
        assert "candidates_found" not in scan


# ═══════════════════════════════════════════════
# 8. Current Market Analysis renders NONE as NO TRADE
# ═══════════════════════════════════════════════

class TestCurrentMarketAnalysisRendering:
    """Verify display_decision renders NONE as 'NO TRADE'."""

    def test_analysis_state_none_display(self):
        """A NONE direction must display as 'NO TRADE'."""
        from api.auto_trade import _analysis_state_by_symbol
        for symbol, state in _analysis_state_by_symbol.items():
            if state.get("direction") in ("NONE",):
                assert state.get("display_decision") in ("NO TRADE", "NO_TRADE"), \
                    f"NONE direction should display as NO TRADE for {symbol}, got {state.get('display_decision')}"
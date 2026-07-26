"""
Phase 57A Tests — Options Engine Foundation & Provider Abstraction

Tests models, config, provider protocol, Zerodha provider (mocked Kite),
and Mock option provider.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from options.models import (
    OptionType,
    OptionDirection,
    OptionDecisionStatus,
    OptionPositionStatus,
    OptionChainSource,
    OptionTimeframe,
    DEFAULT_LOT_SIZES,
    UnderlyingSnapshot,
    OptionInstrument,
    OptionQuote,
    OptionChainSlice,
    OptionChainSnapshot,
    OptionStrikeAnalysis,
    OptionDecision,
    OptionPosition,
    OptionRiskCheck,
    OptionSizing,
    OptionChainFreshness,
    AIDecisionFingerprint,
    ExitOrder,
)
from options.config import OptionEngineConfig
from options.providers.base import OptionDataProvider, ProviderCapabilities
from options.providers.mock import MockOptionProvider


# ═══════════════════════════════════════════════════════════════════
#  1. Model Tests
# ═══════════════════════════════════════════════════════════════════


class TestUnderlyingSnapshot:
    def test_valid(self):
        snap = UnderlyingSnapshot(
            symbol="NIFTY 50", ltp=24500, prev_close=24400,
            day_open=24420, day_high=24550, day_low=24380, day_volume=100000,
        )
        assert snap.symbol == "NIFTY 50"
        assert snap.ltp == 24500
        assert snap.day_range == 170

    def test_zero_ltp_raises(self):
        with pytest.raises(ValueError, match="ltp must be positive"):
            UnderlyingSnapshot(
                symbol="X", ltp=0, prev_close=100,
                day_open=100, day_high=110, day_low=90, day_volume=1000,
            )

    def test_high_lt_low_raises(self):
        with pytest.raises(ValueError, match="day_high must be >= day_low"):
            UnderlyingSnapshot(
                symbol="X", ltp=100, prev_close=100,
                day_open=100, day_high=90, day_low=110, day_volume=1000,
            )


class TestOptionInstrument:
    def test_valid_ce(self):
        inst = OptionInstrument(
            symbol="NIFTY24JUL24500CE", underlying="NIFTY 50",
            expiry=date(2025, 7, 31), strike=24500, option_type=OptionType.CE,
        )
        assert inst.option_type == OptionType.CE
        assert inst.key == "NIFTY 50-2025-07-31-24500-CE"

    def test_negative_strike_raises(self):
        with pytest.raises(ValueError, match="strike must be non-negative"):
            OptionInstrument(
                symbol="X", underlying="X", expiry=date.today(),
                strike=-100, option_type=OptionType.PE,
            )

    def test_zero_lot_raises(self):
        with pytest.raises(ValueError, match="lot_size must be positive"):
            OptionInstrument(
                symbol="X", underlying="X", expiry=date.today(),
                strike=100, option_type=OptionType.CE, lot_size=0,
            )


class TestOptionQuote:
    def test_valid(self):
        inst = OptionInstrument(
            symbol="T", underlying="NIFTY 50", expiry=date.today(),
            strike=24500, option_type=OptionType.CE,
        )
        q = OptionQuote(instrument=inst, ltp=150.5, bid=149, ask=152, oi=5000, volume=300)
        assert q.spread == 3.0
        assert q.is_tradeable is True

    def test_zero_ltp_not_tradeable(self):
        inst = OptionInstrument(
            symbol="T", underlying="NIFTY 50", expiry=date.today(),
            strike=24500, option_type=OptionType.CE,
        )
        q = OptionQuote(instrument=inst, ltp=0, oi=5000)
        assert q.is_tradeable is False

    def test_negative_ltp_raises(self):
        inst = OptionInstrument(
            symbol="T", underlying="NIFTY 50", expiry=date.today(),
            strike=24500, option_type=OptionType.CE,
        )
        with pytest.raises(ValueError, match="ltp must be non-negative"):
            OptionQuote(instrument=inst, ltp=-10)


class TestOptionChainSlice:
    def _make_slice(self, strikes, spot):
        today = date.today()
        ce = {}
        pe = {}
        for s in strikes:
            inst_ce = OptionInstrument(
                symbol=f"CE{s}", underlying="NIFTY 50", expiry=today,
                strike=s, option_type=OptionType.CE,
            )
            inst_pe = OptionInstrument(
                symbol=f"PE{s}", underlying="NIFTY 50", expiry=today,
                strike=s, option_type=OptionType.PE,
            )
            ce[s] = OptionQuote(instrument=inst_ce, ltp=max(100 - abs(s - spot) * 0.5, 1), oi=1000)
            pe[s] = OptionQuote(instrument=inst_pe, ltp=max(abs(s - spot) * 0.5 + 10, 1), oi=1000)
        return OptionChainSlice(
            underlying="NIFTY 50", expiry=today, strikes=strikes,
            ce_quotes=ce, pe_quotes=pe, spot_price=spot,
        )

    def test_atm_strike(self):
        s = self._make_slice([24400, 24450, 24500, 24550, 24600], 24520)
        assert s.atm_strike() == 24500

    def test_otm_ce(self):
        s = self._make_slice([24400, 24450, 24500, 24550, 24600], 24500)
        otm = s.otm_strikes(OptionType.CE, count=2)
        assert len(otm) == 2
        assert all(q.instrument.strike > 24500 for q in otm)

    def test_otm_pe(self):
        s = self._make_slice([24400, 24450, 24500, 24550, 24600], 24500)
        otm = s.otm_strikes(OptionType.PE, count=2)
        assert len(otm) == 2
        assert all(q.instrument.strike < 24500 for q in otm)

    def test_empty_strikes_raises(self):
        today = date.today()
        with pytest.raises(ValueError, match="strikes list must not be empty"):
            OptionChainSlice(
                underlying="X", expiry=today, strikes=[],
                ce_quotes={}, pe_quotes={}, spot_price=100,
            )


class TestOptionChainSnapshot:
    def test_nearest_expiry(self):
        today = date.today()
        e1 = today + timedelta(days=3)
        e2 = today + timedelta(days=10)
        snap = OptionChainSnapshot(
            underlying="NIFTY 50", spot_price=24500,
            expiries={e1: MagicMock(), e2: MagicMock()},
        )
        assert snap.nearest_expiry() == e1

    def test_empty_expiries(self):
        snap = OptionChainSnapshot(
            underlying="NIFTY 50", spot_price=24500, expiries={},
        )
        assert snap.nearest_expiry() is None


class TestOptionDecision:
    def test_valid(self):
        d = OptionDecision(
            analysis_cycle_id="c1", underlying="NIFTY 50",
            strike=24500, option_type=OptionType.CE,
            confidence=0.75, strategy_version="v1",
        )
        assert d.is_approved is False
        key = d.idempotency_key
        assert "c1" in key
        assert "NIFTY 50" in key
        assert "24500" in key

    def test_invalid_confidence(self):
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            OptionDecision(confidence=1.5)

    def test_negative_strike_raises(self):
        with pytest.raises(ValueError, match="strike must be non-negative"):
            OptionDecision(strike=-100)


class TestOptionPosition:
    def test_update_pnl_long(self):
        p = OptionPosition(
            entry_price=100, quantity=50, direction=OptionDirection.LONG,
            lot_size=25,
        )
        p.update_pnl(110)
        assert p.unrealized_pnl == 500  # (110-100)*50
        assert p.highest_premium == 110

    def test_update_pnl_short(self):
        p = OptionPosition(
            entry_price=100, quantity=50, direction=OptionDirection.SHORT,
            lot_size=25,
        )
        p.update_pnl(90)
        assert p.unrealized_pnl == 500  # (100-90)*50

    def test_close(self):
        p = OptionPosition(
            entry_price=100, quantity=50, direction=OptionDirection.LONG,
            lot_size=25, status=OptionPositionStatus.OPEN,
        )
        p.close(120, "target_hit")
        assert p.exit_price == 120
        assert p.exit_reason == "target_hit"
        assert p.realized_pnl == 1000  # (120-100)*50

    def test_pnl_pct(self):
        p = OptionPosition(entry_price=100, quantity=50, lot_size=25)
        p.update_pnl(120)
        assert p.pnl_pct == pytest.approx(20.0)


class TestOptionChainFreshness:
    def test_fresh(self):
        f = OptionChainFreshness(
            underlying="NIFTY 50",
            fetched_at=datetime.now(timezone.utc),
            max_age_seconds=30.0,
        )
        assert f.is_fresh is True
        assert f.is_stale is False

    def test_stale(self):
        f = OptionChainFreshness(
            underlying="NIFTY 50",
            fetched_at=datetime.now(timezone.utc) - timedelta(seconds=60),
            max_age_seconds=30.0,
        )
        assert f.is_fresh is False
        assert f.is_stale is True


class TestAIDecisionFingerprint:
    def test_fresh(self):
        fp = AIDecisionFingerprint(
            analysis_cycle_id="c1", candle_version="v1",
            candle_ts="2025-01-01T00:00:00", ai_signal="BUY",
            confidence=0.8, fetched_at=datetime.now(timezone.utc),
        )
        assert fp.is_fresh is True

    def test_stale(self):
        fp = AIDecisionFingerprint(
            analysis_cycle_id="c1", candle_version="v1",
            candle_ts="2025-01-01T00:00:00", ai_signal="BUY",
            confidence=0.8, fetched_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        )
        assert fp.is_fresh is False


class TestDefaultLotSizes:
    def test_all_positive(self):
        for sym, lot in DEFAULT_LOT_SIZES.items():
            assert lot > 0, f"{sym} lot_size must be > 0"

    def test_known_symbols(self):
        assert "NIFTY 50" in DEFAULT_LOT_SIZES
        assert "BANKNIFTY" in DEFAULT_LOT_SIZES
        assert "SENSEX" in DEFAULT_LOT_SIZES


# ═══════════════════════════════════════════════════════════════════
#  2. Config Tests
# ═══════════════════════════════════════════════════════════════════


class TestOptionEngineConfig:
    def test_defaults(self):
        c = OptionEngineConfig()
        assert c.provider == "MOCK"
        assert c.shadow_enabled is True
        assert c.real_orders_blocked is True
        assert c.max_capital_per_trade == 50_000.0

    def test_invalid_provider(self):
        with pytest.raises(ValueError, match="provider must be one of"):
            OptionEngineConfig(provider="INVALID")

    def test_invalid_lot_size(self):
        with pytest.raises(ValueError, match="lot_sizes"):
            OptionEngineConfig(lot_sizes={"NIFTY 50": 0})

    def test_invalid_otm_range(self):
        with pytest.raises(ValueError, match="otm_range"):
            OptionEngineConfig(otm_range=(3.0, 1.0))

    def test_invalid_capital(self):
        with pytest.raises(ValueError, match="max_capital_per_trade"):
            OptionEngineConfig(max_capital_per_trade=-1)

    def test_invalid_confidence(self):
        with pytest.raises(ValueError, match="min_confidence"):
            OptionEngineConfig(min_confidence=1.5)

    def test_get_lot_size_known(self):
        c = OptionEngineConfig()
        assert c.get_lot_size("NIFTY 50") == 25
        assert c.get_lot_size("BANKNIFTY") == 15

    def test_get_lot_size_unknown(self):
        c = OptionEngineConfig()
        assert c.get_lot_size("UNKNOWN") == 25

    def test_from_env(self):
        with patch.dict(os.environ, {
            "OPTIONS_ENGINE_PROVIDER": "ZERODHA",
            "OPTIONS_ENGINE_UNDERLYINGS": "SENSEX",
            "OPTIONS_MAX_CAPITAL_PER_TRADE": "100000",
        }):
            c = OptionEngineConfig.from_env()
            assert c.provider == "ZERODHA"
            assert c.underlyings == ("SENSEX",)
            assert c.max_capital_per_trade == 100_000.0

    def test_to_dict(self):
        c = OptionEngineConfig()
        d = c.to_dict()
        assert d["provider"] == "MOCK"
        assert d["shadow_enabled"] is True
        assert "max_capital_per_trade" in d


# ═══════════════════════════════════════════════════════════════════
#  3. Provider Protocol Tests
# ═══════════════════════════════════════════════════════════════════


class TestProviderProtocol:
    def test_mock_implements_protocol(self):
        p = MockOptionProvider()
        assert isinstance(p, OptionDataProvider)

    def test_capabilities(self):
        p = MockOptionProvider()
        caps = p.capabilities()
        assert caps.provider_name == "MOCK"
        assert caps.source == OptionChainSource.MOCK
        assert caps.supports_live_chain is True

    def test_provider_capabilities_frozen(self):
        caps = ProviderCapabilities(
            provider_name="X", source=OptionChainSource.MOCK,
        )
        with pytest.raises(AttributeError):
            caps.provider_name = "Y"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════
#  4. Mock Provider Tests
# ═══════════════════════════════════════════════════════════════════


class TestMockOptionProvider:
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        p = MockOptionProvider()
        assert await p.connect() is True
        h = await p.health()
        assert h["connected"] is True
        await p.disconnect()
        h = await p.health()
        assert h["connected"] is False

    @pytest.mark.asyncio
    async def test_fetch_chain_snapshot(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        snap = await p.fetch_chain_snapshot("NIFTY 50")
        assert snap.underlying == "NIFTY 50"
        assert snap.spot_price == 24500.0
        assert len(snap.expiries) > 0
        # Each expiry should have strikes
        for exp, s in snap.expiries.items():
            assert len(s.strikes) == 21
            assert len(s.ce_quotes) == 21
            assert len(s.pe_quotes) == 21
            assert s.spot_price == 24500.0

    @pytest.mark.asyncio
    async def test_fetch_chain_slice(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        expiries = await p.get_available_expiries("NIFTY 50")
        assert len(expiries) > 0
        s = await p.fetch_chain_slice("NIFTY 50", expiries[0])
        assert s.expiry == expiries[0]
        assert len(s.strikes) > 0

    @pytest.mark.asyncio
    async def test_fetch_option_quote(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        expiries = await p.get_available_expiries("NIFTY 50")
        q = await p.fetch_option_quote("NIFTY 50", expiries[0], 24500, "CE")
        assert q is not None
        assert q.instrument.strike == 24500
        assert q.instrument.option_type == OptionType.CE
        assert q.ltp > 0

    @pytest.mark.asyncio
    async def test_fetch_instruments(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        insts = await p.fetch_instruments("NIFTY 50")
        assert len(insts) > 0
        assert all(isinstance(i, OptionInstrument) for i in insts)

    @pytest.mark.asyncio
    async def test_otm_ce_premium_lt_atm(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        expiries = await p.get_available_expiries("NIFTY 50")
        atm_q = await p.fetch_option_quote("NIFTY 50", expiries[0], 24500, "CE")
        otm_q = await p.fetch_option_quote("NIFTY 50", expiries[0], 24700, "CE")
        assert atm_q is not None and otm_q is not None
        assert otm_q.ltp < atm_q.ltp

    @pytest.mark.asyncio
    async def test_request_log(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        await p.fetch_chain_snapshot("NIFTY 50")
        log = p.get_request_log()
        assert len(log) == 1
        assert log[0]["method"] == "fetch_chain_snapshot"

    @pytest.mark.asyncio
    async def test_set_spot(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        p.set_spot(25000.0)
        snap = await p.fetch_chain_snapshot("NIFTY 50")
        assert snap.spot_price == 25000.0

    @pytest.mark.asyncio
    async def test_chain_snapshot_freshness(self):
        p = MockOptionProvider(spot=24500.0)
        await p.connect()
        snap = await p.fetch_chain_snapshot("NIFTY 50")
        f = OptionChainFreshness(
            underlying="NIFTY 50",
            fetched_at=snap.fetched_at,
            max_age_seconds=15.0,
        )
        assert f.is_fresh is True


# ═══════════════════════════════════════════════════════════════════
#  5. Zerodha Provider Tests (mocked Kite)
# ═══════════════════════════════════════════════════════════════════


class TestZerodhaOptionProvider:
    def _make_kite_provider(self):
        kite = MagicMock()
        kite.option_chain.return_value = self._sample_chain()
        kp = MagicMock()
        kp.auth.kite = kite
        kp.auth.is_authenticated = True
        return kp, kite

    @staticmethod
    def _sample_chain():
        today = date.today()
        expiry = (today + timedelta(days=3)).isoformat()
        chain = {}
        instruments = []
        for strike in [24400, 24450, 24500, 24550, 24600]:
            for ins_type in ["CE", "PE"]:
                instruments.append({
                    "instrument_token": strike + (1 if ins_type == "CE" else 2),
                    "strike": strike,
                    "instrument_type": ins_type,
                    "expiry": expiry,
                    "tradingsymbol": f"NIFTY {expiry} {strike} {ins_type}",
                    "lot_size": 25,
                    "tick_size": 0.05,
                    "quote": {
                        "last_price": max(100 - abs(strike - 24500) * 0.5, 1),
                        "oi": 5000 - abs(strike - 24500) * 2,
                        "volume": 500,
                        "bid": 99.0,
                        "ask": 101.0,
                    },
                })
        chain[expiry] = instruments
        return chain

    @pytest.mark.asyncio
    async def test_connect_success(self):
        from options.providers.zerodha import ZerodhaOptionProvider
        kp, _ = self._make_kite_provider()
        p = ZerodhaOptionProvider(kite_provider=kp)
        assert await p.connect() is True
        h = await p.health()
        assert h["connected"] is True

    @pytest.mark.asyncio
    async def test_connect_no_provider(self):
        from options.providers.zerodha import ZerodhaOptionProvider
        p = ZerodhaOptionProvider()
        assert await p.connect() is False

    @pytest.mark.asyncio
    async def test_fetch_chain_snapshot(self):
        from options.providers.zerodha import ZerodhaOptionProvider
        kp, _ = self._make_kite_provider()
        p = ZerodhaOptionProvider(kite_provider=kp)
        await p.connect()
        snap = await p.fetch_chain_snapshot("NIFTY 50")
        assert snap.underlying == "NIFTY 50"
        assert len(snap.expiries) > 0

    @pytest.mark.asyncio
    async def test_fetch_chain_not_connected(self):
        from options.providers.zerodha import ZerodhaOptionProvider
        p = ZerodhaOptionProvider()
        with pytest.raises(RuntimeError, match="not connected"):
            await p.fetch_chain_snapshot("NIFTY 50")

    @pytest.mark.asyncio
    async def test_fetch_unknown_underlying(self):
        from options.providers.zerodha import ZerodhaOptionProvider
        kp, _ = self._make_kite_provider()
        p = ZerodhaOptionProvider(kite_provider=kp)
        await p.connect()
        with pytest.raises(ValueError, match="Unknown underlying"):
            await p.fetch_chain_snapshot("UNKNOWN")

    @pytest.mark.asyncio
    async def test_fetch_chain_kite_error(self):
        from options.providers.zerodha import ZerodhaOptionProvider
        kp, kite = self._make_kite_provider()
        kite.option_chain.side_effect = Exception("API timeout")
        p = ZerodhaOptionProvider(kite_provider=kp)
        await p.connect()
        with pytest.raises(RuntimeError, match="fetch failed"):
            await p.fetch_chain_snapshot("NIFTY 50")
        h = await p.health()
        assert h["error_count"] == 1

    @pytest.mark.asyncio
    async def test_capabilities(self):
        from options.providers.zerodha import ZerodhaOptionProvider
        p = ZerodhaOptionProvider()
        caps = p.capabilities()
        assert caps.source == OptionChainSource.ZERODHA
        assert "NIFTY 50" in caps.underlyings

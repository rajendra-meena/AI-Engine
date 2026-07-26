"""
Regime Detector — detects 14 market regimes from context, structure, indicator, and MTF data.

Each sub-detector returns (confidence, factors[]). Main detect() picks the highest.
"""

from __future__ import annotations

from typing import Any

from market_regime.snapshot import RegimeSnapshot


REGIME_LIST = [
    "STRONG_BULL_TREND", "STRONG_BEAR_TREND",
    "WEAK_BULL_TREND", "WEAK_BEAR_TREND",
    "SIDEWAYS_RANGE", "HIGH_VOLATILITY", "LOW_VOLATILITY",
    "BREAKOUT", "FAKE_BREAKOUT", "MEAN_REVERSION",
    "NEWS_DRIVEN", "OPENING_AUCTION", "CLOSING_SESSION",
    "ILLIQUID_MARKET",
]

REGIME_CATEGORIES = {
    "STRONG_BULL_TREND": "TREND",
    "STRONG_BEAR_TREND": "TREND",
    "WEAK_BULL_TREND": "TREND",
    "WEAK_BEAR_TREND": "TREND",
    "SIDEWAYS_RANGE": "RANGE",
    "HIGH_VOLATILITY": "VOLATILITY",
    "LOW_VOLATILITY": "VOLATILITY",
    "BREAKOUT": "BREAKOUT",
    "FAKE_BREAKOUT": "BREAKOUT",
    "MEAN_REVERSION": "SPECIAL",
    "NEWS_DRIVEN": "SPECIAL",
    "OPENING_AUCTION": "SPECIAL",
    "CLOSING_SESSION": "SPECIAL",
    "ILLIQUID_MARKET": "SPECIAL",
}

CONFIDENCE_THRESHOLD = 40  # Minimum confidence to accept a regime


class RegimeDetector:
    """Detects 14 market regimes from engine outputs."""

    @staticmethod
    def detect(
        context_snap: dict[str, Any] | None = None,
        structure_snap: dict[str, Any] | None = None,
        indicator_snap: dict[str, Any] | None = None,
        mtf_snap: dict[str, Any] | None = None,
        previous_regime: str | None = None,
        regime_age_bars: int = 0,
    ) -> RegimeSnapshot:
        """Run all 14 sub-detectors and return the most confident match."""
        detectors: list[tuple[str, tuple[int, list[str]]]] = [
            ("STRONG_BULL_TREND", RegimeDetector._detect_strong_bull_trend(context_snap, structure_snap, indicator_snap, mtf_snap)),
            ("STRONG_BEAR_TREND", RegimeDetector._detect_strong_bear_trend(context_snap, structure_snap, indicator_snap, mtf_snap)),
            ("WEAK_BULL_TREND", RegimeDetector._detect_weak_bull_trend(context_snap, structure_snap, indicator_snap, mtf_snap)),
            ("WEAK_BEAR_TREND", RegimeDetector._detect_weak_bear_trend(context_snap, structure_snap, indicator_snap, mtf_snap)),
            ("SIDEWAYS_RANGE", RegimeDetector._detect_sideways_range(context_snap, structure_snap, indicator_snap, mtf_snap)),
            ("HIGH_VOLATILITY", RegimeDetector._detect_high_volatility(context_snap, indicator_snap)),
            ("LOW_VOLATILITY", RegimeDetector._detect_low_volatility(context_snap, indicator_snap)),
            ("BREAKOUT", RegimeDetector._detect_breakout(context_snap, structure_snap, indicator_snap, mtf_snap)),
            ("FAKE_BREAKOUT", RegimeDetector._detect_fake_breakout(context_snap, structure_snap, indicator_snap, mtf_snap)),
            ("MEAN_REVERSION", RegimeDetector._detect_mean_reversion(context_snap, indicator_snap)),
            ("NEWS_DRIVEN", RegimeDetector._detect_news_driven(context_snap, indicator_snap)),
            ("OPENING_AUCTION", RegimeDetector._detect_opening_auction(context_snap)),
            ("CLOSING_SESSION", RegimeDetector._detect_closing_session(context_snap)),
            ("ILLIQUID_MARKET", RegimeDetector._detect_illiquid_market(context_snap, indicator_snap, structure_snap)),
        ]

        best_regime = "SIDEWAYS_RANGE"
        best_confidence = 0
        best_factors: list[str] = []

        for name, (confidence, factors) in detectors:
            if confidence > best_confidence and confidence >= CONFIDENCE_THRESHOLD:
                best_confidence = confidence
                best_regime = name
                best_factors = factors

        # If nothing found above threshold, default to SIDEWAYS_RANGE with low confidence
        if best_confidence < CONFIDENCE_THRESHOLD:
            best_regime = "SIDEWAYS_RANGE"
            best_confidence = max(20, best_confidence)
            if not best_factors:
                best_factors = ["No clear regime detected — defaulting to range"]

        category = REGIME_CATEGORIES.get(best_regime, "UNKNOWN")

        return RegimeSnapshot(
            regime=best_regime,
            regime_category=category,
            confidence=min(100, best_confidence),
            supporting_factors=tuple(best_factors),
            previous_regime=previous_regime,
            regime_age_bars=regime_age_bars,
        )

    # ── Trend sub-detectors ──

    @staticmethod
    def _detect_strong_bull_trend(ctx: dict | None, struct: dict | None, ind: dict | None, mtf: dict | None) -> tuple[int, list[str]]:
        """EMA 50>200, ADX>30, HH/HL structure, VWAP support, strong volume."""
        factors: list[str] = []
        confidence = 0

        # Trend must be bullish/bullish
        trend = _s(struct, "trend", _s(ctx, "trend", ""))
        if trend.upper() not in ("UPTREND", "BULLISH"):
            return (0, [])

        strength = _s(struct, "trend_strength", _s(ctx, "trend_strength", ""))
        if strength.upper() == "STRONG":
            confidence += 30
            factors.append("strong_trend_strength")

        # ADX > 30
        adx = _n(ind, "adx_14")
        if adx and adx > 30:
            confidence += 20
            factors.append(f"adx_{adx:.0f}")
        elif adx and adx > 25:
            confidence += 10

        # EMA alignment
        ema9 = _n(ind, "ema_9")
        ema20 = _n(ind, "ema_20")
        ema50 = _n(ind, "ema_50")
        if ema9 and ema20 and ema50 and ema9 > ema20 > ema50:
            confidence += 20
            factors.append("ema_bullish_alignment")
        elif ema9 and ema20 and ema9 > ema20:
            confidence += 10

        # Higher Highs / Higher Lows (HH/HL structure)
        bos = _n(struct, "bos_count", 0)
        if isinstance(bos, (int, float)) and bos > 0:
            confidence += 10
            factors.append(f"{int(bos)}_bos_detected")

        # VWAP support
        close = _n(ind, "candle_close")
        vwap = _n(ind, "vwap")
        if close and vwap and close > vwap:
            confidence += 10
            factors.append("vwap_support")

        # Volume confirmation
        vol = _n(ind, "candle_volume") or _n(ind, "volume", 0)
        avg_vol = _n(ind, "average_volume", 0)
        if vol and avg_vol and avg_vol > 0 and vol > avg_vol * 1.2:
            confidence += 10
            factors.append("strong_volume")

        return (min(100, confidence), factors)

    @staticmethod
    def _detect_strong_bear_trend(ctx: dict | None, struct: dict | None, ind: dict | None, mtf: dict | None) -> tuple[int, list[str]]:
        """EMA 50<200, ADX>30, LH/LL structure, VWAP resistance, strong volume."""
        factors: list[str] = []
        confidence = 0

        trend = _s(struct, "trend", _s(ctx, "trend", ""))
        if trend.upper() not in ("DOWNTREND", "BEARISH"):
            return (0, [])

        strength = _s(struct, "trend_strength", _s(ctx, "trend_strength", ""))
        if strength.upper() == "STRONG":
            confidence += 30
            factors.append("strong_trend_strength")

        adx = _n(ind, "adx_14")
        if adx and adx > 30:
            confidence += 20
            factors.append(f"adx_{adx:.0f}")
        elif adx and adx > 25:
            confidence += 10

        ema9 = _n(ind, "ema_9")
        ema20 = _n(ind, "ema_20")
        ema50 = _n(ind, "ema_50")
        if ema9 and ema20 and ema50 and ema9 < ema20 < ema50:
            confidence += 20
            factors.append("ema_bearish_alignment")

        choch = _n(struct, "choch_count", 0)
        if isinstance(choch, (int, float)) and choch > 0:
            confidence += 10
            factors.append(f"{int(choch)}_choch_detected")

        close = _n(ind, "candle_close")
        vwap = _n(ind, "vwap")
        if close and vwap and close < vwap:
            confidence += 10
            factors.append("vwap_resistance")

        vol = _n(ind, "candle_volume") or _n(ind, "volume", 0)
        avg_vol = _n(ind, "average_volume", 0)
        if vol and avg_vol and avg_vol > 0 and vol > avg_vol * 1.2:
            confidence += 10
            factors.append("strong_volume")

        return (min(100, confidence), factors)

    @staticmethod
    def _detect_weak_bull_trend(ctx: dict | None, struct: dict | None, ind: dict | None, mtf: dict | None) -> tuple[int, list[str]]:
        """ADX 20-30, partial EMA alignment, HH/HL but with pullbacks."""
        factors: list[str] = []
        confidence = 0

        trend = _s(struct, "trend", _s(ctx, "trend", ""))
        if trend.upper() not in ("UPTREND", "BULLISH"):
            return (0, [])

        strength = _s(struct, "trend_strength", _s(ctx, "trend_strength", ""))
        if strength.upper() == "WEAK":
            confidence += 20
        elif strength.upper() == "MODERATE":
            confidence += 15

        adx = _n(ind, "adx_14")
        if adx and 20 <= adx <= 30:
            confidence += 20
            factors.append(f"adx_{adx:.0f}_moderate")
        elif adx and adx > 30:
            confidence += 5

        ema9 = _n(ind, "ema_9")
        ema20 = _n(ind, "ema_20")
        if ema9 and ema20 and ema9 > ema20:
            confidence += 15
            factors.append("partial_ema_alignment")

        bos = _n(struct, "bos_count", 0)
        if isinstance(bos, (int, float)) and bos > 0:
            confidence += 10
            factors.append("bos_detected")

        return (min(100, confidence), factors)

    @staticmethod
    def _detect_weak_bear_trend(ctx: dict | None, struct: dict | None, ind: dict | None, mtf: dict | None) -> tuple[int, list[str]]:
        """ADX 20-30, partial EMA alignment, LH/LL but with pullbacks."""
        factors: list[str] = []
        confidence = 0

        trend = _s(struct, "trend", _s(ctx, "trend", ""))
        if trend.upper() not in ("DOWNTREND", "BEARISH"):
            return (0, [])

        if _s(struct, "trend_strength", "").upper() == "WEAK":
            confidence += 20

        adx = _n(ind, "adx_14")
        if adx and 20 <= adx <= 30:
            confidence += 20
            factors.append(f"adx_{adx:.0f}_moderate")

        ema9 = _n(ind, "ema_9")
        ema20 = _n(ind, "ema_20")
        if ema9 and ema20 and ema9 < ema20:
            confidence += 15
            factors.append("partial_ema_alignment")

        choch = _n(struct, "choch_count", 0)
        if isinstance(choch, (int, float)) and choch > 0:
            confidence += 10
            factors.append("choch_detected")

        return (min(100, confidence), factors)

    # ── Range sub-detector ──

    @staticmethod
    def _detect_sideways_range(ctx: dict | None, struct: dict | None, ind: dict | None, mtf: dict | None) -> tuple[int, list[str]]:
        """ADX<20, EMA flat/chop, no HH/HL, volatility compressing, bounded price."""
        factors: list[str] = []
        confidence = 0

        adx = _n(ind, "adx_14")
        if adx and adx < 20:
            confidence += 25
            factors.append(f"low_adx_{adx:.0f}")
        elif adx and adx < 25:
            confidence += 10

        valid = _b(struct, "valid_structure", True)
        bos = _n(struct, "bos_count", 0)
        if not valid or (isinstance(bos, (int, float)) and bos == 0):
            confidence += 15
            factors.append("no_bos")

        ema9 = _n(ind, "ema_9")
        ema20 = _n(ind, "ema_20")
        if ema9 and ema20:
            ema_diff_pct = abs(ema9 - ema20) / ema20 * 100
            if ema_diff_pct < 0.5:
                confidence += 15
                factors.append("emas_tight")
            elif ema_diff_pct < 1.0:
                confidence += 10

        vol_state = _s(ctx, "volatility_state", "")
        if vol_state.upper() == "CONTRACTING":
            confidence += 15
            factors.append("volatility_contracting")

        close = _n(ind, "candle_close")
        vwap = _n(ind, "vwap")
        if close and vwap:
            vwap_diff = abs(close - vwap) / vwap * 100
            if vwap_diff < 1.0:
                confidence += 10
                factors.append("near_vwap")

        return (min(100, confidence), factors)

    # ── Volatility sub-detectors ──

    @staticmethod
    def _detect_high_volatility(ctx: dict | None, ind: dict | None) -> tuple[int, list[str]]:
        factors: list[str] = []
        confidence = 0

        vol_state = _s(ctx, "volatility_state", "")
        if vol_state.upper() == "EXPANDING":
            confidence += 30
            factors.append("volatility_expanding")

        atr = _n(ind, "atr_14")
        close = _n(ind, "candle_close")
        if atr and close and close > 0:
            atr_pct = atr / close * 100
            if atr_pct > 2.0:
                confidence += 25
                factors.append(f"high_atr_{atr_pct:.1f}%")
            elif atr_pct > 1.5:
                confidence += 15
                factors.append("elevated_atr")

        return (min(100, confidence), factors)

    @staticmethod
    def _detect_low_volatility(ctx: dict | None, ind: dict | None) -> tuple[int, list[str]]:
        factors: list[str] = []
        confidence = 0

        vol_state = _s(ctx, "volatility_state", "")
        if vol_state.upper() == "CONTRACTING":
            confidence += 30
            factors.append("volatility_contracting")

        atr = _n(ind, "atr_14")
        close = _n(ind, "candle_close")
        if atr and close and close > 0:
            atr_pct = atr / close * 100
            if atr_pct < 0.5:
                confidence += 25
                factors.append(f"low_atr_{atr_pct:.2f}%")
            elif atr_pct < 0.8:
                confidence += 15
                factors.append("reduced_atr")

        return (min(100, confidence), factors)

    # ── Breakout sub-detectors ──

    @staticmethod
    def _detect_breakout(ctx: dict | None, struct: dict | None, ind: dict | None, mtf: dict | None) -> tuple[int, list[str]]:
        factors: list[str] = []
        confidence = 0

        mtf_cond = _s(mtf, "market_condition", "")
        if mtf_cond.upper() == "BREAKOUT":
            confidence += 25
            factors.append("mtf_breakout_condition")

        bos = _n(struct, "bos_count", 0)
        if isinstance(bos, (int, float)) and bos > 0:
            confidence += 20
            factors.append("bos_detected")

        momentum = _s(ctx, "momentum", "")
        if momentum.upper() in ("STRONG", "BULLISH"):
            confidence += 15
            factors.append("strong_momentum")

        vol = _n(ind, "candle_volume") or _n(ind, "volume", 0)
        avg_vol = _n(ind, "average_volume", 0)
        if vol and avg_vol and avg_vol > 0 and vol > avg_vol * 1.3:
            confidence += 15
            factors.append("volume_spike")

        mtf_align = _s(mtf, "alignment_level", "")
        if mtf_align in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT"):
            confidence += 10
            factors.append("mtf_aligned")

        return (min(100, confidence), factors)

    @staticmethod
    def _detect_fake_breakout(ctx: dict | None, struct: dict | None, ind: dict | None, mtf: dict | None) -> tuple[int, list[str]]:
        """BOS detected then immediate reversal, failed breakout."""
        factors: list[str] = []
        confidence = 0

        bos = _n(struct, "bos_count", 0)
        choch = _n(struct, "choch_count", 0)
        if isinstance(bos, (int, float)) and isinstance(choch, (int, float)) and bos > 0 and choch > 0:
            confidence += 30
            factors.append("bos_then_choch")

        if isinstance(bos, (int, float)) and bos > 0:
            confidence += 10

        mtf_align = _s(mtf, "alignment_level", "")
        if mtf_align in ("CONFLICT", "WEAK"):
            confidence += 15
            factors.append("weak_mtf_alignment")

        liq = _n(struct, "liquidity_sweeps", 0)
        if isinstance(liq, (int, float)) and liq > 0:
            confidence += 15
            factors.append("liquidity_sweep")

        return (min(100, confidence), factors)

    # ── Mean Reversion ──

    @staticmethod
    def _detect_mean_reversion(ctx: dict | None, ind: dict | None) -> tuple[int, list[str]]:
        """RSI>70/<30, price far from VWAP/EMA, overextended."""
        factors: list[str] = []
        confidence = 0

        rsi = _n(ind, "rsi_14")
        if rsi:
            if rsi > 70:
                confidence += 30
                factors.append(f"rsi_{rsi:.0f}_overbought")
            elif rsi < 30:
                confidence += 30
                factors.append(f"rsi_{rsi:.0f}_oversold")
            elif rsi > 65 or rsi < 35:
                confidence += 15

        close = _n(ind, "candle_close")
        vwap = _n(ind, "vwap")
        if close and vwap and vwap > 0:
            vwap_diff = abs(close - vwap) / vwap * 100
            if vwap_diff > 2.0:
                confidence += 20
                factors.append(f"far_from_vwap_{vwap_diff:.1f}%")
            elif vwap_diff > 1.5:
                confidence += 10

        ema20 = _n(ind, "ema_20")
        if close and ema20 and ema20 > 0:
            ema_diff = abs(close - ema20) / ema20 * 100
            if ema_diff > 2.0:
                confidence += 15
                factors.append("far_from_ema20")

        return (min(100, confidence), factors)

    # ── News Driven ──

    @staticmethod
    def _detect_news_driven(ctx: dict | None, ind: dict | None) -> tuple[int, list[str]]:
        """Sudden volume spike, gap open, no technical reason."""
        factors: list[str] = []
        confidence = 0

        vol = _n(ind, "candle_volume") or _n(ind, "volume", 0)
        avg_vol = _n(ind, "average_volume", 0)
        if vol and avg_vol and avg_vol > 0:
            ratio = vol / avg_vol
            if ratio > 3.0:
                confidence += 35
                factors.append(f"volume_spike_{ratio:.1f}x")
            elif ratio > 2.0:
                confidence += 20

        close = _n(ind, "candle_close")
        vwap = _n(ind, "vwap")
        if close and vwap and vwap > 0:
            gap = abs(close - vwap) / vwap * 100
            if gap > 3.0:
                confidence += 20
                factors.append(f"wide_spread_{gap:.1f}%")

        volatility = _s(ctx, "volatility", "")
        if volatility.upper() == "HIGH":
            confidence += 10

        return (min(100, confidence), factors)

    # ── Session sub-detectors ──

    @staticmethod
    def _detect_opening_auction(ctx: dict | None) -> tuple[int, list[str]]:
        """First 30-60 minutes of session."""
        session = _s(ctx, "session", "")
        if "open" in session.lower():
            return (75, ["opening_session"])
        return (0, [])

    @staticmethod
    def _detect_closing_session(ctx: dict | None) -> tuple[int, list[str]]:
        """Last 30-60 minutes of session."""
        session = _s(ctx, "session", "")
        if "closing" in session.lower() or "close" in session.lower():
            return (70, ["closing_session"])
        return (0, [])

    # ── Illiquid Market ──

    @staticmethod
    def _detect_illiquid_market(ctx: dict | None, ind: dict | None, struct: dict | None = None) -> tuple[int, list[str]]:
        """Volume < 50% avg, wide spread, no structure."""
        factors: list[str] = []
        confidence = 0

        vol = _n(ind, "candle_volume") or _n(ind, "volume", 0)
        avg_vol = _n(ind, "average_volume", 0)
        if vol and avg_vol and avg_vol > 0:
            ratio = vol / avg_vol
            if ratio < 0.3:
                confidence += 40
                factors.append(f"very_low_volume_{ratio:.0%}_of_avg")
            elif ratio < 0.5:
                confidence += 25
                factors.append("low_volume")

        valid = _b(struct, "valid_structure", True)
        if not valid:
            confidence += 15
            factors.append("no_structure")

        bos = _n(struct, "bos_count", 0)
        if isinstance(bos, (int, float)) and bos == 0:
            confidence += 10
            factors.append("no_structural_moves")

        return (min(100, confidence), factors)


# ── Type-safe helpers ──

def _s(d: dict | None, key: str, default: str = "") -> str:
    if not d:
        return default
    v = d.get(key)
    return str(v) if v is not None else default


def _n(d: dict | None, key: str, default: float | None = None) -> float | None:
    if not d:
        return default
    v = d.get(key)
    return float(v) if v is not None and isinstance(v, (int, float)) else default


def _b(d: dict | None, key: str, default: bool = True) -> bool:
    if not d:
        return default
    v = d.get(key)
    return bool(v) if v is not None else default

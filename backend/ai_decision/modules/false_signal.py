"""
False Signal Detection — detects and rejects known false signal patterns.

7 detectors:
1. Low Volume Breakout
2. Fake Breakout
3. Liquidity Grab
4. News Spike
5. Opening Noise
6. Range Trap
7. Exhaustion Move
"""

from __future__ import annotations

from typing import Any


class FalseSignalDetector:
    """Detects false signal patterns in market data."""

    @staticmethod
    def detect(
        context_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
        structure_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Run all false signal detectors and return combined result."""
        detections: list[dict[str, Any]] = []

        d1 = FalseSignalDetector._detect_low_volume_breakout(indicator_snap, sr_snap)
        detections.append(d1)

        d2 = FalseSignalDetector._detect_fake_breakout(sr_snap, indicator_snap)
        detections.append(d2)

        d3 = FalseSignalDetector._detect_liquidity_grab(structure_snap)
        detections.append(d3)

        d4 = FalseSignalDetector._detect_news_spike(indicator_snap)
        detections.append(d4)

        d5 = FalseSignalDetector._detect_opening_noise(context_snap)
        detections.append(d5)

        d6 = FalseSignalDetector._detect_range_trap(indicator_snap, sr_snap)
        detections.append(d6)

        d7 = FalseSignalDetector._detect_exhaustion_move(indicator_snap, context_snap)
        detections.append(d7)

        any_detected = any(d["detected"] for d in detections)
        reject_reasons = [d["reason"] for d in detections if d["detected"]]

        return {
            "is_false_signal": any_detected,
            "detections": detections,
            "reject_reasons": reject_reasons,
        }

    @staticmethod
    def _detect_low_volume_breakout(
        indicator_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Breakout signal with volume < 50% of average volume."""
        if not indicator_snap or not sr_snap:
            return {"type": "low_volume_breakout", "detected": False, "confidence": 0, "reason": "Insufficient data"}
        volume = indicator_snap.get("candle_volume") or indicator_snap.get("volume", 0)
        avg_volume = indicator_snap.get("average_volume", 0)
        breakout_state = sr_snap.get("breakout_state", "none")
        if isinstance(volume, (int, float)) and isinstance(avg_volume, (int, float)) and avg_volume > 0:
            vol_ratio = volume / avg_volume
            if vol_ratio < 0.5 and breakout_state in ("breakout", "breakdown"):
                return {
                    "type": "low_volume_breakout",
                    "detected": True,
                    "confidence": min(100, int((1 - vol_ratio) * 100)),
                    "reason": f"Breakout with volume {vol_ratio:.0%} of average — low conviction breakout",
                }
        return {"type": "low_volume_breakout", "detected": False, "confidence": 0, "reason": "No low volume breakout"}

    @staticmethod
    def _detect_fake_breakout(
        sr_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Price breaks S/R but immediately retraces (wick beyond, close inside)."""
        if not sr_snap:
            return {"type": "fake_breakout", "detected": False, "confidence": 0, "reason": "No S/R data"}
        breakout_state = sr_snap.get("breakout_state", "none")
        if breakout_state in ("breakout", "breakdown"):
            close = (indicator_snap or {}).get("candle_close", 0)
            nearest_r = sr_snap.get("nearest_resistance", 0)
            nearest_s = sr_snap.get("nearest_support", 0)
            if breakout_state == "breakout" and close and nearest_r:
                close_pct = abs(close - nearest_r) / max(abs(nearest_r), 1)
                if close_pct < 0.002:  # Less than 0.2% above resistance
                    return {"type": "fake_breakout", "detected": True, "confidence": 75, "reason": f"Price closed at {close:.1f} near resistance {nearest_r:.1f} — possible fakeout"}
            if breakout_state == "breakdown" and close and nearest_s:
                close_pct = abs(close - nearest_s) / max(abs(nearest_s), 1)
                if close_pct < 0.002:
                    return {"type": "fake_breakout", "detected": True, "confidence": 75, "reason": f"Price closed at {close:.1f} near support {nearest_s:.1f} — possible fakeout"}
        return {"type": "fake_breakout", "detected": False, "confidence": 0, "reason": "No fake breakout detected"}

    @staticmethod
    def _detect_liquidity_grab(structure_snap: dict[str, Any] | None) -> dict[str, Any]:
        """Price sweeps swing high/low then reverses."""
        if not structure_snap:
            return {"type": "liquidity_grab", "detected": False, "confidence": 0, "reason": "No structure data"}
        sweeps = structure_snap.get("liquidity_sweeps", 0)
        if isinstance(sweeps, (int, float)) and sweeps > 0:
            return {
                "type": "liquidity_grab",
                "detected": True,
                "confidence": min(100, int(sweeps) * 25),
                "reason": f"{int(sweeps)} liquidity sweep(s) detected — possible grab before reversal",
            }
        return {"type": "liquidity_grab", "detected": False, "confidence": 0, "reason": "No liquidity sweeps"}

    @staticmethod
    def _detect_news_spike(indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        """Sudden volume spike > 300% without technical basis."""
        if not indicator_snap:
            return {"type": "news_spike", "detected": False, "confidence": 0, "reason": "No indicator data"}
        volume = indicator_snap.get("candle_volume") or indicator_snap.get("volume", 0)
        avg_volume = indicator_snap.get("average_volume", 0)
        if isinstance(volume, (int, float)) and isinstance(avg_volume, (int, float)) and avg_volume > 0:
            ratio = volume / avg_volume
            if ratio > 3.0:
                return {
                    "type": "news_spike",
                    "detected": True,
                    "confidence": min(100, int((ratio - 2) * 20)),
                    "reason": f"Volume spike {ratio:.1f}x average — possible news-driven move",
                }
        return {"type": "news_spike", "detected": False, "confidence": 0, "reason": "No news spike detected"}

    @staticmethod
    def _detect_opening_noise(context_snap: dict[str, Any] | None) -> dict[str, Any]:
        """First 15-30 minutes of session — low liquidity, high spreads."""
        if not context_snap:
            return {"type": "opening_noise", "detected": False, "confidence": 0, "reason": "No context data"}
        session = context_snap.get("session", "")
        if isinstance(session, str) and "open" in session.lower():
            return {
                "type": "opening_noise",
                "detected": True,
                "confidence": 60,
                "reason": f"Opening session ({session}) — reduced liquidity, wait for confirmation",
            }
        return {"type": "opening_noise", "detected": False, "confidence": 0, "reason": "Not during opening"}

    @staticmethod
    def _detect_range_trap(
        indicator_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Price in tight range (< 0.5 ATR over last candles) then false breakout."""
        if not indicator_snap or not sr_snap:
            return {"type": "range_trap", "detected": False, "confidence": 0, "reason": "Insufficient data"}
        atr = indicator_snap.get("atr_14", 0)
        close = indicator_snap.get("candle_close", 0)
        breakout_state = sr_snap.get("breakout_state", "none")
        if isinstance(atr, (int, float)) and isinstance(close, (int, float)) and close > 0:
            atr_pct = atr / close * 100
            if atr_pct < 0.5 and breakout_state in ("breakout", "breakdown"):
                return {
                    "type": "range_trap",
                    "detected": True,
                    "confidence": 70,
                    "reason": f"Tight range (ATR {atr_pct:.1f}%) with breakout — possible range trap",
                }
        return {"type": "range_trap", "detected": False, "confidence": 0, "reason": "No range trap detected"}

    @staticmethod
    def _detect_exhaustion_move(
        indicator_snap: dict[str, Any] | None,
        context_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Extended move (+3 ATR in same direction) suggesting trend end."""
        if not indicator_snap or not context_snap:
            return {"type": "exhaustion_move", "detected": False, "confidence": 0, "reason": "Insufficient data"}
        atr = indicator_snap.get("atr_14", 0)
        close = indicator_snap.get("candle_close", 0)
        trend = str((context_snap.get("trend", "NEUTRAL") or "NEUTRAL")).upper()
        if isinstance(atr, (int, float)) and isinstance(close, (int, float)) and atr > 0 and trend in ("BULLISH", "BEARISH"):
            move_count = close / atr  # Rough estimate of ATR multiple
            if move_count > 3:
                return {
                    "type": "exhaustion_move",
                    "detected": True,
                    "confidence": min(100, int((move_count - 2) * 20)),
                    "reason": f"Extended {trend} move ({move_count:.1f} ATR) — possible exhaustion",
                }
        return {"type": "exhaustion_move", "detected": False, "confidence": 0, "reason": "No exhaustion detected"}

"""
Signal Validator — validates individual signal dimensions.

Each signal dimension gets PASS / WARNING / BLOCK with reasoning.
"""

from __future__ import annotations

from typing import Any


class SignalValidator:
    """Validates AI signal across 10 dimensions."""

    @staticmethod
    def validate(
        decision_snap: dict[str, Any] | None,
        context_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
        structure_snap: dict[str, Any] | None,
        pattern_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Run all 10 signal validations and return combined result."""
        validations: list[dict[str, Any]] = []
        direction = (decision_snap or {}).get("direction", "WAIT")

        v1 = SignalValidator._validate_trend(direction, context_snap, structure_snap)
        validations.append(v1)

        v2 = SignalValidator._validate_ema_alignment(direction, indicator_snap)
        validations.append(v2)

        v3 = SignalValidator._validate_vwap(direction, indicator_snap)
        validations.append(v3)

        v4 = SignalValidator._validate_structure(direction, structure_snap)
        validations.append(v4)

        v5 = SignalValidator._validate_rsi(direction, indicator_snap)
        validations.append(v5)

        v6 = SignalValidator._validate_macd(direction, indicator_snap)
        validations.append(v6)

        v7 = SignalValidator._validate_volume(indicator_snap)
        validations.append(v7)

        v8 = SignalValidator._validate_patterns(direction, pattern_snap)
        validations.append(v8)

        v9 = SignalValidator._validate_sr_proximity(direction, sr_snap, indicator_snap)
        validations.append(v9)

        v10 = SignalValidator._validate_volatility(indicator_snap)
        validations.append(v10)

        pass_count = sum(1 for v in validations if v["status"] == "PASS")
        warning_count = sum(1 for v in validations if v["status"] == "WARNING")
        block_count = sum(1 for v in validations if v["status"] == "BLOCK")

        if block_count > 0:
            overall = "BLOCK"
        elif warning_count > 2:
            overall = "WARNING"
        elif warning_count > 0:
            overall = "WARNING"
        else:
            overall = "PASS"

        return {
            "validations": validations,
            "overall_status": overall,
            "pass_count": pass_count,
            "warning_count": warning_count,
            "block_count": block_count,
        }

    # ── Individual validators ──

    @staticmethod
    def _validate_trend(
        direction: str, context_snap: dict[str, Any] | None, structure_snap: dict[str, Any] | None
    ) -> dict[str, Any]:
        if not context_snap and not structure_snap:
            return {"signal": "trend", "status": "WARNING", "reason": "No trend data available", "severity": "low"}
        trend = structure_snap.get("trend") if structure_snap else context_snap.get("trend", "NEUTRAL")
        if not isinstance(trend, str):
            trend = "NEUTRAL"
        trend = trend.upper()
        if direction == "BUY" and trend in ("UPTREND", "BULLISH"):
            return {"signal": "trend", "status": "PASS", "reason": f"Trend {trend} aligns with BUY", "severity": "none"}
        elif direction == "SELL" and trend in ("DOWNTREND", "BEARISH"):
            return {"signal": "trend", "status": "PASS", "reason": f"Trend {trend} aligns with SELL", "severity": "none"}
        elif trend in ("RANGING", "NEUTRAL", "SIDEWAYS"):
            return {"signal": "trend", "status": "WARNING", "reason": f"Trend is {trend} — no clear direction", "severity": "medium"}
        else:
            return {"signal": "trend", "status": "WARNING", "reason": f"Trend {trend} conflicts with {direction}", "severity": "high"}

    @staticmethod
    def _validate_ema_alignment(direction: str, indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"signal": "ema_alignment", "status": "WARNING", "reason": "No indicator data", "severity": "low"}
        ema9 = indicator_snap.get("ema_9")
        ema20 = indicator_snap.get("ema_20")
        ema50 = indicator_snap.get("ema_50")
        if ema9 is None or ema20 is None:
            return {"signal": "ema_alignment", "status": "WARNING", "reason": "EMA data incomplete", "severity": "low"}
        bullish = ema9 > ema20 > (ema50 if ema50 else ema20 - 1)
        bearish = ema9 < ema20 < (ema50 if ema50 else ema20 + 1)
        if direction == "BUY" and bullish:
            return {"signal": "ema_alignment", "status": "PASS", "reason": "EMA bullish alignment (9>20>50)", "severity": "none"}
        elif direction == "SELL" and bearish:
            return {"signal": "ema_alignment", "status": "PASS", "reason": "EMA bearish alignment (9<20<50)", "severity": "none"}
        elif bullish or bearish:
            return {"signal": "ema_alignment", "status": "WARNING", "reason": f"EMA aligns opposite to {direction}", "severity": "medium"}
        else:
            return {"signal": "ema_alignment", "status": "WARNING", "reason": "EMA no clear alignment", "severity": "low"}

    @staticmethod
    def _validate_vwap(direction: str, indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"signal": "vwap", "status": "WARNING", "reason": "No VWAP data", "severity": "low"}
        close = indicator_snap.get("candle_close")
        vwap = indicator_snap.get("vwap")
        if close is None or vwap is None or vwap == 0:
            return {"signal": "vwap", "status": "WARNING", "reason": "VWAP data incomplete", "severity": "low"}
        above = close > vwap
        if direction == "BUY" and above:
            return {"signal": "vwap", "status": "PASS", "reason": "Price above VWAP (bullish)", "severity": "none"}
        elif direction == "SELL" and not above:
            return {"signal": "vwap", "status": "PASS", "reason": "Price below VWAP (bearish)", "severity": "none"}
        else:
            return {"signal": "vwap", "status": "WARNING", "reason": f"Price {'above' if above else 'below'} VWAP conflicts with {direction}", "severity": "medium"}

    @staticmethod
    def _validate_structure(direction: str, structure_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not structure_snap:
            return {"signal": "structure", "status": "WARNING", "reason": "No structure data", "severity": "low"}
        valid = structure_snap.get("valid_structure", False)
        if not valid:
            return {"signal": "structure", "status": "WARNING", "reason": "Market structure not confirmed", "severity": "medium"}
        return {"signal": "structure", "status": "PASS", "reason": "Valid market structure", "severity": "none"}

    @staticmethod
    def _validate_rsi(direction: str, indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"signal": "rsi", "status": "WARNING", "reason": "No RSI data", "severity": "low"}
        rsi = indicator_snap.get("rsi_14")
        if rsi is None:
            return {"signal": "rsi", "status": "WARNING", "reason": "RSI not available", "severity": "low"}
        if rsi > 85:
            return {"signal": "rsi", "status": "BLOCK", "reason": f"RSI {rsi:.0f} — extreme overbought", "severity": "high"}
        if rsi > 70:
            return {"signal": "rsi", "status": "WARNING", "reason": f"RSI {rsi:.0f} — overbought", "severity": "medium"}
        if rsi < 15:
            return {"signal": "rsi", "status": "BLOCK", "reason": f"RSI {rsi:.0f} — extreme oversold", "severity": "high"}
        if rsi < 30:
            return {"signal": "rsi", "status": "WARNING", "reason": f"RSI {rsi:.0f} — oversold", "severity": "medium"}
        return {"signal": "rsi", "status": "PASS", "reason": f"RSI {rsi:.0f} — normal range", "severity": "none"}

    @staticmethod
    def _validate_macd(direction: str, indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"signal": "macd", "status": "WARNING", "reason": "No MACD data", "severity": "low"}
        hist = indicator_snap.get("macd_histogram")
        if hist is None:
            return {"signal": "macd", "status": "WARNING", "reason": "MACD not available", "severity": "low"}
        bullish = hist > 0
        if (direction == "BUY" and bullish) or (direction == "SELL" and not bullish):
            return {"signal": "macd", "status": "PASS", "reason": f"MACD histogram {'positive' if bullish else 'negative'} aligns", "severity": "none"}
        else:
            return {"signal": "macd", "status": "WARNING", "reason": f"MACD histogram {'positive' if bullish else 'negative'} conflicts with {direction}", "severity": "medium"}

    @staticmethod
    def _validate_volume(indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"signal": "volume", "status": "WARNING", "reason": "No volume data", "severity": "low"}
        volume = indicator_snap.get("candle_volume") or indicator_snap.get("volume")
        avg_volume = indicator_snap.get("average_volume")
        if volume is None:
            return {"signal": "volume", "status": "WARNING", "reason": "Volume not available", "severity": "low"}
        if avg_volume and volume < avg_volume * 0.5:
            return {"signal": "volume", "status": "WARNING", "reason": f"Volume {volume:.0f} is <50% of average", "severity": "medium"}
        if avg_volume and volume > avg_volume * 1.5:
            return {"signal": "volume", "status": "PASS", "reason": f"Volume {volume:.0f} is above average", "severity": "none"}
        return {"signal": "volume", "status": "PASS", "reason": "Volume normal", "severity": "none"}

    @staticmethod
    def _validate_patterns(direction: str, pattern_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not pattern_snap:
            return {"signal": "patterns", "status": "WARNING", "reason": "No pattern data", "severity": "low"}
        pat_dir = pattern_snap.get("pattern_direction", "NEUTRAL")
        if not isinstance(pat_dir, str):
            pat_dir = "NEUTRAL"
        pat_dir = pat_dir.upper()
        if direction == "BUY" and pat_dir in ("BULLISH", "BUY"):
            return {"signal": "patterns", "status": "PASS", "reason": f"Pattern direction {pat_dir} aligns with BUY", "severity": "none"}
        elif direction == "SELL" and pat_dir in ("BEARISH", "SELL"):
            return {"signal": "patterns", "status": "PASS", "reason": f"Pattern direction {pat_dir} aligns with SELL", "severity": "none"}
        elif pat_dir in ("NEUTRAL", "NONE"):
            return {"signal": "patterns", "status": "WARNING", "reason": "No clear pattern direction", "severity": "low"}
        else:
            return {"signal": "patterns", "status": "WARNING", "reason": f"Pattern {pat_dir} conflicts with {direction}", "severity": "medium"}

    @staticmethod
    def _validate_sr_proximity(
        direction: str, sr_snap: dict[str, Any] | None, indicator_snap: dict[str, Any] | None
    ) -> dict[str, Any]:
        if not sr_snap:
            return {"signal": "sr_proximity", "status": "WARNING", "reason": "No S/R data", "severity": "low"}
        close = (indicator_snap or {}).get("candle_close")
        nearest_s = sr_snap.get("nearest_support")
        nearest_r = sr_snap.get("nearest_resistance")
        if close is None or nearest_s is None or nearest_r is None:
            return {"signal": "sr_proximity", "status": "WARNING", "reason": "S/R proximity data incomplete", "severity": "low"}
        range_size = nearest_r - nearest_s
        if range_size <= 0:
            return {"signal": "sr_proximity", "status": "WARNING", "reason": "Invalid S/R range", "severity": "low"}
        pos = (close - nearest_s) / range_size
        if 0.2 <= pos <= 0.8:
            return {"signal": "sr_proximity", "status": "PASS", "reason": "Price is mid-range with room to move", "severity": "none"}
        if direction == "BUY" and pos < 0.2:
            return {"signal": "sr_proximity", "status": "WARNING", "reason": "Price near support — risk of breakdown", "severity": "medium"}
        if direction == "SELL" and pos > 0.8:
            return {"signal": "sr_proximity", "status": "WARNING", "reason": "Price near resistance — risk of breakout", "severity": "medium"}
        return {"signal": "sr_proximity", "status": "WARNING", "reason": "Price near S/R boundary", "severity": "low"}

    @staticmethod
    def _validate_volatility(indicator_snap: dict[str, Any] | None) -> dict[str, Any]:
        if not indicator_snap:
            return {"signal": "volatility", "status": "WARNING", "reason": "No volatility data", "severity": "low"}
        atr = indicator_snap.get("atr_14")
        close = indicator_snap.get("candle_close")
        if atr is None or close is None or close == 0:
            return {"signal": "volatility", "status": "WARNING", "reason": "ATR data incomplete", "severity": "low"}
        atr_pct = (atr / close) * 100
        if atr_pct > 5:
            return {"signal": "volatility", "status": "WARNING", "reason": f"ATR {atr_pct:.1f}% — high volatility", "severity": "medium"}
        if atr_pct < 0.3:
            return {"signal": "volatility", "status": "WARNING", "reason": f"ATR {atr_pct:.1f}% — very low volatility", "severity": "low"}
        return {"signal": "volatility", "status": "PASS", "reason": f"ATR {atr_pct:.1f}% — normal volatility", "severity": "none"}

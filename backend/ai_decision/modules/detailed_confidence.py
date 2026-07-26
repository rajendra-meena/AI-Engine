"""
Detailed Confidence Engine — per-factor breakdown with 10 individual scores.

Each factor: 0-100, overall = weighted average.
"""

from __future__ import annotations

from typing import Any


class DetailedConfidenceEngine:
    """Computes detailed per-factor confidence breakdown."""

    FACTOR_WEIGHTS = {
        "trend": 15,
        "market_structure": 15,
        "momentum": 12,
        "volume": 10,
        "liquidity": 10,
        "volatility": 8,
        "htf_alignment": 12,
        "pattern_strength": 8,
        "sr_distance": 5,
        "risk_reward": 5,
    }

    @staticmethod
    def evaluate(
        context_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
        structure_snap: dict[str, Any] | None,
        pattern_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
        decision_snap: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compute 10-factor confidence breakdown and overall confidence."""
        factors: list[dict[str, Any]] = []

        # 1. Trend Confidence
        trend_score = DetailedConfidenceEngine._factor_trend(context_snap, structure_snap)
        factors.append({"name": "Trend", "score": trend_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["trend"],
                        "detail": DetailedConfidenceEngine._trend_detail(context_snap, structure_snap)})

        # 2. Market Structure Confidence
        struct_score = DetailedConfidenceEngine._factor_structure(structure_snap)
        factors.append({"name": "Market Structure", "score": struct_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["market_structure"],
                        "detail": DetailedConfidenceEngine._structure_detail(structure_snap)})

        # 3. Momentum Confidence
        momo_score = DetailedConfidenceEngine._factor_momentum(indicator_snap, context_snap)
        factors.append({"name": "Momentum", "score": momo_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["momentum"],
                        "detail": DetailedConfidenceEngine._momentum_detail(indicator_snap, context_snap)})

        # 4. Volume Confidence
        vol_score = DetailedConfidenceEngine._factor_volume(indicator_snap)
        factors.append({"name": "Volume", "score": vol_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["volume"],
                        "detail": DetailedConfidenceEngine._volume_detail(indicator_snap)})

        # 5. Liquidity Confidence
        liq_score = DetailedConfidenceEngine._factor_liquidity(context_snap, structure_snap)
        factors.append({"name": "Liquidity", "score": liq_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["liquidity"],
                        "detail": DetailedConfidenceEngine._liquidity_detail(context_snap, structure_snap)})

        # 6. Volatility Confidence
        vola_score = DetailedConfidenceEngine._factor_volatility(indicator_snap)
        factors.append({"name": "Volatility", "score": vola_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["volatility"],
                        "detail": DetailedConfidenceEngine._volatility_detail(indicator_snap)})

        # 7. HTF Alignment Confidence
        htf_score = DetailedConfidenceEngine._factor_htf_alignment(mtf_snap)
        factors.append({"name": "Higher TF Alignment", "score": htf_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["htf_alignment"],
                        "detail": DetailedConfidenceEngine._htf_detail(mtf_snap)})

        # 8. Pattern Strength Confidence
        pat_score = DetailedConfidenceEngine._factor_patterns(pattern_snap)
        factors.append({"name": "Pattern Strength", "score": pat_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["pattern_strength"],
                        "detail": DetailedConfidenceEngine._pattern_detail(pattern_snap)})

        # 9. S/R Distance Confidence
        sr_score = DetailedConfidenceEngine._factor_sr_distance(sr_snap, indicator_snap)
        factors.append({"name": "S/R Distance", "score": sr_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["sr_distance"],
                        "detail": DetailedConfidenceEngine._sr_detail(sr_snap, indicator_snap)})

        # 10. Risk Reward Confidence
        rr_score = DetailedConfidenceEngine._factor_risk_reward(decision_snap)
        factors.append({"name": "Risk Reward", "score": rr_score, "weight": DetailedConfidenceEngine.FACTOR_WEIGHTS["risk_reward"],
                        "detail": DetailedConfidenceEngine._rr_detail(decision_snap)})

        # Weighted overall
        total_weight = sum(f["weight"] for f in factors)
        weighted = sum(f["score"] * f["weight"] for f in factors)
        overall = round(weighted / total_weight) if total_weight > 0 else 0
        overall = max(0, min(100, overall))

        grade = DetailedConfidenceEngine._to_grade(overall)
        reasoning = DetailedConfidenceEngine._build_reasoning(factors, overall)

        return {
            "overall_confidence": overall,
            "grade": grade,
            "factor_breakdown": sorted(factors, key=lambda f: f["weight"], reverse=True),
            "reasoning": reasoning,
        }

    @staticmethod
    def _factor_trend(context_snap: dict[str, Any] | None, structure_snap: dict[str, Any] | None) -> int:
        trend = "NEUTRAL"
        strength = "WEAK"
        if structure_snap:
            trend = str(structure_snap.get("trend", "NEUTRAL")).upper()
            strength = str(structure_snap.get("trend_strength", "WEAK")).upper()
        elif context_snap:
            trend = str(context_snap.get("trend", "NEUTRAL")).upper()
            strength = str(context_snap.get("trend_strength", "WEAK")).upper()
        if trend in ("UPTREND", "BULLISH"):
            return 90 if strength == "STRONG" else 70
        elif trend in ("DOWNTREND", "BEARISH"):
            return 85 if strength == "STRONG" else 65
        return 45

    @staticmethod
    def _trend_detail(context_snap: dict[str, Any] | None, structure_snap: dict[str, Any] | None) -> str:
        trend = "N/A"
        strength = "N/A"
        if structure_snap:
            trend = structure_snap.get("trend", "N/A")
            strength = structure_snap.get("trend_strength", "N/A")
        elif context_snap:
            trend = context_snap.get("trend", "N/A")
            strength = context_snap.get("trend_strength", "N/A")
        return f"{trend} ({strength})"

    @staticmethod
    def _factor_structure(structure_snap: dict[str, Any] | None) -> int:
        if not structure_snap:
            return 40
        valid = structure_snap.get("valid_structure", False)
        bos = structure_snap.get("bos_count", 0) or 0
        score = 40
        if valid:
            score += 30
        if isinstance(bos, (int, float)) and bos > 0:
            score += min(20, int(bos) * 5)
        return min(100, score)

    @staticmethod
    def _structure_detail(structure_snap: dict[str, Any] | None) -> str:
        if not structure_snap:
            return "No structure data"
        valid = structure_snap.get("valid_structure", False)
        return "Valid structure" if valid else "Structure not confirmed"

    @staticmethod
    def _factor_momentum(indicator_snap: dict[str, Any] | None, context_snap: dict[str, Any] | None) -> int:
        score = 50
        if indicator_snap:
            rsi = indicator_snap.get("rsi_14")
            if isinstance(rsi, (int, float)):
                if 40 <= rsi <= 60:
                    score += 20
                elif rsi > 70 or rsi < 30:
                    score -= 10
            macd = indicator_snap.get("macd_histogram")
            if isinstance(macd, (int, float)):
                score += 10 if macd > 0 else 5
        if context_snap:
            momo = context_snap.get("momentum", "")
            if isinstance(momo, str):
                if momo.upper() == "STRONG":
                    score += 15
                elif momo.upper() == "WEAK":
                    score -= 10
        return max(0, min(100, score))

    @staticmethod
    def _momentum_detail(indicator_snap: dict[str, Any] | None, context_snap: dict[str, Any] | None) -> str:
        parts = []
        if indicator_snap:
            rsi = indicator_snap.get("rsi_14")
            if rsi is not None:
                parts.append(f"RSI: {rsi:.0f}")
        if context_snap:
            momo = context_snap.get("momentum", "")
            if momo:
                parts.append(f"Momentum: {momo}")
        return ", ".join(parts) if parts else "Neutral momentum"

    @staticmethod
    def _factor_volume(indicator_snap: dict[str, Any] | None) -> int:
        if not indicator_snap:
            return 50
        volume = indicator_snap.get("candle_volume") or indicator_snap.get("volume", 0)
        avg_vol = indicator_snap.get("average_volume", 0)
        if isinstance(volume, (int, float)) and isinstance(avg_vol, (int, float)) and avg_vol > 0:
            ratio = volume / avg_vol
            if ratio > 1.5:
                return 90
            elif ratio > 1.0:
                return 75
            elif ratio > 0.7:
                return 55
            else:
                return 30
        return 50

    @staticmethod
    def _volume_detail(indicator_snap: dict[str, Any] | None) -> str:
        if not indicator_snap:
            return "No volume data"
        vol = indicator_snap.get("candle_volume") or indicator_snap.get("volume")
        avg = indicator_snap.get("average_volume")
        if vol and avg and avg > 0:
            return f"Vol: {vol:.0f} ({vol/avg:.0%} of avg)"
        return f"Vol: {vol:.0f}" if vol else "N/A"

    @staticmethod
    def _factor_liquidity(context_snap: dict[str, Any] | None, structure_snap: dict[str, Any] | None) -> int:
        score = 70
        if context_snap:
            sweeps = context_snap.get("liquidity_sweeps", 0)
            if isinstance(sweeps, (int, float)) and sweeps > 0:
                score -= int(sweeps) * 10
        if structure_snap:
            phase = str(structure_snap.get("market_phase", "")).lower()
            if phase in ("accumulation", "distribution"):
                score += 10
        return max(0, min(100, score))

    @staticmethod
    def _liquidity_detail(context_snap: dict[str, Any] | None, structure_snap: dict[str, Any] | None) -> str:
        parts = []
        if context_snap:
            swp = context_snap.get("liquidity_sweeps", 0)
            if isinstance(swp, (int, float)) and swp > 0:
                parts.append(f"Sweeps: {swp}")
        if structure_snap:
            phase = structure_snap.get("market_phase", "")
            if phase:
                parts.append(f"Phase: {phase}")
        return ", ".join(parts) if parts else "Normal liquidity"

    @staticmethod
    def _factor_volatility(indicator_snap: dict[str, Any] | None) -> int:
        if not indicator_snap:
            return 60
        atr = indicator_snap.get("atr_14", 0)
        close = indicator_snap.get("candle_close", 0)
        if isinstance(atr, (int, float)) and isinstance(close, (int, float)) and close > 0 and atr > 0:
            pct = atr / close * 100
            if 0.5 <= pct <= 2.0:
                return 85
            elif pct < 0.5:
                return 60
            elif pct <= 3.0:
                return 50
            else:
                return 30
        return 60

    @staticmethod
    def _volatility_detail(indicator_snap: dict[str, Any] | None) -> str:
        if not indicator_snap:
            return "No volatility data"
        atr = indicator_snap.get("atr_14")
        close = indicator_snap.get("candle_close")
        if atr and close and close > 0:
            return f"ATR: {atr:.1f} ({(atr/close)*100:.1f}%)"
        return f"ATR: {atr}" if atr else "N/A"

    @staticmethod
    def _factor_htf_alignment(mtf_snap: dict[str, Any] | None) -> int:
        if not mtf_snap:
            return 50
        align = mtf_snap.get("alignment_level", "MIXED")
        score = mtf_snap.get("alignment_score", 0)
        if isinstance(score, (int, float)):
            if align in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT"):
                return min(100, 70 + abs(score) // 5)
            elif align == "PARTIAL_ALIGNMENT":
                return 55
            elif align == "CONFLICT":
                return 25
        return 50

    @staticmethod
    def _htf_detail(mtf_snap: dict[str, Any] | None) -> str:
        if not mtf_snap:
            return "No MTF data"
        align = mtf_snap.get("alignment_level", "N/A")
        score = mtf_snap.get("alignment_score", 0)
        return f"{align} ({score})"

    @staticmethod
    def _factor_patterns(pattern_snap: dict[str, Any] | None) -> int:
        if not pattern_snap:
            return 40
        count = pattern_snap.get("pattern_count") or pattern_snap.get("total_count", 0)
        if isinstance(count, (list, dict)):
            count = 0
        score = 40
        if pattern_snap.get("strongest_pattern"):
            score += 20
        if isinstance(count, (int, float)) and count >= 3:
            score += 20
        elif isinstance(count, (int, float)) and count >= 1:
            score += 10
        return min(100, score)

    @staticmethod
    def _pattern_detail(pattern_snap: dict[str, Any] | None) -> str:
        if not pattern_snap:
            return "No patterns"
        pat = pattern_snap.get("strongest_pattern", "none")
        count = pattern_snap.get("pattern_count") or pattern_snap.get("total_count", 0)
        return f"{count} patterns, {pat}"

    @staticmethod
    def _factor_sr_distance(sr_snap: dict[str, Any] | None, indicator_snap: dict[str, Any] | None) -> int:
        if not sr_snap:
            return 50
        close = (indicator_snap or {}).get("candle_close")
        nearest_r = sr_snap.get("nearest_resistance")
        nearest_s = sr_snap.get("nearest_support")
        if close and nearest_r and nearest_s and nearest_r > nearest_s:
            mid = (nearest_r + nearest_s) / 2
            dist = abs(close - mid) / (nearest_r - nearest_s)
            if dist < 0.3:
                return 80  # Close to middle = room to move
            elif dist < 0.5:
                return 60
            else:
                return 40  # Near boundary
        return 50

    @staticmethod
    def _sr_detail(sr_snap: dict[str, Any] | None, indicator_snap: dict[str, Any] | None) -> str:
        if not sr_snap:
            return "No S/R data"
        s = sr_snap.get("nearest_support")
        r = sr_snap.get("nearest_resistance")
        return f"S: {s}, R: {r}" if s and r else "S/R available"

    @staticmethod
    def _factor_risk_reward(decision_snap: dict[str, Any] | None) -> int:
        if not decision_snap:
            return 50
        tp = decision_snap.get("trade_plan", {})
        entry = tp.get("entry_zone")
        sl = tp.get("sl_zone")
        targets = tp.get("target_zones", [])
        target = targets[0] if isinstance(targets, list) and targets else tp.get("target_price")
        if isinstance(entry, dict): entry = entry.get("price") or entry.get("value")
        if isinstance(sl, dict): sl = sl.get("price") or sl.get("value")
        if isinstance(target, dict): target = target.get("price") or target.get("value")
        if entry and sl and target:
            try:
                risk = abs(float(entry) - float(sl))
                reward = abs(float(target) - float(entry))
                if risk > 0:
                    rr = reward / risk
                    if rr >= 3: return 95
                    elif rr >= 2: return 80
                    elif rr >= 1.5: return 60
                    elif rr >= 1: return 40
                    else: return 20
            except (TypeError, ValueError, ZeroDivisionError):
                pass
        return 50

    @staticmethod
    def _rr_detail(decision_snap: dict[str, Any] | None) -> str:
        rr = DetailedConfidenceEngine._factor_risk_reward(decision_snap)
        if rr >= 80: return "Favorable R:R"
        elif rr >= 60: return "Adequate R:R"
        elif rr >= 40: return "Borderline R:R"
        else: return "Poor R:R"

    @staticmethod
    def _to_grade(confidence: int) -> str:
        if confidence >= 80: return "VERY_HIGH"
        elif confidence >= 60: return "HIGH"
        elif confidence >= 40: return "MODERATE"
        elif confidence >= 20: return "LOW"
        return "VERY_LOW"

    @staticmethod
    def _build_reasoning(factors: list[dict[str, Any]], overall: int) -> list[str]:
        reasons = [f"Overall confidence: {overall}/100"]
        top = sorted(factors, key=lambda f: f["score"], reverse=True)[:3]
        for f in top:
            reasons.append(f"{f['name']}: {f['score']}")
        low = [f for f in factors if f["score"] < 40]
        for f in low:
            reasons.append(f"Low {f['name']}: {f['score']}")
        return reasons[:6]

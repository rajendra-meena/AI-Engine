"""
Trade Quality Scorer — grades each proposed trade A+/A/B/C/D/REJECT.

Uses 5 weighted factors + MTF alignment bonus.
"""

from __future__ import annotations

from typing import Any


class TradeQualityScorer:
    """Evaluates trade quality independent of execution safety."""

    WEIGHTS = {
        "trend_alignment": 20,
        "risk_reward": 18,
        "pattern_strength": 17,
        "liquidity": 19,
        "execution_feasibility": 20,
    }

    MTF_BONUS_WEIGHT = 6

    @staticmethod
    def evaluate(
        decision_snap: dict[str, Any] | None,
        context_snap: dict[str, Any] | None,
        indicator_snap: dict[str, Any] | None,
        pattern_snap: dict[str, Any] | None,
        sr_snap: dict[str, Any] | None,
        mtf_snap: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Compute trade quality score and letter grade."""
        direction = (decision_snap or {}).get("direction", "WAIT")

        factors: list[dict[str, Any]] = []

        # 1. Trend Alignment (20%)
        trend_score = TradeQualityScorer._score_trend(direction, context_snap)
        factors.append({"name": "Trend Alignment", "score": trend_score, "weight": TradeQualityScorer.WEIGHTS["trend_alignment"], "detail": TradeQualityScorer._trend_detail(direction, context_snap)})

        # 2. Risk Reward (18%)
        rr_score = TradeQualityScorer._score_risk_reward(decision_snap, sr_snap)
        factors.append({"name": "Risk Reward", "score": rr_score, "weight": TradeQualityScorer.WEIGHTS["risk_reward"], "detail": TradeQualityScorer._rr_detail(decision_snap, sr_snap)})

        # 3. Pattern Strength (17%)
        pat_score = TradeQualityScorer._score_patterns(direction, pattern_snap)
        factors.append({"name": "Pattern Strength", "score": pat_score, "weight": TradeQualityScorer.WEIGHTS["pattern_strength"], "detail": TradeQualityScorer._pattern_detail(pattern_snap)})

        # 4. Liquidity (19%)
        liq_score = TradeQualityScorer._score_liquidity(context_snap, indicator_snap)
        factors.append({"name": "Liquidity", "score": liq_score, "weight": TradeQualityScorer.WEIGHTS["liquidity"], "detail": TradeQualityScorer._liquidity_detail(context_snap, indicator_snap)})

        # 5. Execution Feasibility (20%)
        exec_score = TradeQualityScorer._score_execution(indicator_snap, sr_snap)
        factors.append({"name": "Execution Feasibility", "score": exec_score, "weight": TradeQualityScorer.WEIGHTS["execution_feasibility"], "detail": TradeQualityScorer._execution_detail(indicator_snap)})

        # Weighted total (base)
        total_weight = sum(f["weight"] for f in factors)
        weighted = sum(f["score"] * f["weight"] for f in factors)
        total_score = weighted / total_weight if total_weight > 0 else 0

        # MTF Bonus (6%)
        mtf_score = 0
        if mtf_snap:
            align = mtf_snap.get("alignment_level", "MIXED")
            if align in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT"):
                mtf_score = 100
            elif align == "PARTIAL_ALIGNMENT":
                mtf_score = 60
            elif align == "CONFLICT":
                mtf_score = 0
            else:
                mtf_score = 40
            factors.append({"name": "MTF Agreement", "score": mtf_score, "weight": TradeQualityScorer.MTF_BONUS_WEIGHT, "detail": f"MTF: {align}"})
            total_weight += TradeQualityScorer.MTF_BONUS_WEIGHT
            weighted += mtf_score * TradeQualityScorer.MTF_BONUS_WEIGHT
            total_score = weighted / total_weight if total_weight > 0 else 0

        total_score = max(0, min(100, round(total_score)))
        grade = TradeQualityScorer._to_grade(total_score)
        reasoning = TradeQualityScorer._build_reasoning(factors, total_score, grade)

        return {
            "total_score": total_score,
            "grade": grade,
            "factor_scores": sorted(factors, key=lambda f: f["weight"], reverse=True),
            "reasoning": reasoning,
            "warnings": TradeQualityScorer._build_warnings(factors),
        }

    @staticmethod
    def _score_trend(direction: str, context_snap: dict[str, Any] | None) -> int:
        if not context_snap:
            return 30
        trend = context_snap.get("trend", "NEUTRAL")
        strength = context_snap.get("trend_strength", "WEAK")
        trend = str(trend).upper()
        strength = str(strength).upper()
        direction = str(direction).upper()

        if direction == "BUY" and trend in ("BULLISH", "UPTREND"):
            return 95 if strength == "STRONG" else 70
        elif direction == "SELL" and trend in ("BEARISH", "DOWNTREND"):
            return 95 if strength == "STRONG" else 70
        elif trend in ("RANGING", "NEUTRAL", "SIDEWAYS"):
            return 40
        else:
            return 20  # Against trend

    @staticmethod
    def _trend_detail(direction: str, context_snap: dict[str, Any] | None) -> str:
        if not context_snap:
            return "No trend data"
        trend = context_snap.get("trend", "N/A")
        strength = context_snap.get("trend_strength", "N/A")
        return f"Trend: {trend} ({strength}) — {'aligned' if not (direction.upper() == 'BUY' and str(trend).upper() in ('BEARISH', 'DOWNTREND')) else 'against'}"

    @staticmethod
    def _score_risk_reward(decision_snap: dict[str, Any] | None, sr_snap: dict[str, Any] | None) -> int:
        tp = (decision_snap or {}).get("trade_plan", {})
        sl_price = tp.get("sl_zone")
        entry_price = tp.get("entry_zone")
        target_zones = tp.get("target_zones", [])
        target_price = target_zones[0] if isinstance(target_zones, list) and target_zones else tp.get("target_price")

        # Handle both dict and scalar zone formats
        if isinstance(sl_price, dict):
            sl_price = sl_price.get("price") or sl_price.get("value")
        if isinstance(entry_price, dict):
            entry_price = entry_price.get("price") or entry_price.get("value") or entry_price
        if isinstance(target_price, dict):
            target_price = target_price.get("price") or target_price.get("value")

        if sl_price and entry_price and target_price:
            try:
                risk = abs(float(entry_price) - float(sl_price))
                reward = abs(float(target_price) - float(entry_price))
                if risk > 0:
                    rr = reward / risk
                    if rr >= 3.0:
                        return 100
                    elif rr >= 2.5:
                        return 90
                    elif rr >= 2.0:
                        return 80
                    elif rr >= 1.5:
                        return 60
                    elif rr >= 1.0:
                        return 40
                    else:
                        return 10
            except (TypeError, ValueError, ZeroDivisionError):
                pass
        return 40  # Default if can't calculate

    @staticmethod
    def _rr_detail(decision_snap: dict[str, Any] | None, sr_snap: dict[str, Any] | None) -> str:
        rr = TradeQualityScorer._score_risk_reward(decision_snap, sr_snap)
        if rr >= 80:
            return "Favorable R:R ratio"
        elif rr >= 60:
            return "Adequate R:R ratio"
        elif rr >= 40:
            return "Borderline R:R ratio"
        else:
            return "Poor R:R ratio"

    @staticmethod
    def _score_patterns(direction: str, pattern_snap: dict[str, Any] | None) -> int:
        if not pattern_snap:
            return 30
        count = pattern_snap.get("pattern_count") or pattern_snap.get("total_count", 0)
        if isinstance(count, (list, dict)):
            count = 0
        direction_str = str(direction).upper()
        pat_dir = str(pattern_snap.get("pattern_direction", "NEUTRAL")).upper()
        aligned = (direction_str == "BUY" and pat_dir in ("BULLISH", "BUY")) or \
                  (direction_str == "SELL" and pat_dir in ("BEARISH", "SELL"))
        score = 30
        if aligned:
            score += 30
        if count and isinstance(count, (int, float)) and count >= 3:
            score += 20
        elif count and isinstance(count, (int, float)) and count >= 1:
            score += 10
        if pattern_snap.get("strongest_pattern"):
            score += 10
        return min(100, score)

    @staticmethod
    def _pattern_detail(pattern_snap: dict[str, Any] | None) -> str:
        if not pattern_snap:
            return "No patterns"
        pat = pattern_snap.get("strongest_pattern", "none")
        count = pattern_snap.get("pattern_count") or pattern_snap.get("total_count", 0)
        return f"{count} patterns, strongest: {pat}"

    @staticmethod
    def _score_liquidity(context_snap: dict[str, Any] | None, indicator_snap: dict[str, Any] | None) -> int:
        score = 70  # Base
        if indicator_snap:
            volume = indicator_snap.get("candle_volume") or indicator_snap.get("volume")
            avg_vol = indicator_snap.get("average_volume")
            if volume and avg_vol and avg_vol > 0:
                ratio = volume / avg_vol
                if ratio > 1.5:
                    score += 15
                elif ratio < 0.5:
                    score -= 20
        if context_snap:
            sweeps = context_snap.get("liquidity_sweeps", 0)
            if isinstance(sweeps, (int, float)) and sweeps > 2:
                score -= 15
        return max(0, min(100, score))

    @staticmethod
    def _liquidity_detail(context_snap: dict[str, Any] | None, indicator_snap: dict[str, Any] | None) -> str:
        parts = []
        if indicator_snap:
            vol = indicator_snap.get("candle_volume") or indicator_snap.get("volume")
            if vol:
                parts.append(f"Vol: {vol:.0f}")
        if context_snap:
            swp = context_snap.get("liquidity_sweeps", 0)
            if isinstance(swp, (int, float)) and swp > 0:
                parts.append(f"Sweeps: {swp}")
        return ", ".join(parts) if parts else "Normal liquidity"

    @staticmethod
    def _score_execution(indicator_snap: dict[str, Any] | None, sr_snap: dict[str, Any] | None) -> int:
        score = 70
        if indicator_snap:
            atr = indicator_snap.get("atr_14")
            close = indicator_snap.get("candle_close")
            if atr and close and close > 0:
                atr_pct = (atr / close) * 100
                if atr_pct > 3:
                    score -= 20
                elif atr_pct < 0.3:
                    score -= 10
        if sr_snap:
            nearest_s = sr_snap.get("nearest_support")
            nearest_r = sr_snap.get("nearest_resistance")
            if nearest_s and nearest_r:
                spread = nearest_r - nearest_s
                if spread > 0 and close and (spread / close) < 0.01:
                    score += 10
                elif spread > 0 and close and (spread / close) > 0.05:
                    score -= 10
        return max(0, min(100, score))

    @staticmethod
    def _execution_detail(indicator_snap: dict[str, Any] | None) -> str:
        if not indicator_snap:
            return "No execution data"
        atr = indicator_snap.get("atr_14")
        close = indicator_snap.get("candle_close")
        if atr and close and close > 0:
            return f"ATR: {atr:.1f} ({(atr/close)*100:.1f}%)"
        return "Execution feasible"

    @staticmethod
    def _to_grade(score: int) -> str:
        if score >= 95:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 65:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "REJECT"

    @staticmethod
    def _build_reasoning(factors: list[dict[str, Any]], total: int, grade: str) -> list[str]:
        reasons = [f"Total score: {total}/100 — Grade: {grade}"]
        top = sorted(factors, key=lambda f: f["score"], reverse=True)[:2]
        for f in top:
            reasons.append(f"{f['name']}: {f['score']}")
        return reasons

    @staticmethod
    def _build_warnings(factors: list[dict[str, Any]]) -> list[str]:
        warnings = []
        for f in factors:
            if f["score"] < 40:
                warnings.append(f"Low {f['name']}: {f['score']}")
        return warnings[:3]

"""
Trade Plan Engine — Strategy qualification, trade planning, and Risk Firewall integration.

Flow:
    AIDecision → StrategyEngine.qualify() → TradePlanner.build_plan()
    → RiskEngine.validate() → Approved/Blocked TradePlan
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from ai_decision.decision_service import AIDecision
from risk.trade_validator import TradeIntent
from risk.risk_engine import RiskEngine
from core.enums import normalize_direction, TradeDirection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"tplan_{uuid.uuid4().hex[:12]}"


def _canonical_side(direction: str) -> str:
    """
    Normalize LONG→BUY, SHORT→SELL for internal direction comparisons
    in strategy qualification, stop loss, and target calculation.
    """
    try:
        d = normalize_direction(direction)
        if d == TradeDirection.LONG:
            return "BUY"
        if d == TradeDirection.SHORT:
            return "SELL"
        return "WAIT"
    except ValueError:
        return "WAIT"


@dataclass
class TradePlan:
    """Complete structured trade plan after strategy + planner + risk validation."""
    plan_id: str = ""
    trace_id: str = ""
    decision_id: str = ""

    # Identity
    symbol: str = ""
    direction: str = "NONE"  # Canonical: LONG, SHORT, NONE
    strategy: str = "ai_strategy"
    strategy_version: str = "1.0"
    execution_type: str = "synthetic_spot"  # "synthetic_spot" / "option_buying"

    # Option-specific fields (used when execution_type == "option_buying")
    option_type: str | None = None
    option_strike: float | None = None
    option_expiry: str | None = None
    option_premium: float | None = None
    option_lot_size: int | None = None
    option_lots: int | None = None
    option_instrument_token: int | None = None
    option_execution_symbol: str | None = None
    underlying_entry_price: float | None = None
    underlying_stop_price: float | None = None
    underlying_target_price: float | None = None

    # Entry
    entry_price: float | None = None
    entry_type: str = "MARKET"
    entry_zone: str | None = None

    # Stop Loss
    stop_price: float | None = None
    stop_distance: float | None = None
    stop_reason: str | None = None

    # Target
    target_price: float | None = None
    target_distance: float | None = None
    target_reason: str | None = None

    # Risk
    risk_reward: float | None = None
    risk_amount: float | None = None
    risk_percent: float | None = None
    position_size: int = 0
    capital_required: float | None = None

    # Qualification
    qualified: bool = False
    qualification_score: int = 0
    rejection_reason: str | None = None

    # AI context
    ai_score: int = 0
    ai_confidence: int = 0
    ai_decision: str = "NO_TRADE"

    # Market context
    market_regime: str | None = None
    trend: str | None = None
    momentum: str | None = None
    volatility: str | None = None
    mtf_alignment: str | None = None

    # Risk Firewall
    risk_status: str | None = None  # "approved", "blocked", "pending"
    risk_score: float = 0.0
    risk_grade: str = "LOW"
    risk_block_reason: str | None = None

    # Data quality
    data_freshness: str = "live"

    # Timing
    created_at: str = ""
    expires_at: str = ""
    strategy_reasoning: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "trace_id": self.trace_id,
            "decision_id": self.decision_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "strategy": self.strategy,
            "entry_price": self.entry_price,
            "entry_type": self.entry_type,
            "stop_price": self.stop_price,
            "stop_distance": self.stop_distance,
            "stop_reason": self.stop_reason,
            "target_price": self.target_price,
            "target_distance": self.target_distance,
            "target_reason": self.target_reason,
            "risk_reward": self.risk_reward,
            "risk_amount": self.risk_amount,
            "risk_percent": self.risk_percent,
            "position_size": self.position_size,
            "capital_required": self.capital_required,
            "qualified": self.qualified,
            "qualification_score": self.qualification_score,
            "rejection_reason": self.rejection_reason,
            "ai_score": self.ai_score,
            "ai_confidence": self.ai_confidence,
            "ai_decision": self.ai_decision,
            "market_regime": self.market_regime,
            "trend": self.trend,
            "momentum": self.momentum,
            "volatility": self.volatility,
            "mtf_alignment": self.mtf_alignment,
            "risk_status": self.risk_status,
            "risk_score": self.risk_score,
            "risk_grade": self.risk_grade,
            "risk_block_reason": self.risk_block_reason,
            "data_freshness": self.data_freshness,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "strategy_reasoning": self.strategy_reasoning,
        }


class StrategyEngine:
    """
    Qualifies AI decisions by checking market context alignment.

    An AI BUY/SELL does not automatically mean a trade is valid.
    This engine validates the decision against current market conditions.
    """

    @staticmethod
    def qualify(
        decision: AIDecision,
        price: float | None = None,
        context_snap: dict | None = None,
        indicator_snap: dict | None = None,
        structure_snap: dict | None = None,
        mtf_snap: dict | None = None,
        sr_snap: dict | None = None,
    ) -> tuple[bool, int, str, list[str]]:
        """
        Qualify an AI decision. Returns (qualified, score, reason, reasoning_list).

        If AI says WAIT → always reject.
        If context conflicts with AI direction → reject with reason.
        """
        reasoning: list[str] = []
        score: float = 50.0  # base score
        raw_direction = (decision.direction or "WAIT").upper()
        # Normalize canonical LONG/SHORT to BUY/SELL for internal comparisons
        direction = _canonical_side(raw_direction)

        # AI says WAIT — always reject
        if direction == "WAIT":
            return False, 0, "AI_WAIT", ["AI decision is WAIT — no trade to plan"]

        # Data freshness check
        if decision.data_freshness in ("stale", "disconnected"):
            return False, 0, "STALE_DATA", ["Market data is stale"]

        # Market context checks
        if context_snap:
            trend = context_snap.get("trend", "NEUTRAL")
            bias = context_snap.get("overall_bias", "NEUTRAL")
            momentum = context_snap.get("momentum", "WEAK")
            regime = context_snap.get("market_regime", "")

            # Trend alignment
            if direction == "BUY" and trend == "BULLISH":
                score += 15
                reasoning.append(f"Trend aligned: {trend}")
            elif direction == "SELL" and trend == "BEARISH":
                score += 15
                reasoning.append(f"Trend aligned: {trend}")
            else:
                score -= 10
                reasoning.append(f"Trend conflict: AI={direction}, trend={trend}")

            # Bias alignment
            if direction == "BUY" and bias in ("BULLISH", "STRONG_BUY"):
                score += 10
                reasoning.append(f"Bias aligned: {bias}")
            elif direction == "SELL" and bias in ("BEARISH", "STRONG_SELL"):
                score += 10
                reasoning.append(f"Bias aligned: {bias}")

            # Momentum
            if momentum == "STRONG":
                score += 10
                reasoning.append(f"Momentum: {momentum}")
            elif momentum == "WEAK":
                score -= 5
                reasoning.append(f"Momentum weak: {momentum}")

            # Market regime caution
            if "CRISIS" in regime or "STRESS" in regime:
                score -= 20
                reasoning.append(f"Caution: market regime {regime}")

        # MTF alignment
        if mtf_snap:
            align = mtf_snap.get("alignment_level", "MIXED")
            align_score = mtf_snap.get("alignment_score", 0)
            bias_dir = mtf_snap.get("institutional_bias", "")

            if align in ("FULL_ALIGNMENT", "STRONG_ALIGNMENT"):
                score += 15
                reasoning.append(f"MTF aligned: {align} ({align_score})")
            elif align == "CONFLICT":
                score -= 15
                reasoning.append(f"MTF conflict: {align}")

            # Bias alignment check
            if direction == "BUY" and "BULLISH" in bias_dir:
                score += 5
            elif direction == "SELL" and "BEARISH" in bias_dir:
                score += 5

        # Structure
        if structure_snap:
            valid = structure_snap.get("valid_structure", False)
            phase = structure_snap.get("market_phase", "")
            if valid:
                score += 5
                reasoning.append("Valid market structure")
            if direction == "BUY" and phase in ("markup", "accumulation"):
                score += 5
                reasoning.append(f"Structure supports BUY: {phase}")
            elif direction == "SELL" and phase in ("markdown", "distribution"):
                score += 5
                reasoning.append(f"Structure supports SELL: {phase}")

        # S/R proximity
        if sr_snap and price and price > 0:
            nearest_r = sr_snap.get("nearest_resistance")
            nearest_s = sr_snap.get("nearest_support")
            if direction == "BUY" and nearest_r and nearest_r > 0:
                dist_to_r = (nearest_r - price) / price * 100
                if dist_to_r < 1.0:
                    score -= 15
                    reasoning.append(f"BUY too close to resistance ({dist_to_r:.1f}%)")
                else:
                    score += 5
                    reasoning.append(f"Room to resistance: {dist_to_r:.1f}%")
            if direction == "SELL" and nearest_s and nearest_s > 0:
                dist_to_s = (price - nearest_s) / price * 100
                if dist_to_s < 1.0:
                    score -= 15
                    reasoning.append(f"SELL too close to support ({dist_to_s:.1f}%)")
                else:
                    score += 5
                    reasoning.append(f"Room to support: {dist_to_s:.1f}%")

        # AI confidence
        score += (decision.confidence - 50) * 0.3
        if decision.confidence >= 70:
            reasoning.append(f"AI confidence: {decision.confidence}%")
        elif decision.confidence < 40:
            reasoning.append(f"Low AI confidence: {decision.confidence}%")

        # Final score
        final_score = max(0, min(100, int(score)))
        qualified = final_score >= 50

        if not qualified:
            return False, final_score, f"SCORE_TOO_LOW: {final_score}", reasoning

        return True, final_score, "QUALIFIED", reasoning


class TradePlanner:
    """
    Builds a complete TradePlan from a qualified AI decision.

    Calculates entry, stop loss, target, risk/reward, and position sizing.
    Then validates through the Risk Firewall.
    """

    def __init__(self, risk_engine: RiskEngine | None = None):
        self._risk_engine = risk_engine

    def set_risk_engine(self, engine: RiskEngine):
        self._risk_engine = engine

    def build_plan(
        self,
        decision: AIDecision,
        price: float | None = None,
        context_snap: dict | None = None,
        indicator_snap: dict | None = None,
        structure_snap: dict | None = None,
        mtf_snap: dict | None = None,
        sr_snap: dict | None = None,
        capital: float = 100000.0,
        risk_percent_config: float = 2.0,
    ) -> TradePlan:
        """Build a complete TradePlan from an AI decision."""
        plan = TradePlan(
            plan_id=_new_id(),
            trace_id=decision.trace_id or f"trace_{uuid.uuid4().hex[:8]}",
            decision_id=decision.decision_id,
            symbol=decision.symbol,
            direction=decision.direction or "WAIT",
            ai_score=decision.score,
            ai_confidence=decision.confidence,
            ai_decision=decision.decision,
            market_regime=decision.market_snapshot.get("market_regime") if decision.market_snapshot else None,
            trend=decision.market_snapshot.get("trend") if decision.market_snapshot else None,
            momentum=decision.market_snapshot.get("momentum") if decision.market_snapshot else None,
            volatility=decision.market_snapshot.get("volatility") if decision.market_snapshot else None,
            mtf_alignment=decision.market_snapshot.get("mtf_alignment") if decision.market_snapshot else None,
            data_freshness=decision.data_freshness,
            created_at=_now(),
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
        )

        if _canonical_side(decision.direction or "") == "WAIT":
            plan.qualified = False
            plan.rejection_reason = "AI_WAIT"
            plan.strategy_reasoning = ["AI decision is WAIT"]
            return plan

        market_price = price or (decision.market_snapshot or {}).get("last_price") or 0
        if market_price <= 0:
            plan.qualified = False
            plan.rejection_reason = "NO_MARKET_PRICE"
            return plan

        # Step 1: Strategy qualification
        qualified, qual_score, qual_reason, qual_reasoning = StrategyEngine.qualify(
            decision=decision,
            price=market_price,
            context_snap=context_snap,
            indicator_snap=indicator_snap,
            structure_snap=structure_snap,
            mtf_snap=mtf_snap,
            sr_snap=sr_snap,
        )
        plan.qualification_score = qual_score
        plan.strategy_reasoning = qual_reasoning

        if not qualified:
            plan.qualified = False
            plan.rejection_reason = qual_reason
            return plan

        # Step 2: Calculate stop loss
        stop = self._calc_stop_loss(
            direction=plan.direction,
            entry=market_price,
            sr_snap=sr_snap,
            structure_snap=structure_snap,
            indicator_snap=indicator_snap,
        )
        if not stop:
            plan.qualified = False
            plan.rejection_reason = "NO_VALID_STOP"
            plan.strategy_reasoning.append("Could not determine logical stop loss")
            return plan

        plan.stop_price = stop["price"]
        plan.stop_distance = stop["distance"]
        plan.stop_reason = stop["reason"]

        # Step 3: Calculate target
        target = self._calc_target(
            direction=plan.direction,
            entry=market_price,
            stop_price=plan.stop_price,
            sr_snap=sr_snap,
            structure_snap=structure_snap,
            indicator_snap=indicator_snap,
        )
        if not target:
            plan.qualified = False
            plan.rejection_reason = "NO_VALID_TARGET"
            plan.strategy_reasoning.append("Could not determine logical target")
            return plan

        plan.target_price = target["price"]
        plan.target_distance = target["distance"]
        plan.target_reason = target["reason"]

        # Step 4: Calculate risk/reward
        risk = abs(market_price - plan.stop_price)
        reward = abs(target["price"] - market_price)
        if risk > 0:
            plan.risk_reward = round(reward / risk, 2)
        else:
            plan.risk_reward = 0

        # Check minimum R:R (use config or default 1.5)
        min_rr = 1.5
        if plan.risk_reward < min_rr:
            plan.qualified = False
            plan.rejection_reason = f"INSUFFICIENT_RR: {plan.risk_reward:.2f} < {min_rr}"
            plan.strategy_reasoning.append(f"R:R {plan.risk_reward:.2f} below minimum {min_rr}")
            return plan

        # Step 5: Position sizing
        risk_amount = capital * (risk_percent_config / 100)
        raw_qty = int(risk_amount / risk) if risk > 0 else 0
        plan.position_size = max(raw_qty, 1)
        plan.risk_amount = round(risk_amount, 2)
        plan.risk_percent = risk_percent_config
        plan.capital_required = round(plan.position_size * market_price, 2)

        # Step 6: Entry
        plan.entry_price = market_price
        plan.entry_type = "MARKET"

        # Step 7: Risk Firewall validation
        self._validate_risk(plan)

        plan.qualified = True
        return plan

    # ── Stop Loss calculation ──

    def _calc_stop_loss(
        self,
        direction: str,
        entry: float,
        sr_snap: dict | None = None,
        structure_snap: dict | None = None,
        indicator_snap: dict | None = None,
    ) -> dict | None:
        """Calculate logical stop loss based on market structure and S/R."""
        side = _canonical_side(direction)
        if not side:
            return None
        # Use S/R levels for stop
        if sr_snap:
            if side == "BUY":
                level = sr_snap.get("nearest_support")
                if level and level < entry:
                    dist = abs(entry - level)
                    return {
                        "price": level,
                        "distance": round(dist, 2),
                        "reason": f"Below nearest support at {level}",
                    }
            else:
                level = sr_snap.get("nearest_resistance")
                if level and level > entry:
                    dist = abs(level - entry)
                    return {
                        "price": level,
                        "distance": round(dist, 2),
                        "reason": f"Above nearest resistance at {level}",
                    }

        # Use ATR-based stop if S/R unavailable
        atr = None
        if indicator_snap:
            atr = indicator_snap.get("atr_14") or indicator_snap.get("atr")
        if atr and atr > 0:
            atr_dist = atr * 2
            if side == "BUY":
                stop = entry - atr_dist
                return {
                    "price": round(stop, 2),
                    "distance": round(atr_dist, 2),
                    "reason": f"ATR-based ({atr:.1f} × 2) below entry",
                }
            else:
                stop = entry + atr_dist
                return {
                    "price": round(stop, 2),
                    "distance": round(atr_dist, 2),
                    "reason": f"ATR-based ({atr:.1f} × 2) above entry",
                }

        # Fallback: percentage-based
        pct = 0.01  # 1%
        if side == "BUY":
            stop = entry * (1 - pct)
            return {"price": round(stop, 2), "distance": round(entry * pct, 2), "reason": "1% below entry (fallback)"}
        else:
            stop = entry * (1 + pct)
            return {"price": round(stop, 2), "distance": round(entry * pct, 2), "reason": "1% above entry (fallback)"}

    # ── Target calculation ──

    def _calc_target(
        self,
        direction: str,
        entry: float,
        stop_price: float,
        sr_snap: dict | None = None,
        structure_snap: dict | None = None,
        indicator_snap: dict | None = None,
    ) -> dict | None:
        """Calculate logical target based on market structure and S/R."""
        side = _canonical_side(direction)
        if not side:
            return None
        risk = abs(entry - stop_price)
        min_reward = risk * 2  # minimum 2:1 R:R target

        if sr_snap:
            if side == "BUY":
                level = sr_snap.get("nearest_resistance")
                if level and level > entry:
                    reward = level - entry
                    if reward >= min_reward:
                        return {
                            "price": level,
                            "distance": round(reward, 2),
                            "reason": f"Nearest resistance at {level}",
                        }
            else:
                level = sr_snap.get("nearest_support")
                if level and level < entry:
                    reward = entry - level
                    if reward >= min_reward:
                        return {
                            "price": level,
                            "distance": round(reward, 2),
                            "reason": f"Nearest support at {level}",
                        }

        # ATR-based target
        atr = None
        if indicator_snap:
            atr = indicator_snap.get("atr_14") or indicator_snap.get("atr")
        if atr and atr > 0:
            target_dist = max(atr * 3, min_reward)
            if side == "BUY":
                tgt = entry + target_dist
            else:
                tgt = entry - target_dist
            return {
                "price": round(tgt, 2),
                "distance": round(target_dist, 2),
                "reason": f"ATR-based ({atr:.1f} × 3) target",
            }

        # Fixed R:R fallback
        target_dist = max(risk * 2, entry * 0.02)
        if side == "BUY":
            tgt = entry + target_dist
        else:
            tgt = entry - target_dist
        return {
            "price": round(tgt, 2),
            "distance": round(target_dist, 2),
            "reason": "2:1 R:R target (fallback)",
        }

    # ── Risk Firewall integration ──

    def _validate_risk(self, plan: TradePlan):
        """Validate the trade plan through the Risk Firewall."""
        if not self._risk_engine or not plan.entry_price:
            plan.risk_status = "pending"
            return

        try:
            intent = TradeIntent(
                symbol=plan.symbol,
                side=plan.direction or "BUY",
                quantity=plan.position_size,
                price=plan.entry_price,
                order_type="MARKET",
                product="MIS",
                exchange="NSE",
                strategy=plan.strategy,
                ai_score=float(plan.ai_score) if plan.ai_score else None,
                ai_confidence=float(plan.ai_confidence) if plan.ai_confidence else None,
                ai_decision=plan.ai_decision,
                stop_loss=plan.stop_price,
                take_profit=plan.target_price,
                tag=plan.trace_id,
            )
            validation = self._risk_engine.validate(intent)
            plan.risk_score = validation.risk_score
            plan.risk_grade = validation.risk_grade
            plan.risk_block_reason = "; ".join(validation.rejected_by) if validation.rejected_by else None

            if validation.execution_permitted:
                plan.risk_status = "approved"
            else:
                plan.risk_status = "blocked"
                plan.rejection_reason = f"RISK_BLOCKED: {plan.risk_block_reason}"
                plan.qualified = False

        except Exception as e:
            plan.risk_status = "error"
            plan.risk_block_reason = str(e)
            plan.rejection_reason = "RISK_ERROR"

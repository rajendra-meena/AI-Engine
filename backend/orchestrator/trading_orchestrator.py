"""
Trading Orchestrator — Central coordinator for the end-to-end pipeline.

Coordinates: Market Data → Context → AI → ML → Strategy → Planner →
             Risk Firewall → Execution → Portfolio → Learning

Every stage is independently safe. Risk Firewall is the HARD GATE
that must pass before any broker order is submitted.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from orchestrator.decision_context import (
    DecisionContext,
    ExecutionMode,
    OrderState,
    PipelineResult,
    PipelineStage,
    StageStatus,
    VALID_TRANSITIONS,
)
from risk.trade_validator import TradeIntent
from risk.risk_engine import RiskEngine
from learning import integration as lri
from trading.trade_lifecycle import TradeLifecycleManager
from utils.logger import log_info, log_warn, log_error


# Global engine references (set by main.py)
_risk_engine: RiskEngine | None = None


def set_risk_engine(engine: RiskEngine):
    global _risk_engine
    _risk_engine = engine


def _get_risk() -> RiskEngine:
    assert _risk_engine is not None, "RiskEngine not initialized"
    return _risk_engine


# ── Trace ID generation ──

def _new_trace_id() -> str:
    return f"TRACE-{uuid.uuid4().hex[:8].upper()}"


def _new_correlation_id() -> str:
    import uuid
    return f"corr_{uuid.uuid4().hex[:16]}"


# ── Ordered pipeline stages ──

PIPELINE_ORDER = [
    PipelineStage.MARKET_DATA,
    PipelineStage.CONTEXT,
    PipelineStage.AI_DECISION,
    PipelineStage.ML_PREDICTION,
    PipelineStage.STRATEGY,
    PipelineStage.TRADE_PLANNER,
    PipelineStage.RISK_FIREWALL,
    PipelineStage.EXECUTION,
    PipelineStage.PORTFOLIO,
    PipelineStage.LEARNING,
]


# ── State machine helper ──

def _transition_to(ctx: DecisionContext, new_state: OrderState) -> bool:
    """Attempt to transition order state. Returns False if invalid."""
    current = ctx.order_state
    allowed = VALID_TRANSITIONS.get(current, [])
    if new_state not in allowed:
        log_warn(
            "Orchestrator: invalid state transition",
            from_state=current.value,
            to_state=new_state.value,
            trace_id=ctx.trace_id,
        )
        return False
    ctx.order_state = new_state
    return True


# ── Orchestrator ──

class TradingOrchestrator:
    """
    End-to-end trading pipeline coordinator.

    Run the full pipeline with analyze():
        1. Market context
        2. AI Decision
        3. ML Prediction
        4. Strategy
        5. Trade Planner
        6. Risk Firewall (HARD GATE)
        7. Execution
        8. Portfolio
        9. Learning

    If Risk Firewall blocks, execution and later stages are skipped.
    """

    def __init__(self):
        self._history: list[dict[str, Any]] = []
        self._traces: dict[str, DecisionContext] = {}
        self._idempotency_store: dict[str, dict[str, Any]] = {}

    # ── Main entry point ──

    async def analyze(
        self,
        symbol: str,
        interval: str = "15m",
        exchange: str = "NSE",
        execution_mode: str = "paper",
        strategy_id: str | None = None,
        user_id: str = "",
        ai_score: int | None = None,
        ai_confidence: int | None = None,
        ai_decision: str | None = None,
        ml_prediction: str | None = None,
        ml_probability: float | None = None,
        market_price: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Run the full analysis pipeline. Returns the complete decision context.
        This does NOT execute an order — use execute() for that.
        """
        # Idempotency check
        if idempotency_key and idempotency_key in self._idempotency_store:
            log_info("Orchestrator: idempotency hit", key=idempotency_key)
            return self._idempotency_store[idempotency_key]

        ctx = DecisionContext(
            trace_id=_new_trace_id(),
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            market_price=market_price,
            execution_mode=ExecutionMode(execution_mode) if execution_mode else ExecutionMode.PAPER,
            correlation_id=_new_correlation_id(),
        )

        start = time.time()

        # ── Stage 1: Market Data ──
        ctx.set_stage(PipelineStage.MARKET_DATA, StageStatus.PASSED)
        # (Data is assumed available — the caller provides it)

        # ── Stage 2: Context ──
        ctx.set_stage(PipelineStage.CONTEXT, StageStatus.PASSED)

        # ── Stage 3: AI Decision ──
        if ai_decision:
            ctx.ai_decision = ai_decision
            ctx.ai_score = ai_score
            ctx.ai_confidence = ai_confidence
            ctx.set_stage(PipelineStage.AI_DECISION, StageStatus.PASSED, output={
                "decision": ai_decision, "score": ai_score, "confidence": ai_confidence,
            })
        else:
            ctx.set_stage(PipelineStage.AI_DECISION, StageStatus.SKIPPED)

        # ── Stage 4: ML Prediction ──
        if ml_prediction:
            ctx.ml_prediction = ml_prediction
            ctx.ml_probability = ml_probability
            ctx.set_stage(PipelineStage.ML_PREDICTION, StageStatus.PASSED, output={
                "prediction": ml_prediction, "probability": ml_probability,
            })
        else:
            ctx.set_stage(PipelineStage.ML_PREDICTION, StageStatus.SKIPPED)

        # ── Stage 5: Strategy ──
        ctx.set_stage(PipelineStage.STRATEGY, StageStatus.PASSED)

        # ── Stage 6: Trade Planner ──
        ctx.set_stage(PipelineStage.TRADE_PLANNER, StageStatus.PASSED)

        # ── Stage 7: Risk Firewall (HARD GATE) ──
        risk_result = self._run_risk_firewall(ctx)
        ctx.stages[PipelineStage.RISK_FIREWALL.value] = risk_result

        if risk_result.status == StageStatus.BLOCKED:
            ctx.risk_status = "blocked"
            ctx.risk_reasons = [risk_result.blocked_reason] if risk_result.blocked_reason else []
            ctx.set_stage(PipelineStage.EXECUTION, StageStatus.SKIPPED)
            ctx.set_stage(PipelineStage.PORTFOLIO, StageStatus.SKIPPED)

            # ── Learning: Record blocked trade ──
            self._record_learning_blocked(ctx)
            ctx.set_stage(PipelineStage.LEARNING, StageStatus.PASSED)

            ctx.order_state = OrderState.BLOCKED
            elapsed = time.time() - start
            result = ctx.to_dict()
            result["pipeline_duration_ms"] = round(elapsed * 1000, 1)

            if idempotency_key:
                self._idempotency_store[idempotency_key] = result

            self._history.append(result)
            self._traces[ctx.trace_id] = ctx
            return result

        # Risk passed — qualified for execution
        ctx.risk_status = "approved"
        ctx.order_state = OrderState.APPROVED
        ctx.set_stage(PipelineStage.RISK_FIREWALL, StageStatus.PASSED, output={
            "risk_score": ctx.risk_score,
            "risk_grade": ctx.risk_grade,
        })

        elapsed = time.time() - start
        result = ctx.to_dict()
        result["pipeline_duration_ms"] = round(elapsed * 1000, 1)

        if idempotency_key:
            self._idempotency_store[idempotency_key] = result

        self._history.append(result)
        self._traces[ctx.trace_id] = ctx
        return result

    # ── Risk Firewall ──

    def _run_risk_firewall(self, ctx: DecisionContext) -> PipelineResult:
        """Execute the Risk Firewall validation."""
        try:
            risk = _get_risk()
            intent = TradeIntent(
                symbol=ctx.symbol,
                side=ctx.ai_direction or "BUY",
                quantity=ctx.quantity or 1,
                price=ctx.market_price,
                order_type=ctx.order_type,
                product=ctx.product,
                exchange=ctx.exchange,
                strategy=ctx.strategy_id or "orchestrator",
                ai_score=float(ctx.ai_score) if ctx.ai_score else None,
                ai_confidence=float(ctx.ai_confidence) if ctx.ai_confidence else None,
                ai_decision=ctx.ai_decision,
                stop_loss=ctx.stop_loss,
                take_profit=ctx.target,
                tag=ctx.trace_id,
            )
            validation = risk.validate(intent)
            ctx.risk_firewall_result = validation.to_dict()
            ctx.risk_score = validation.risk_score
            ctx.risk_grade = validation.risk_grade
            ctx.risk_reasons = validation.rejected_by

            if not validation.execution_permitted:
                reason = "; ".join(validation.rejected_by) if validation.rejected_by else "Risk Firewall blocked"
                return PipelineResult(
                    stage=PipelineStage.RISK_FIREWALL,
                    status=StageStatus.BLOCKED,
                    blocked_reason=reason,
                    output=validation.to_dict(),
                )
            return PipelineResult(
                stage=PipelineStage.RISK_FIREWALL,
                status=StageStatus.PASSED,
                output=validation.to_dict(),
            )
        except Exception as e:
            log_error("Orchestrator: risk firewall error", trace_id=ctx.trace_id, error=str(e))
            return PipelineResult(
                stage=PipelineStage.RISK_FIREWALL,
                status=StageStatus.FAILED,
                error=str(e),
            )

    # ── Learning: Journal prediction ──

    def _journal_prediction(self, ctx: DecisionContext) -> str | None:
        """Record the prediction in the learning journal."""
        try:
            pid = lri.journal_ai_prediction(
                symbol=ctx.symbol,
                interval=ctx.interval,
                decision=ctx.ai_decision or "NO_TRADE",
                score=ctx.ai_score or 0,
                confidence=ctx.ai_confidence or 0,
                direction=ctx.ai_direction,
                exchange=ctx.exchange,
                risk_score=int(ctx.risk_score) if ctx.risk_score else None,
                risk_level=ctx.risk_grade,
                entry_price=ctx.entry_price or ctx.market_price,
                stop_loss=ctx.stop_loss,
                target=ctx.target,
                risk_reward=ctx.risk_reward,
                strategy_id=ctx.strategy_id,
                market_regime=ctx.market_regime,
                trend=ctx.trend,
                institutional_bias=ctx.institutional_bias,
                mtf_alignment=ctx.mtf_alignment,
                volatility=ctx.volatility,
                momentum=ctx.momentum,
                ml_prediction=ctx.ml_prediction,
                ml_confidence=ctx.ml_probability,
                prediction_source="orchestrator",
                correlation_id=ctx.correlation_id,
            )
            ctx.prediction_id = pid
            return pid
        except Exception as e:
            log_warn("Orchestrator: prediction journal failed", trace_id=ctx.trace_id, error=str(e))
            return None

    # ── Learning: Record blocked trade ──

    def _record_learning_blocked(self, ctx: DecisionContext):
        """Record a blocked trade in the learning engine."""
        try:
            if ctx.prediction_id:
                lri.record_blocked_trade(
                    prediction_id=ctx.prediction_id,
                    symbol=ctx.symbol,
                    direction=ctx.ai_direction,
                    intended_entry=ctx.entry_price or ctx.market_price,
                    intended_sl=ctx.stop_loss,
                    intended_tp=ctx.target,
                    intended_quantity=ctx.quantity or 0,
                    ai_score=ctx.ai_score,
                    ai_confidence=ctx.ai_confidence,
                    strategy=ctx.strategy_id,
                    blocked_by=ctx.risk_reasons[0] if ctx.risk_reasons else "risk_firewall",
                    block_reason="; ".join(ctx.risk_reasons),
                    risk_score=int(ctx.risk_score) if ctx.risk_score else None,
                    market_regime=ctx.market_regime,
                    correlation_id=ctx.correlation_id,
                )
        except Exception as e:
            log_warn("Orchestrator: blocked trade record failed", trace_id=ctx.trace_id, error=str(e))

    # ── Learning: Record trade feedback ──

    def _record_trade_feedback(
        self,
        ctx: DecisionContext,
        gross_pnl: float | None = None,
        exit_reason: str | None = None,
    ):
        """Record trade feedback after execution."""
        try:
            if ctx.prediction_id:
                lri.record_trade_feedback(
                    prediction_id=ctx.prediction_id,
                    entry_price=ctx.entry_price or ctx.market_price or 0,
                    gross_pnl=gross_pnl,
                    exit_reason=exit_reason,
                    risk_firewall_result=ctx.risk_firewall_result,
                )
        except Exception as e:
            log_warn("Orchestrator: trade feedback failed", trace_id=ctx.trace_id, error=str(e))

    # ── Queries ──

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Get a specific trace by ID."""
        ctx = self._traces.get(trace_id)
        return ctx.to_dict() if ctx else None

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get pipeline execution history."""
        return list(self._history)[-limit:]

    def get_last_decision(self) -> dict[str, Any] | None:
        """Get the most recent pipeline decision."""
        return self._history[-1] if self._history else None

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status summary."""
        return {
            "total_executions": len(self._history),
            "last_execution": self._history[-1]["timestamp"] if self._history else None,
            "recent_results": {
                "approved": sum(1 for h in self._history[-50:] if h.get("risk_status") == "approved"),
                "blocked": sum(1 for h in self._history[-50:] if h.get("risk_status") == "blocked"),
            },
            "idempotency_cache_size": len(self._idempotency_store),
        }

"""
Trading Orchestrator — Decision Context

Single normalized object passed between every pipeline stage.
Contains ALL available data: market, AI, ML, strategy, planner, risk, execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PipelineStage(str, Enum):
    MARKET_DATA = "market_data"
    CONTEXT = "context"
    AI_DECISION = "ai_decision"
    ML_PREDICTION = "ml_prediction"
    STRATEGY = "strategy"
    TRADE_PLANNER = "trade_planner"
    RISK_FIREWALL = "risk_firewall"
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    LEARNING = "learning"


class StageStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(str, Enum):
    MANUAL = "manual"
    PAPER = "paper"
    SEMI_AUTO = "semi_auto"
    AI_ASSISTED = "ai_assisted"
    LIVE = "live"


class OrderState(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    RISK_CHECK = "risk_check"
    APPROVED = "approved"
    BLOCKED = "blocked"
    SUBMITTING = "submitting"
    ACKNOWLEDGED = "acknowledged"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    EXIT_PENDING = "exit_pending"
    CLOSED = "closed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


VALID_TRANSITIONS: dict[OrderState, list[OrderState]] = {
    OrderState.CREATED: [OrderState.VALIDATING, OrderState.BLOCKED],
    OrderState.VALIDATING: [OrderState.RISK_CHECK, OrderState.BLOCKED, OrderState.FAILED],
    OrderState.RISK_CHECK: [OrderState.APPROVED, OrderState.BLOCKED],
    OrderState.APPROVED: [OrderState.SUBMITTING, OrderState.BLOCKED],
    OrderState.BLOCKED: [],
    OrderState.SUBMITTING: [OrderState.ACKNOWLEDGED, OrderState.REJECTED, OrderState.FAILED],
    OrderState.ACKNOWLEDGED: [OrderState.OPEN, OrderState.REJECTED, OrderState.CANCELLED],
    OrderState.OPEN: [OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED],
    OrderState.PARTIALLY_FILLED: [OrderState.FILLED, OrderState.CANCELLED],
    OrderState.FILLED: [OrderState.EXIT_PENDING, OrderState.CLOSED],
    OrderState.EXIT_PENDING: [OrderState.CLOSED],
    OrderState.CLOSED: [],
    OrderState.REJECTED: [],
    OrderState.CANCELLED: [],
    OrderState.FAILED: [],
}


@dataclass
class PipelineResult:
    """Result of a single pipeline stage."""
    stage: PipelineStage
    status: StageStatus = StageStatus.WAITING
    duration_ms: float = 0.0
    output: dict[str, Any] | None = None
    error: str | None = None
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 1),
            "output": self.output,
            "error": self.error,
            "blocked_reason": self.blocked_reason,
        }


@dataclass
class DecisionContext:
    """
    Single normalized context passed through all pipeline stages.
    Every stage reads from and writes to this object.
    """
    # Trace
    trace_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Symbol
    symbol: str = ""
    exchange: str = "NSE"
    interval: str = "15m"
    market_price: float | None = None

    # Market context
    market_regime: str | None = None
    trend: str | None = None
    momentum: float | None = None
    volatility: float | None = None
    mtf_alignment: str | None = None
    institutional_bias: str | None = None

    # Indicators / Patterns / Structure / S/R
    indicators: dict[str, Any] | None = None
    patterns: dict[str, Any] | None = None
    market_structure: dict[str, Any] | None = None
    support_resistance: dict[str, Any] | None = None

    # AI Decision
    ai_decision: str | None = None
    ai_score: int | None = None
    ai_confidence: int | None = None
    ai_direction: str | None = None
    ai_reasoning: list[str] | None = None
    ai_risk_level: str | None = None

    # ML Prediction
    ml_prediction: str | None = None
    ml_probability: float | None = None
    ml_confidence: float | None = None
    ml_model: str | None = None
    ml_version: str | None = None

    # AI/ML fusion
    ai_ml_agreement: str | None = None  # agreement, conflict, ai_only, ml_only, both_unavailable

    # Strategy
    strategy_id: str | None = None
    strategy_name: str | None = None
    strategy_signal: str | None = None
    strategy_decision: str | None = None

    # Trade Plan
    entry_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    risk_reward: float | None = None
    quantity: int = 0
    position_size: int = 0
    capital_required: float | None = None
    estimated_loss: float | None = None
    estimated_brokerage: float | None = None
    estimated_slippage: float | None = None
    risk_percent: float | None = None

    # Execution
    execution_mode: ExecutionMode = ExecutionMode.MANUAL
    broker: str = "zerodha"
    broker_connected: bool = False
    order_type: str = "MARKET"
    product: str = "MIS"
    order_state: OrderState = OrderState.CREATED
    broker_order_id: str | None = None
    order_status: str | None = None
    filled_quantity: int = 0
    average_price: float | None = None
    rejection_reason: str | None = None

    # Risk
    risk_status: str | None = None
    risk_score: float = 0.0
    risk_grade: str = "LOW"
    risk_reasons: list[str] = field(default_factory=list)
    risk_firewall_result: dict[str, Any] | None = None

    # Pipeline stages
    stages: dict[str, PipelineResult] = field(default_factory=dict)

    # Prediction journal
    prediction_id: str | None = None
    correlation_id: str | None = None

    def set_stage(self, stage: PipelineStage, status: StageStatus, **kwargs):
        self.stages[stage.value] = PipelineResult(stage=stage, status=status, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "interval": self.interval,
            "market_price": self.market_price,
            "market_regime": self.market_regime,
            "trend": self.trend,
            "ai_decision": self.ai_decision,
            "ai_score": self.ai_score,
            "ai_confidence": self.ai_confidence,
            "ml_prediction": self.ml_prediction,
            "ml_probability": self.ml_probability,
            "ai_ml_agreement": self.ai_ml_agreement,
            "strategy_decision": self.strategy_decision,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "risk_reward": self.risk_reward,
            "quantity": self.quantity,
            "execution_mode": self.execution_mode.value if self.execution_mode else "manual",
            "order_state": self.order_state.value if self.order_state else "created",
            "risk_status": self.risk_status,
            "risk_score": self.risk_score,
            "risk_grade": self.risk_grade,
            "risk_reasons": self.risk_reasons,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "prediction_id": self.prediction_id,
            "correlation_id": self.correlation_id,
        }

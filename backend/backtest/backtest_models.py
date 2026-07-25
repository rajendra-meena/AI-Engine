"""Backtest data models — config, state, result, and trade types."""

from __future__ import annotations

from dataclasses import dataclass, field
# from datetime import datetime
from enum import Enum
from typing import Any


class BacktestStatus(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    LOADING_DATA = "loading_data"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[BacktestStatus, list[BacktestStatus]] = {
    BacktestStatus.CREATED: [BacktestStatus.VALIDATING, BacktestStatus.CANCELLED],
    BacktestStatus.VALIDATING: [BacktestStatus.LOADING_DATA, BacktestStatus.FAILED, BacktestStatus.CANCELLED],
    BacktestStatus.LOADING_DATA: [BacktestStatus.READY, BacktestStatus.FAILED, BacktestStatus.CANCELLED],
    BacktestStatus.READY: [BacktestStatus.RUNNING, BacktestStatus.CANCELLED],
    BacktestStatus.RUNNING: [BacktestStatus.PAUSED, BacktestStatus.COMPLETED, BacktestStatus.FAILED],
    BacktestStatus.PAUSED: [BacktestStatus.RUNNING, BacktestStatus.CANCELLED],
    BacktestStatus.COMPLETED: [],
    BacktestStatus.FAILED: [],
    BacktestStatus.CANCELLED: [],
}


class ExecutionModel(str, Enum):
    NEXT_OPEN = "next_open"
    NEXT_CLOSE = "next_close"


class IntrabarRule(str, Enum):
    CONSERVATIVE = "conservative"
    OPTIMISTIC = "optimistic"
    SKIP_AMBIGUOUS = "skip_ambiguous"


class DataQualityStatus(str, Enum):
    GOOD = "good"
    WARNING = "warning"
    INVALID = "invalid"


SUPPORTED_TIMEFRAMES = ["1m", "2m", "3m", "5m", "10m", "15m", "30m", "60m"]


@dataclass
class BacktestConfig:
    backtest_id: str = ""
    name: str = ""
    symbol: str = "NIFTY 50"
    timeframe: str = "15m"
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 100000.0
    risk_per_trade_pct: float = 2.0
    max_positions: int = 1
    max_daily_loss: float = 0.0
    slippage_model: str = "none"
    slippage_value: float = 0.0
    brokerage_model: str = "none"
    brokerage_value: float = 0.0
    execution_model: str = "next_open"
    intrabar_rule: str = "conservative"
    end_of_test_rule: str = "force_close"
    enable_ai: bool = True
    enable_strategy: bool = True
    enable_risk: bool = True
    config_hash: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "backtest_id": self.backtest_id,
            "name": self.name,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "max_positions": self.max_positions,
            "slippage_model": self.slippage_model,
            "slippage_value": self.slippage_value,
            "brokerage_model": self.brokerage_model,
            "brokerage_value": self.brokerage_value,
            "execution_model": self.execution_model,
            "intrabar_rule": self.intrabar_rule,
            "end_of_test_rule": self.end_of_test_rule,
            "enable_ai": self.enable_ai,
            "enable_strategy": self.enable_strategy,
            "enable_risk": self.enable_risk,
            "created_at": self.created_at,
        }


@dataclass
class BacktestTrade:
    symbol: str = ""
    direction: str = "LONG"
    quantity: int = 0
    entry_price: float = 0.0
    entry_time: str = ""
    exit_price: float = 0.0
    exit_time: str = ""
    stop_loss: float | None = None
    target: float | None = None
    gross_pnl: float = 0.0
    brokerage: float = 0.0
    slippage_cost: float = 0.0
    net_pnl: float = 0.0
    r_multiple: float = 0.0
    mae: float = 0.0
    mfe: float = 0.0
    exit_reason: str = ""
    intrabar_ambiguity: bool = False
    ai_score: int = 0
    ai_confidence: int = 0
    strategy_score: int = 0
    regime: str = ""
    trace_id: str = ""
    decision_id: str = ""
    trade_plan_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "direction": self.direction,
            "quantity": self.quantity, "entry_price": self.entry_price,
            "entry_time": self.entry_time, "exit_price": self.exit_price,
            "exit_time": self.exit_time, "stop_loss": self.stop_loss,
            "target": self.target,
            "gross_pnl": round(self.gross_pnl, 2),
            "brokerage": round(self.brokerage, 2),
            "slippage_cost": round(self.slippage_cost, 2),
            "net_pnl": round(self.net_pnl, 2),
            "r_multiple": round(self.r_multiple, 2),
            "mae": round(self.mae, 2), "mfe": round(self.mfe, 2),
            "exit_reason": self.exit_reason,
            "intrabar_ambiguity": self.intrabar_ambiguity,
            "ai_score": self.ai_score, "ai_confidence": self.ai_confidence,
            "strategy_score": self.strategy_score, "regime": self.regime,
        }


@dataclass
class DataQualityReport:
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0
    missing_intervals: int = 0
    timestamp_gaps: int = 0
    invalid_ohlc_count: int = 0
    invalid_volume_count: int = 0
    first_timestamp: str = ""
    last_timestamp: str = ""
    coverage_pct: float = 0.0
    quality_status: str = "invalid"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows, "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows, "duplicate_rows": self.duplicate_rows,
            "missing_intervals": self.missing_intervals,
            "timestamp_gaps": self.timestamp_gaps,
            "invalid_ohlc_count": self.invalid_ohlc_count,
            "invalid_volume_count": self.invalid_volume_count,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "coverage_pct": round(self.coverage_pct, 1),
            "quality_status": self.quality_status,
        }


@dataclass
class BacktestMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_trade: float = 0.0
    avg_r: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consec_wins: int = 0
    consec_losses: int = 0
    max_drawdown_pct: float = 0.0
    total_brokerage: float = 0.0
    total_slippage: float = 0.0
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    blocked_trades: int = 0
    r_distribution: dict[str, int] = field(default_factory=lambda: {
        "ge_2r": 0, "ge_1r": 0, "ge_0r": 0, "lt_0r": 0, "lt_neg1r": 0,
    })
    sample_level: str = "insufficient_sample"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 1),
            "net_pnl": round(self.net_pnl, 2),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 2),
            "avg_trade": round(self.avg_trade, 2),
            "avg_r": round(self.avg_r, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "consec_wins": self.consec_wins,
            "consec_losses": self.consec_losses,
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "total_brokerage": round(self.total_brokerage, 2),
            "total_slippage": round(self.total_slippage, 2),
            "long_trades": self.long_trades,
            "short_trades": self.short_trades,
            "long_win_rate": round(self.long_win_rate, 1),
            "short_win_rate": round(self.short_win_rate, 1),
            "blocked_trades": self.blocked_trades,
            "r_distribution": self.r_distribution,
            "sample_level": self.sample_level,
        }


"""
BacktestRunner — Orchestrates the complete backtesting pipeline.

Pipeline:
    Config -> Validate -> Load Data -> Data Quality Check ->
    Initialize Isolated Environment -> Replay Candles ->
    Production Intelligence Pipeline -> AI Decision ->
    Strategy -> TradePlan -> Risk -> BacktestBroker ->
    SL/Target Monitor -> Close -> Metrics -> Result
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backtest.backtest_models import (
    BacktestConfig, BacktestStatus, BacktestMetrics, DataQualityReport,
)


def _new_id() -> str:
    return f"bt_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_level(count: int) -> str:
    if count < 20:
        return "insufficient_sample"
    if count < 50:
        return "low_confidence"
    if count < 100:
        return "moderate_sample"
    if count >= 250:
        return "strong"
    return "good"


class BacktestRunner:
    """Runs a complete backtest using the production pipeline."""

    def __init__(self):
        self._runs: dict[str, BacktestRun] = {}
        self._history: list[dict] = []

    def create_run(self, symbol="NIFTY 50", timeframe="15m", start_date="", end_date="",
                   initial_capital=100000.0, name="", **kwargs) -> str:
        run_id = _new_id()
        config = BacktestConfig(
            backtest_id=run_id,
            name=name or f"Backtest {symbol} {timeframe} {start_date}",
            symbol=symbol, timeframe=timeframe,
            start_date=start_date, end_date=end_date,
            initial_capital=initial_capital,
            risk_per_trade_pct=kwargs.get("risk_per_trade_pct", 2.0),
            max_positions=kwargs.get("max_positions", 1),
            slippage_model=kwargs.get("slippage_model", "none"),
            slippage_value=kwargs.get("slippage_value", 0.0),
            brokerage_model=kwargs.get("brokerage_model", "none"),
            brokerage_value=kwargs.get("brokerage_value", 0.0),
            execution_model=kwargs.get("execution_model", "next_open"),
            intrabar_rule=kwargs.get("intrabar_rule", "conservative"),
            end_of_test_rule=kwargs.get("end_of_test_rule", "force_close"),
            created_at=_now(),
        )
        run = BacktestRun(run_id=run_id, config=config)
        self._runs[run_id] = run
        return run_id

    def get_run(self, run_id: str):
        return self._runs.get(run_id)

    def get_all_runs(self):
        return list(self._runs.values())

    def delete_run(self, run_id: str) -> bool:
        if run_id in self._runs:
            del self._runs[run_id]
            return True
        return False


@dataclass
class BacktestRun:
    run_id: str = ""
    config: BacktestConfig | None = None
    status: BacktestStatus = BacktestStatus.CREATED
    data_quality: DataQualityReport | None = None
    metrics: BacktestMetrics | None = None
    error: str | None = None
    progress: float = 0.0
    processed_candles: int = 0
    total_candles: int = 0
    current_timestamp: str = ""
    trades: list = field(default_factory=list)
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value if self.status else "unknown",
            "progress": self.progress,
            "processed_candles": self.processed_candles,
            "total_candles": self.total_candles,
            "current_timestamp": self.current_timestamp,
            "error": self.error,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "data_quality": self.data_quality.to_dict() if self.data_quality else None,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

"""
Shadow Trade Model — virtual trade representing what the champion strategy
would have done if executed. Never touches Zerodha or PaperBroker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ShadowTrade:
    shadow_trade_id: str = ""
    strategy_version_id: str = ""
    decision_id: str = ""
    trade_plan_id: str = ""
    symbol: str = ""
    direction: str = "LONG"
    entry_price: float = 0.0
    stop_loss: float | None = None
    target: float | None = None
    quantity: int = 0
    risk_amount: float = 0.0
    risk_reward: float = 0.0
    entry_timestamp: str = ""
    exit_timestamp: str = ""
    exit_price: float | None = None
    exit_reason: str = ""
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    r_multiple: float = 0.0
    mae: float = 0.0
    mfe: float = 0.0
    ai_score: int = 0
    ai_confidence: int = 0
    market_regime: str = ""
    timeframe: str = "15m"
    data_freshness: str = "live"
    status: str = "pending"  # pending, open, closed, cancelled, invalidated

    def to_dict(self) -> dict[str, Any]:
        return {
            "shadow_trade_id": self.shadow_trade_id,
            "strategy_version_id": self.strategy_version_id,
            "decision_id": self.decision_id,
            "trade_plan_id": self.trade_plan_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "quantity": self.quantity,
            "risk_amount": round(self.risk_amount, 2),
            "risk_reward": round(self.risk_reward, 2),
            "entry_timestamp": self.entry_timestamp,
            "exit_timestamp": self.exit_timestamp,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "r_multiple": round(self.r_multiple, 2),
            "mae": round(self.mae, 2),
            "mfe": round(self.mfe, 2),
            "ai_score": self.ai_score,
            "ai_confidence": self.ai_confidence,
            "market_regime": self.market_regime,
            "timeframe": self.timeframe,
            "data_freshness": self.data_freshness,
            "status": self.status,
        }

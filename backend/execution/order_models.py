"""Order models with immutable identifiers and complete execution state."""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _new_uuid(prefix: str = "ord") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    BRACKET = "bracket"
    COVER = "cover"


class OrderValidity(str, Enum):
    DAY = "day"
    IOC = "ioc"
    GTC = "gtc"


@dataclass
class OrderIdentifier:
    """Immutable order identifiers — set once, never mutated."""
    internal_order_id: str = field(default_factory=lambda: _new_uuid("ord"))
    broker_order_id: str = ""
    client_order_id: str = ""
    correlation_id: str = field(default_factory=lambda: _new_uuid("cor"))

    def to_dict(self) -> dict[str, str]:
        return {
            "internal_order_id": self.internal_order_id,
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "correlation_id": self.correlation_id,
        }


@dataclass
class RiskSnapshot:
    """Snapshot of risk state at order creation time."""
    risk_approved: bool = False
    risk_blockers: list[str] = field(default_factory=list)
    approval_id: str = ""
    daily_loss_remaining: float = 0.0
    max_drawdown_remaining: float = 0.0
    current_exposure: float = 0.0
    portfolio_value: float = 0.0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_approved": self.risk_approved,
            "risk_blockers": self.risk_blockers,
            "approval_id": self.approval_id,
            "daily_loss_remaining": self.daily_loss_remaining,
            "max_drawdown_remaining": self.max_drawdown_remaining,
            "current_exposure": self.current_exposure,
            "portfolio_value": self.portfolio_value,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionOrder:
    """Complete order model with all execution fields. Immutable after creation."""
    # Identifiers
    internal_order_id: str = field(default_factory=lambda: _new_uuid("ord"))
    broker_order_id: str = ""
    client_order_id: str = ""
    correlation_id: str = field(default_factory=lambda: _new_uuid("cor"))

    # Market
    symbol: str = ""
    exchange: str = "NSE"
    side: str = "buy"
    order_type: str = "market"

    # Quantity and pricing
    quantity: int = 0
    price: float | None = None
    trigger_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    validity: str = "day"
    product: str = "MIS"

    # Strategy
    strategy_version: str = ""
    champion_version: str = ""
    signal_id: str = ""
    runtime_mode: str = ""

    # Risk
    risk_snapshot: RiskSnapshot = field(default_factory=RiskSnapshot)

    # Fill state
    state: str = "created"
    filled_quantity: int = 0
    average_fill_price: float | None = None
    rejection_reason: str = ""
    order_note: str = ""

    # Timestamps
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    # Metadata
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "internal_order_id": self.internal_order_id,
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "correlation_id": self.correlation_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "validity": self.validity,
            "product": self.product,
            "strategy_version": self.strategy_version,
            "champion_version": self.champion_version,
            "signal_id": self.signal_id,
            "runtime_mode": self.runtime_mode,
            "risk_snapshot": self.risk_snapshot.to_dict(),
            "state": self.state,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price,
            "rejection_reason": self.rejection_reason,
            "order_note": self.order_note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "meta": self.meta,
        }


@dataclass
class ExecutionReport:
    """Report from broker or simulator after order processing."""
    internal_order_id: str = ""
    broker_order_id: str = ""
    status: str = ""
    filled_quantity: int = 0
    average_price: float | None = None
    rejection_reason: str = ""
    latency_ms: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "internal_order_id": self.internal_order_id,
            "broker_order_id": self.broker_order_id,
            "status": self.status,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "rejection_reason": self.rejection_reason,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }

"""
Trade Lifecycle Manager — Central coordinator for trade state after orchestrator approval.

Manages:
- Order creation and broker submission
- Real-time order status tracking
- Partial fill accumulation
- Position management
- SL/Target monitoring
- Exit workflow
- Trade closure
- Learning outcome delivery
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from trading.lifecycle_events import (
    ORDER_CREATED,
    ORDER_SUBMITTED,
    ORDER_ACKNOWLEDGED,
    ORDER_PARTIAL_FILL,
    ORDER_FILLED,
    ORDER_REJECTED,
    ORDER_CANCELLED,
    TRADE_CREATED,
    POSITION_OPENED,
    POSITION_CLOSED,
    RECONCILIATION_WARNING,
    ZERODHA_STATUS_MAP,
)
from learning import integration as lri
from orchestrator.decision_context import DecisionContext
from utils.logger import log_info, log_warn, log_error
from core.event_bus import EventBus
from core.event_model import Event


def _new_id() -> str:
    return f"trd_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ManagedOrder:
    """Internal representation of a broker order with full lifecycle tracking."""
    internal_id: str = ""
    trade_id: str = ""
    trace_id: str = ""
    idempotency_key: str = ""
    broker_order_id: str = ""
    symbol: str = ""
    exchange: str = "NSE"
    transaction_type: str = "BUY"
    order_type: str = "MARKET"
    product: str = "MIS"
    quantity: int = 0
    filled_quantity: int = 0
    pending_quantity: int = 0
    price: float | None = None
    average_price: float | None = None
    trigger_price: float | None = None
    status: str = "created"
    rejection_reason: str | None = None
    created_at: str = ""
    updated_at: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "internal_id": self.internal_id,
            "trade_id": self.trade_id,
            "trace_id": self.trace_id,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "transaction_type": self.transaction_type,
            "order_type": self.order_type,
            "product": self.product,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "pending_quantity": self.pending_quantity,
            "price": self.price,
            "average_price": self.average_price,
            "trigger_price": self.trigger_price,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ManagedTrade:
    """Full trade lifecycle record."""
    id: str = ""
    trace_id: str = ""
    symbol: str = ""
    exchange: str = "NSE"
    direction: str = "LONG"
    status: str = "created"  # created, open, closed
    entry_price: float | None = None
    exit_price: float | None = None
    quantity: int = 0
    stop_loss: float | None = None
    target: float | None = None
    risk_reward: float | None = None
    pnl: float | None = None
    pnl_percent: float | None = None
    duration_minutes: int | None = None
    exit_reason: str | None = None
    strategy_id: str | None = None
    ai_decision: str | None = None
    ai_score: int | None = None
    ai_confidence: int | None = None
    ml_prediction: str | None = None
    ml_probability: float | None = None
    market_regime: str | None = None
    risk_score: float = 0.0
    risk_grade: str = "LOW"
    prediction_id: str | None = None
    entry_order: ManagedOrder | None = None
    exit_order: ManagedOrder | None = None
    created_at: str = ""
    opened_at: str | None = None
    closed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "direction": self.direction,
            "status": self.status,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "risk_reward": self.risk_reward,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "duration_minutes": self.duration_minutes,
            "exit_reason": self.exit_reason,
            "strategy_id": self.strategy_id,
            "ai_decision": self.ai_decision,
            "ai_score": self.ai_score,
            "ai_confidence": self.ai_confidence,
            "risk_score": self.risk_score,
            "risk_grade": self.risk_grade,
            "entry_order": self.entry_order.to_dict() if self.entry_order else None,
            "exit_order": self.exit_order.to_dict() if self.exit_order else None,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
        }


class TradeLifecycleManager:
    """
    Manages the complete trade lifecycle AFTER orchestrator approval.

    Flow:
        1. create_trade() - from approved DecisionContext
        2. submit_entry_order() - via broker
        3. handle_order_update() - from broker status changes
        4. open_position() - when entry fills
        5. submit_exit_order() - when SL/target/strategy triggers
        6. close_trade() - when exit fills
        7. deliver_to_learning() - send actual outcome
    """

    def __init__(self, kite_order_manager=None, event_bus: EventBus | None = None):
        self._kite_orders = kite_order_manager
        self._event_bus = event_bus
        self._trades: dict[str, ManagedTrade] = {}
        self._orders: dict[str, ManagedOrder] = {}
        self._broker_order_map: dict[str, str] = {}  # broker_order_id -> internal_id
        self._open_positions: dict[str, str] = {}  # symbol -> trade_id
        self._idempotency: dict[str, str] = {}  # key -> trade_id

    def set_kite_orders(self, km):
        self._kite_orders = km

    # ── Trade creation ──

    def create_trade(self, ctx: DecisionContext) -> ManagedTrade:
        """Create a new trade from an approved orchestrator decision."""
        trade_id = _new_id()
        id_key = ctx.correlation_id or trade_id

        # Idempotency: check if we already created a trade for this correlation
        if id_key in self._idempotency:
            existing_id = self._idempotency[id_key]
            log_info("TradeLifecycle: idempotent trade creation", trade_id=existing_id)
            return self._trades[existing_id]

        trade = ManagedTrade(
            id=trade_id,
            trace_id=ctx.trace_id,
            symbol=ctx.symbol,
            exchange=ctx.exchange,
            direction=ctx.ai_direction or "LONG",
            entry_price=ctx.entry_price or ctx.market_price,
            stop_loss=ctx.stop_loss,
            target=ctx.target,
            risk_reward=ctx.risk_reward,
            quantity=ctx.quantity,
            strategy_id=ctx.strategy_id,
            ai_decision=ctx.ai_decision,
            ai_score=ctx.ai_score,
            ai_confidence=ctx.ai_confidence,
            ml_prediction=ctx.ml_prediction,
            ml_probability=ctx.ml_probability,
            market_regime=ctx.market_regime,
            risk_score=ctx.risk_score,
            risk_grade=ctx.risk_grade,
            created_at=_now(),
        )
        self._trades[trade_id] = trade
        self._idempotency[id_key] = trade_id
        self._publish(TRADE_CREATED, trade.to_dict())
        log_info("TradeLifecycle: trade created", trade_id=trade_id, symbol=trade.symbol)
        return trade

    # ── Entry order submission ──

    def submit_entry_order(self, trade_id: str) -> ManagedOrder | None:
        """Submit the entry order to the broker."""
        trade = self._trades.get(trade_id)
        if not trade:
            log_error("TradeLifecycle: trade not found", trade_id=trade_id)
            return None

        order = ManagedOrder(
            internal_id=_new_id(),
            trade_id=trade_id,
            trace_id=trade.trace_id,
            symbol=trade.symbol,
            exchange=trade.exchange,
            transaction_type="BUY" if trade.direction == "LONG" else "SELL",
            order_type="MARKET",
            product="MIS",
            quantity=trade.quantity,
            price=trade.entry_price,
            status="submitting",
            created_at=_now(),
            updated_at=_now(),
        )
        self._orders[order.internal_id] = order
        self._publish(ORDER_CREATED, order.to_dict())

        if self._kite_orders and self._kite_orders.is_ready:
            try:
                result = self._kite_orders.place_order(
                    tradingsymbol=trade.symbol,
                    exchange=trade.exchange,
                    transaction_type=order.transaction_type,
                    quantity=order.quantity,
                    order_type=order.order_type,
                    price=order.price or 0,
                    product=order.product,
                    tag=trade.trace_id,
                )
                broker_id = result.get("order_id", "")
                if broker_id:
                    order.broker_order_id = broker_id
                    order.status = "acknowledged"
                    self._broker_order_map[broker_id] = order.internal_id
                    self._publish(ORDER_ACKNOWLEDGED, order.to_dict())
                    log_info("TradeLifecycle: order acknowledged", broker_id=broker_id, trade_id=trade_id)
                else:
                    order.status = "rejected"
                    order.rejection_reason = "Empty broker order_id"
                    self._publish(ORDER_REJECTED, order.to_dict())
            except Exception as e:
                order.status = "failed"
                order.rejection_reason = str(e)
                self._publish(ORDER_REJECTED, order.to_dict())
                log_error("TradeLifecycle: order submission failed", trade_id=trade_id, error=str(e))
        else:
            # Paper mode: simulate fill
            order.status = "filled"
            order.filled_quantity = order.quantity
            order.average_price = order.price or 0
            self._publish(ORDER_FILLED, order.to_dict())
            self._open_position(trade, order)

        order.updated_at = _now()
        return order

    # ── Order update handler ──

    def handle_order_update(self, broker_order_id: str, broker_status: str, **fields) -> ManagedOrder | None:
        """Handle an order update from broker (WebSocket or REST poll)."""
        internal_id = self._broker_order_map.get(broker_order_id)
        if not internal_id:
            log_warn("TradeLifecycle: unknown broker order", broker_id=broker_order_id)
            return None

        order = self._orders.get(internal_id)
        if not order:
            return None

        internal_status = ZERODHA_STATUS_MAP.get(broker_status, broker_status.lower())

        # Update fields
        filled_qty = fields.get("filled_quantity", fields.get("filledQty"))
        if filled_qty is not None:
            order.filled_quantity = int(filled_qty)
            order.pending_quantity = max(0, order.quantity - order.filled_quantity)

        avg_price = fields.get("average_price", fields.get("avgPrice"))
        if avg_price is not None:
            order.average_price = float(avg_price)

        if order.status != internal_status:
            order.status = internal_status
            if internal_status == "filled":
                self._publish(ORDER_FILLED, order.to_dict())
                self._open_position_for_order(order)
            elif internal_status == "partially_filled" or "partial" in broker_status.lower():
                self._publish(ORDER_PARTIAL_FILL, order.to_dict())
            elif internal_status == "rejected":
                order.rejection_reason = fields.get("rejection_reason", fields.get("statusMessage", ""))
                self._publish(ORDER_REJECTED, order.to_dict())
            elif internal_status == "cancelled":
                self._publish(ORDER_CANCELLED, order.to_dict())

        order.updated_at = _now()
        return order

    # ── Position management ──

    def _open_position(self, trade: ManagedTrade, order: ManagedOrder):
        """Open a position from a filled order."""
        trade.entry_order = order
        trade.entry_price = order.average_price or order.price or trade.entry_price
        trade.quantity = order.filled_quantity
        trade.status = "open"
        trade.opened_at = _now()
        self._open_positions[trade.symbol] = trade.id
        self._publish(POSITION_OPENED, trade.to_dict())
        log_info("TradeLifecycle: position opened", trade_id=trade.id, symbol=trade.symbol, qty=trade.quantity)

    def _open_position_for_order(self, order: ManagedOrder):
        """Open position when an order fills."""
        trade = self._trades.get(order.trade_id)
        if trade and trade.status != "open":
            self._open_position(trade, order)

    def get_open_position(self, symbol: str) -> ManagedTrade | None:
        """Get the open trade for a symbol."""
        trade_id = self._open_positions.get(symbol)
        if trade_id:
            return self._trades.get(trade_id)
        return None

    def update_position_price(self, symbol: str, current_price: float):
        """Update unrealized P&L for an open position."""
        trade_id = self._open_positions.get(symbol)
        if not trade_id:
            return
        trade = self._trades.get(trade_id)
        if not trade or trade.status != "open":
            return
        if trade.entry_price and trade.entry_price > 0:
            multiplier = 1 if trade.direction == "LONG" else -1
            trade.pnl = round((current_price - trade.entry_price) * trade.quantity * multiplier, 2)
            trade.pnl_percent = round(((current_price - trade.entry_price) / trade.entry_price) * 100 * multiplier, 2)

    # ── Exit ──

    def submit_exit_order(self, trade_id: str, reason: str = "manual") -> ManagedOrder | None:
        """Submit an exit order for an open trade."""
        trade = self._trades.get(trade_id)
        if not trade or trade.status != "open":
            st = trade.status if trade else "unknown"
            log_warn("TradeLifecycle: cannot exit non-open trade", trade_id=trade_id, status=st)
            return None

        # Idempotency: prevent duplicate exit
        if trade.exit_order is not None:
            log_info("TradeLifecycle: exit already submitted", trade_id=trade_id)
            return trade.exit_order

        exit_side = "SELL" if trade.direction == "LONG" else "BUY"
        exit_order = ManagedOrder(
            internal_id=_new_id(),
            trade_id=trade_id,
            trace_id=trade.trace_id,
            symbol=trade.symbol,
            exchange=trade.exchange,
            transaction_type=exit_side,
            order_type="MARKET",
            product="MIS",
            quantity=trade.quantity,
            status="submitting",
            created_at=_now(),
            updated_at=_now(),
            meta={"exit_reason": reason},
        )
        self._orders[exit_order.internal_id] = exit_order

        if self._kite_orders and self._kite_orders.is_ready:
            try:
                result = self._kite_orders.place_order(
                    tradingsymbol=trade.symbol,
                    exchange=trade.exchange,
                    transaction_type=exit_side,
                    quantity=trade.quantity,
                    order_type="MARKET",
                    product="MIS",
                    tag=f"EXIT_{trade.trace_id}",
                )
                broker_id = result.get("order_id", "")
                if broker_id:
                    exit_order.broker_order_id = broker_id
                    exit_order.status = "acknowledged"
                    self._broker_order_map[broker_id] = exit_order.internal_id
            except Exception as e:
                exit_order.status = "failed"
                exit_order.rejection_reason = str(e)

        # Paper mode: simulate exit
        if not self._kite_orders or not self._kite_orders.is_ready:
            exit_order.status = "filled"
            exit_order.filled_quantity = trade.quantity

        trade.exit_order = exit_order
        trade.exit_reason = reason
        exit_order.updated_at = _now()
        self._publish(ORDER_SUBMITTED, exit_order.to_dict())
        return exit_order

    def close_trade(self, trade_id: str, exit_price: float | None = None):
        """Close a trade (after exit fills)."""
        trade = self._trades.get(trade_id)
        if not trade:
            return

        if not exit_price and trade.exit_order and trade.exit_order.average_price:
            exit_price = trade.exit_order.average_price

        trade.exit_price = exit_price
        trade.status = "closed"
        trade.closed_at = _now()

        if trade.entry_price and exit_price:
            multiplier = 1 if trade.direction == "LONG" else -1
            trade.pnl = round((exit_price - trade.entry_price) * trade.quantity * multiplier, 2)
            trade.pnl_percent = round(((exit_price - trade.entry_price) / trade.entry_price) * 100 * multiplier, 2)

        # Calculate duration
        if trade.opened_at:
            try:
                opened = datetime.fromisoformat(trade.opened_at)
                closed = datetime.fromisoformat(trade.closed_at)
                trade.duration_minutes = int((closed - opened).total_seconds() / 60)
            except (ValueError, TypeError):
                pass

        self._open_positions.pop(trade.symbol, None)
        self._publish(POSITION_CLOSED, trade.to_dict())
        self._deliver_to_learning(trade)
        log_info("TradeLifecycle: trade closed", trade_id=trade_id, pnl=trade.pnl, reason=trade.exit_reason)

    # ── Learning integration ──

    def _deliver_to_learning(self, trade: ManagedTrade):
        """Deliver actual trade outcome to the learning engine."""
        try:
            if trade.prediction_id:
                lri.update_outcome_from_execution(
                    prediction_id=trade.prediction_id,
                    actual_return=trade.pnl_percent,
                    target_hit=trade.exit_reason == "target",
                    stop_loss_hit=trade.exit_reason == "stop_loss",
                    actual_direction=trade.direction,
                )
                lri.record_trade_feedback(
                    prediction_id=trade.prediction_id,
                    entry_price=trade.entry_price or 0,
                    exit_price=trade.exit_price,
                    quantity=trade.quantity,
                    direction=trade.direction,
                    gross_pnl=trade.pnl,
                    exit_reason=trade.exit_reason,
                )
                log_info("TradeLifecycle: learning updated", trade_id=trade.id)
        except Exception as e:
            log_warn("TradeLifecycle: learning update failed", trade_id=trade.id, error=str(e))

    # ── Reconciliation ──

    def reconcile_with_broker(self, broker_orders: list[dict], broker_positions: list[dict]) -> dict[str, Any]:
        """Compare broker state with internal state. Returns warnings."""
        warnings = []
        # Check for broker orders not in internal state
        for b_order in broker_orders:
            broker_id = b_order.get("order_id") or b_order.get("id", "")
            if broker_id and broker_id not in self._broker_order_map:
                warnings.append({
                    "type": "UNKNOWN_BROKER_ORDER",
                    "broker_order_id": broker_id,
                    "detail": f"Order {broker_id} exists at broker but not in internal state",
                })

        # Check for open positions at broker not tracked internally
        for b_pos in broker_positions:
            symbol = b_pos.get("tradingsymbol") or b_pos.get("symbol", "")
            net_qty = int(b_pos.get("net_quantity", b_pos.get("quantity", 0)))
            if net_qty != 0 and symbol not in self._open_positions:
                warnings.append({
                    "type": "ORPHAN_POSITION",
                    "symbol": symbol,
                    "quantity": net_qty,
                    "detail": f"Broker has open position in {symbol} ({net_qty}) not tracked internally",
                })

        if warnings:
            self._publish(RECONCILIATION_WARNING, {"warnings": warnings})

        return {
            "warnings": warnings,
            "warning_count": len(warnings),
            "internal_orders": len(self._orders),
            "internal_trades": len(self._trades),
            "internal_positions": len(self._open_positions),
        }

    # ── Restart recovery ──

    def recover_from_restart(self, broker_orders: list[dict], broker_positions: list[dict]):
        """Rebuild internal state from broker state after restart."""
        for b_pos in broker_positions:
            symbol = b_pos.get("tradingsymbol") or b_pos.get("symbol", "")
            net_qty = int(b_pos.get("net_quantity", b_pos.get("quantity", 0)))
            if net_qty == 0:
                continue

            trade_id = _new_id()
            direction = "LONG" if net_qty > 0 else "SHORT"
            trade = ManagedTrade(
                id=trade_id,
                symbol=symbol,
                exchange=b_pos.get("exchange", "NSE"),
                direction=direction,
                status="open",
                quantity=abs(net_qty),
                entry_price=float(b_pos.get("average_price", 0)),
                opened_at=_now(),
                created_at=_now(),
            )
            self._trades[trade_id] = trade
            self._open_positions[symbol] = trade_id
            log_info("TradeLifecycle: recovered position", symbol=symbol, qty=net_qty)

        for b_order in broker_orders:
            broker_id = b_order.get("order_id") or b_order.get("id", "")
            status = b_order.get("status", "")
            if not broker_id:
                continue
            internal_id = _new_id()
            order = ManagedOrder(
                internal_id=internal_id,
                broker_order_id=broker_id,
                symbol=b_order.get("tradingsymbol", ""),
                order_type=b_order.get("order_type", ""),
                quantity=int(b_order.get("quantity", 0)),
                filled_quantity=int(b_order.get("filled_quantity", 0)),
                status=ZERODHA_STATUS_MAP.get(status, status.lower()),
                created_at=_now(),
                updated_at=_now(),
            )
            self._orders[internal_id] = order
            self._broker_order_map[broker_id] = internal_id

        log_info("TradeLifecycle: recovery complete", trades=len(self._trades), orders=len(self._orders))

    # ── Queries ──

    def get_trade(self, trade_id: str) -> ManagedTrade | None:
        return self._trades.get(trade_id)

    def get_order(self, order_id: str) -> ManagedOrder | None:
        return self._orders.get(order_id)

    def get_order_by_broker_id(self, broker_id: str) -> ManagedOrder | None:
        internal_id = self._broker_order_map.get(broker_id)
        return self._orders.get(internal_id) if internal_id else None

    def get_all_trades(self, status: str | None = None) -> list[ManagedTrade]:
        trades = list(self._trades.values())
        if status:
            trades = [t for t in trades if t.status == status]
        return sorted(trades, key=lambda t: t.created_at or "", reverse=True)

    def get_all_orders(self, status: str | None = None) -> list[ManagedOrder]:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return sorted(orders, key=lambda o: o.created_at or "", reverse=True)

    def get_open_positions(self) -> list[ManagedTrade]:
        return [t for t in self._trades.values() if t.status == "open"]

    def get_trade_events(self, trade_id: str) -> list[dict[str, Any]]:
        trade = self._trades.get(trade_id)
        if not trade:
            return []
        events = []
        if trade.entry_order:
            events.extend(trade.entry_order.events)
        if trade.exit_order:
            events.extend(trade.exit_order.events)
        return events

    # ── Internal ──

    def _publish(self, event_type: str, data: dict[str, Any]):
        """Publish a lifecycle event via the Event Bus."""
        if not self._event_bus:
            return
        try:
            import asyncio
            event = Event(type=event_type, source="trade_lifecycle", payload=data)
            asyncio.ensure_future(self._event_bus.publish(event))
        except Exception as e:
            log_warn("TradeLifecycle: event publish failed", error=str(e))


# Singleton
_instance: TradeLifecycleManager | None = None


def get_lifecycle() -> TradeLifecycleManager:
    assert _instance is not None, "TradeLifecycleManager not initialized"
    return _instance


def init_lifecycle(kite_orders=None, event_bus=None) -> TradeLifecycleManager:
    global _instance
    _instance = TradeLifecycleManager(kite_orders, event_bus)
    return _instance

"""
Paper Broker — realistic paper trading engine using real market ticks.

Flow:
    ExecutionGateway → PaperBroker
        → Order acknowledged
        → TradeLifecycleManager
        → Real-time tick monitoring for SL/Target
        → Position management
        → P&L via PnLEngine
        → Learning feedback on close

Uses EXISTING:
    - MarketStreamManager (real ticks)
    - TradeLifecycleManager
    - PnLEngine
    - EventService
    - Learning Engine
"""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


from trading.trade_lifecycle import TradeLifecycleManager
from trading.pnl_engine import PnLEngine
from trading.event_service import LifecycleEventService
from models.tick import Tick
from utils.logger import log_info, log_warn, log_error


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"pp_{uuid.uuid4().hex[:12]}"


@dataclass
class PaperAccount:
    """Paper trading account state."""
    initial_capital: float = 100000.0
    available_cash: float = 100000.0
    used_margin: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_realized_pnl: float = 0.0
    total_pnl: float = 0.0
    open_positions: int = 0
    closed_trades: int = 0
    win_count: int = 0
    loss_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "available_cash": round(self.available_cash, 2),
            "used_margin": round(self.used_margin, 2),
            "equity": round(self.available_cash + self.total_unrealized_pnl, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "total_realized_pnl": round(self.total_realized_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "return_pct": self._return_pct(),
            "open_positions": self.open_positions,
            "closed_trades": self.closed_trades,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": self._win_rate(),
        }

    def _return_pct(self) -> float:
        if self.initial_capital > 0:
            return round((self.total_pnl / self.initial_capital) * 100, 2)
        return 0.0

    def _win_rate(self) -> float:
        total = self.closed_trades or 1
        return round((self.win_count / total) * 100, 1)


@dataclass
class PaperPosition:
    """Active paper trading position."""
    trade_id: str = ""
    symbol: str = ""
    direction: str = "LONG"
    quantity: int = 0
    entry_price: float = 0.0
    current_price: float = 0.0
    stop_loss: float | None = None
    target: float | None = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    created_at: str = ""
    exit_reason: str | None = None

    # Decision traceability
    decision_id: str = ""
    analysis_cycle_id: str = ""
    candle_version: str = ""
    strategy_version: str = "1.0"
    ai_direction: str = ""
    ai_confidence: float = 0.0
    opportunity_score: float = 0.0
    source_provider: str = ""
    instrument_token: int = 0
    data_timestamp: str = ""
    entry_reason: str = ""

    def to_dict(self, include_diagnostics: bool = False) -> dict[str, Any]:
        d = {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "created_at": self.created_at,
        }
        if include_diagnostics:
            d.update({
                "decision_id": self.decision_id,
                "analysis_cycle_id": self.analysis_cycle_id,
                "candle_version": self.candle_version,
                "strategy_version": self.strategy_version,
                "ai_direction": self.ai_direction,
                "ai_confidence": self.ai_confidence,
                "opportunity_score": self.opportunity_score,
                "source_provider": self.source_provider,
                "instrument_token": self.instrument_token,
                "data_timestamp": self.data_timestamp,
                "entry_reason": self.entry_reason,
            })
        return d


class PaperBroker:
    """
    Realistic paper broker using real market ticks for SL/Target monitoring.
    """

    def __init__(
        self,
        trade_lifecycle: TradeLifecycleManager | None = None,
        pnl_engine: PnLEngine | None = None,
        event_service: LifecycleEventService | None = None,
    ):
        self._trade_lifecycle = trade_lifecycle
        self._pnl_engine = pnl_engine
        self._event_service = event_service
        self._positions: dict[str, PaperPosition] = {}
        self._history: list[dict[str, Any]] = []
        self._orders: dict[str, dict[str, Any]] = {}
        self._account = PaperAccount()
        self._running = False
        self._paused = False

    def set_trade_lifecycle(self, tlc: TradeLifecycleManager):
        self._trade_lifecycle = tlc

    def set_pnl_engine(self, engine: PnLEngine):
        self._pnl_engine = engine

    def set_event_service(self, svc: LifecycleEventService):
        self._event_service = svc

    # ── Session control ──

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def start(self):
        self._running = True
        self._paused = False
        log_info("PaperBroker: started")

    def pause(self):
        self._paused = True
        log_info("PaperBroker: paused")

    def resume(self):
        self._paused = False
        log_info("PaperBroker: resumed")

    def stop(self):
        self._running = False
        self._paused = False
        log_info("PaperBroker: stopped")

    def reset(self):
        """Reset paper account. Does NOT affect production data."""
        self._positions.clear()
        self._history.clear()
        self._orders.clear()
        self._account = PaperAccount(self._account.initial_capital)
        if self._pnl_engine:
            self._pnl_engine.reset()
        log_info("PaperBroker: reset")

    # ── Order execution ──

    def execute(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float | None,
        stop_loss: float | None = None,
        target: float | None = None,
        trade_plan_id: str = "",
        trace_id: str = "",
        execution_id: str = "",
        # Decision traceability fields
        decision_id: str = "",
        analysis_cycle_id: str = "",
        candle_version: str = "",
        strategy_version: str = "",
        ai_direction: str = "",
        ai_confidence: float = 0.0,
        opportunity_score: float = 0.0,
        source_provider: str = "",
        instrument_token: int = 0,
        data_timestamp: str = "",
        entry_reason: str = "",
    ) -> dict[str, Any]:
        """Execute a paper order."""
        if not self._running or self._paused:
            return {"success": False, "status": "blocked", "reason": "Paper trading not running"}

        existing = self.get_position(symbol)
        if existing:
            expected_direction = "LONG" if side == "BUY" else "SHORT"
            if existing.direction == expected_direction:
                reason = f"Existing {existing.direction} position on {symbol}"
                return {"success": False, "status": "blocked", "reason": reason}
            else:
                reason = f"Opposite {existing.direction} position active on {symbol}, cannot {side}"
                return {"success": False, "status": "blocked", "reason": reason}

        entry = price or 0
        if entry <= 0:
            return {"success": False, "status": "rejected", "reason": "Invalid price"}

        cost = entry * quantity
        if cost > self._account.available_cash:
            return {"success": False, "status": "rejected", "reason": "Insufficient funds"}

        broker_order_id = f"paper_{_new_id()}"

        self._orders[broker_order_id] = {
            "id": broker_order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": entry,
            "status": "filled",
            "created_at": _now(),
            "filled_at": _now(),
            "execution_id": execution_id,
            "trade_plan_id": trade_plan_id,
            "trace_id": trace_id,
        }

        direction = "LONG" if side == "BUY" else "SHORT"
        trade_id = f"pt_{uuid.uuid4().hex[:12]}"
        position = PaperPosition(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry,
            current_price=entry,
            stop_loss=stop_loss,
            target=target,
            created_at=_now(),
            decision_id=decision_id,
            analysis_cycle_id=analysis_cycle_id,
            candle_version=candle_version,
            strategy_version=strategy_version or "1.0",
            ai_direction=ai_direction or side,
            ai_confidence=ai_confidence,
            opportunity_score=opportunity_score,
            source_provider=source_provider or "paper",
            instrument_token=instrument_token,
            data_timestamp=data_timestamp,
            entry_reason=entry_reason or side,
        )
        self._positions[trade_id] = position
        self._account.open_positions += 1
        self._account.used_margin += cost
        self._account.available_cash -= cost

        if self._trade_lifecycle:
            try:
                from orchestrator.decision_context import DecisionContext
                trade = self._trade_lifecycle.create_trade(
                    DecisionContext(
                        symbol=symbol, exchange="NSE", trace_id=trade_id,
                        ai_direction=side, entry_price=entry,
                        stop_loss=stop_loss, target=target, quantity=quantity,
                        correlation_id=execution_id or trade_plan_id,
                    )
                )
                self._trade_lifecycle.submit_entry_order(trade.id)
            except Exception as e:
                log_warn("PaperBroker: lifecycle feed failed", error=str(e))

        if self._pnl_engine:
            try:
                self._pnl_engine.update_position(symbol, direction, quantity, entry, entry)
            except Exception as e:
                log_warn("PaperBroker: P&L update failed", error=str(e))

        log_info("PaperBroker: position opened", symbol=symbol, direction=direction, qty=quantity, entry=entry)
        d = {"success": True, "broker_order_id": broker_order_id, "status": "filled", "price": entry}
        d["trade_id"] = trade_id
        return d

    # ── Real-time tick handler ──

    def on_tick(self, tick: Tick):
        """Process real market tick for SL/Target monitoring."""
        if not self._running or self._paused:
            return
        price = tick.price
        if price <= 0:
            return

        for pos in list(self._positions.values()):
            if pos.symbol != tick.symbol and pos.symbol != f"token:{tick.symbol}":
                continue

            pos.current_price = price
            if pos.direction == "LONG":
                pos.unrealized_pnl = (price - pos.entry_price) * pos.quantity
            else:
                pos.unrealized_pnl = (pos.entry_price - price) * pos.quantity

            if self._pnl_engine:
                try:
                    self._pnl_engine.update_price(pos.symbol, price)
                except Exception as e:
                    log_warn("PaperBroker: P&L price update failed",
                             symbol=pos.symbol, error=str(e))

            # Check SL
            if pos.stop_loss is not None:
                at_sl = (pos.direction == "LONG" and price <= pos.stop_loss) or \
                        (pos.direction == "SHORT" and price >= pos.stop_loss)
                if at_sl:
                    self._close_position(pos.trade_id, pos.stop_loss, "stop_loss")
                    continue

            # Check Target
            if pos.target is not None:
                at_target = (pos.direction == "LONG" and price >= pos.target) or \
                            (pos.direction == "SHORT" and price <= pos.target)
                if at_target:
                    self._close_position(pos.trade_id, pos.target, "target")

    # ── Position management ──

    def _close_position(self, trade_id: str, exit_price: float, reason: str):
        pos = self._positions.pop(trade_id, None)
        if not pos:
            return

        if pos.direction == "LONG":
            realized = (exit_price - pos.entry_price) * pos.quantity
        else:
            realized = (pos.entry_price - exit_price) * pos.quantity

        pos.realized_pnl = realized
        pos.exit_reason = reason
        self._account.open_positions -= 1
        self._account.closed_trades += 1
        self._account.total_realized_pnl += realized
        self._account.total_pnl = self._account.total_realized_pnl + self._account.total_unrealized_pnl

        margin_freed = pos.entry_price * pos.quantity
        self._account.available_cash += margin_freed + realized
        self._account.used_margin -= margin_freed

        if realized > 0:
            self._account.win_count += 1
        else:
            self._account.loss_count += 1

        if self._pnl_engine:
            try:
                self._pnl_engine.remove_position(pos.symbol)
                self._pnl_engine.add_realized_pnl(realized)
            except Exception as e:
                log_error("PaperBroker: P&L close update failed",
                          symbol=pos.symbol, trade_id=trade_id, pnl=realized, error=str(e))

        if self._trade_lifecycle:
            try:
                self._trade_lifecycle.close_trade(trade_id, exit_price)
            except Exception as e:
                log_error("PaperBroker: lifecycle close failed",
                          symbol=pos.symbol, trade_id=trade_id, error=str(e))

        record = pos.to_dict()
        record["exit_price"] = exit_price
        record["exit_reason"] = reason
        record["realized_pnl"] = round(realized, 2)
        record["closed_at"] = _now()
        self._history.append(record)

        log_info("PaperBroker: position closed", symbol=pos.symbol, reason=reason, pnl=round(realized, 2))

    def close_position(self, trade_id: str, reason: str = "manual") -> bool:
        pos = self._positions.get(trade_id)
        if not pos:
            return False
        self._close_position(trade_id, pos.current_price, reason)
        return True

    # ── Queries ──

    def get_position(self, symbol: str) -> PaperPosition | None:
        for pos in self._positions.values():
            if pos.symbol == symbol:
                return pos
        return None

    def get_positions(self) -> list[PaperPosition]:
        return list(self._positions.values())

    def get_account(self) -> PaperAccount:
        self._account.total_unrealized_pnl = sum(p.unrealized_pnl for p in self._positions.values())
        self._account.total_pnl = self._account.total_realized_pnl + self._account.total_unrealized_pnl
        return self._account

    def get_orders(self) -> list[dict[str, Any]]:
        return list(self._orders.values())

    def get_trades(self) -> list[dict[str, Any]]:
        return list(self._history)

    def get_events(self) -> list[dict[str, Any]]:
        events = []
        for t in self._history[-50:]:
            events.append({
                "type": "paper_trade_closed",
                "symbol": t.get("symbol"),
                "pnl": t.get("realized_pnl"),
                "reason": t.get("exit_reason"),
                "timestamp": t.get("closed_at"),
            })
        return events


# Singleton
_instance: PaperBroker | None = None


def get_paper_broker() -> PaperBroker:
    assert _instance is not None, "PaperBroker not initialized"
    return _instance


def init_paper_broker(
    trade_lifecycle=None, pnl_engine=None, event_service=None
) -> PaperBroker:
    global _instance
    _instance = PaperBroker(trade_lifecycle, pnl_engine, event_service)
    return _instance

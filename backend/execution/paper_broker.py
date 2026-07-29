"""
Paper Broker — realistic paper trading engine using real market ticks.

Phase 2D additions:
- Premium tick routing via instrument_token
- Premium SL/Target automatic exits
- Premium data freshness (LIVE/STALE/DISCONNECTED)
- SQLite persistence for positions, trades, events
- Restart recovery from persisted state
- Market-close forced exit
- Paper account reconciliation
"""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


from trading.trade_lifecycle import TradeLifecycleManager
from trading.pnl_engine import PnLEngine
from trading.event_service import LifecycleEventService
from models.tick import Tick
from utils.logger import log_info, log_warn, log_error


# ── Constants ──

PREMIUM_STALE_SECONDS = 10
PREMIUM_DISCONNECTED_SECONDS = 60
EXIT_STOP_LOSS_HIT = "STOP_LOSS_HIT"
EXIT_TARGET_HIT = "TARGET_HIT"
EXIT_MANUAL = "MANUAL_EXIT"
EXIT_MARKET_CLOSE = "MARKET_CLOSE_EXIT"
EXIT_KILL_SWITCH = "KILL_SWITCH_EXIT"
EXIT_DATA_SAFETY = "DATA_SAFETY_EXIT"
EXIT_ERROR = "ERROR_EXIT"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"pp_{uuid.uuid4().hex[:12]}"


# ── Exit Statuses ──

EXIT_STATUSES = {
    EXIT_STOP_LOSS_HIT,
    EXIT_TARGET_HIT,
    EXIT_MANUAL,
    EXIT_MARKET_CLOSE,
    EXIT_KILL_SWITCH,
    EXIT_DATA_SAFETY,
    EXIT_ERROR,
}


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


# ── Premium Data Status ──

PREMIUM_STATUS_LIVE = "LIVE"
PREMIUM_STATUS_STALE = "STALE"
PREMIUM_STATUS_DISCONNECTED = "DISCONNECTED"
PREMIUM_STATUS_WAITING = "WAITING_FOR_FIRST_TICK"
PREMIUM_STATUS_ERROR = "ERROR"


@dataclass
class PaperPosition:
    """Active paper trading position with premium monitoring."""
    trade_id: str = ""
    symbol: str = ""
    execution_symbol: str = ""
    direction: str = "LONG"
    quantity: int = 0
    entry_price: float = 0.0
    current_price: float = 0.0
    stop_loss: float | None = None
    target: float | None = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    pnl_percent: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    exit_reason: str | None = None
    exit_price: float | None = None

    # Decision traceability
    decision_id: str = ""
    analysis_cycle_id: str = ""
    candle_version: str = ""
    strategy_version: str = "1.0"
    ai_direction: str = ""
    ai_confidence: float = 0.0
    opportunity_score: float = 0.0
    trade_grade: str = ""
    source_provider: str = ""
    instrument_token: int = 0
    data_timestamp: str = ""
    entry_reason: str = ""

    # Execution model fields
    execution_type: str = "synthetic_spot"
    underlying_symbol: str | None = None
    exchange: str = "NSE"
    option_type: str | None = None
    expiry: str | None = None
    strike: float | None = None
    premium_entry: float | None = None
    premium_current: float | None = None
    premium_stop_loss: float | None = None
    premium_target: float | None = None
    lot_size: int | None = None
    lots: int | None = None
    underlying_entry: float | None = None
    underlying_current: float | None = None
    underlying_stop_loss: float | None = None
    underlying_target: float | None = None
    risk_reward: float | None = None
    premium_source: str = ""
    test_origin: str = ""
    source_provenance: str = ""
    settings_snapshot: dict | None = None
    risk_snapshot: dict | None = None

    # Phase 2D: Premium monitoring fields
    premium_instrument_token: int = 0
    premium_data_status: str = PREMIUM_STATUS_WAITING
    last_premium_tick_at: str = ""
    premium_tick_age_ms: float = 0.0

    # Internal: track last premium for SL/target one-shot
    _sl_hit: bool = False
    _target_hit: bool = False

    def _premium_pnl(self, current_premium: float | None = None) -> float:
        """Calculate unrealized P&L for a bought option.
        CE (Long Call) and PE (Long Put): (current_premium - premium_entry) * quantity
        """
        if self.premium_entry is None:
            return 0.0
        cp = current_premium if current_premium is not None else self.premium_current
        if cp is None:
            return 0.0
        return (cp - self.premium_entry) * self.quantity

    def update_premium(self, premium: float, timestamp: str | None = None) -> dict[str, Any]:
        """
        Update position with a live option premium tick.

        Returns dict with {updated, sl_hit, target_hit, pnl} or None if no change.
        """
        ts = timestamp or _now()
        if premium <= 0:
            return {"updated": False, "reason": "invalid_premium"}

        self.premium_current = premium
        self.current_price = premium
        self.premium_data_status = PREMIUM_STATUS_LIVE
        self.last_premium_tick_at = ts
        self.updated_at = ts

        # Update premium tick age
        try:
            tick_dt = datetime.fromisoformat(ts)
            now_dt = datetime.now(timezone.utc)
            self.premium_tick_age_ms = (now_dt - tick_dt).total_seconds() * 1000
        except Exception:
            self.premium_tick_age_ms = 0.0

        # P&L — premium-based for bought options CE and PE
        pnl = self._premium_pnl(premium)
        self.unrealized_pnl = pnl
        self.pnl_percent = round((pnl / (self.premium_entry * self.quantity)) * 100, 2) if self.premium_entry and self.quantity else 0.0

        result: dict[str, Any] = {
            "updated": True,
            "premium": premium,
            "unrealized_pnl": pnl,
            "pnl_percent": self.pnl_percent,
            "sl_hit": False,
            "target_hit": False,
        }

        # SL check (one-shot)
        if self.premium_stop_loss is not None and not self._sl_hit and not self._target_hit:
            if premium <= self.premium_stop_loss:
                self._sl_hit = True
                result["sl_hit"] = True

        # Target check (one-shot)
        if self.premium_target is not None and not self._target_hit and not self._sl_hit:
            if premium >= self.premium_target:
                self._target_hit = True
                result["target_hit"] = True

        return result

    def check_stale(self) -> str:
        """Check premium data freshness. Returns status string."""
        if self.premium_data_status == PREMIUM_STATUS_WAITING:
            return PREMIUM_STATUS_WAITING
        if not self.last_premium_tick_at:
            return PREMIUM_STATUS_WAITING
        try:
            last = datetime.fromisoformat(self.last_premium_tick_at)
            age = (datetime.now(timezone.utc) - last).total_seconds()
            if age > PREMIUM_DISCONNECTED_SECONDS:
                return PREMIUM_STATUS_DISCONNECTED
            if age > PREMIUM_STALE_SECONDS:
                return PREMIUM_STATUS_STALE
            return PREMIUM_STATUS_LIVE
        except Exception:
            return PREMIUM_STATUS_ERROR

    def to_dict(self, include_diagnostics: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "trade_id": self.trade_id,
            "execution_symbol": self.execution_symbol,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 2) if self.entry_price else 0,
            "current_price": round(self.current_price, 2) if self.current_price else 0,
            "stop_loss": round(self.stop_loss, 2) if self.stop_loss else None,
            "target": round(self.target, 2) if self.target else None,
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "pnl_percent": round(self.pnl_percent, 2),
            "created_at": self.created_at,
            "updated_at": self.updated_at or self.created_at,
            "entry_time": self.created_at,
            "status": "OPEN" if self.exit_reason is None else "CLOSED",
            "execution_type": self.execution_type,
            "symbol": self.underlying_symbol or self.symbol,
            "exchange": self.exchange,
            # Phase 2D premium fields
            "premium_entry": round(self.premium_entry, 2) if self.premium_entry else None,
            "premium_current": round(self.premium_current, 2) if self.premium_current else None,
            "premium_stop_loss": round(self.premium_stop_loss, 2) if self.premium_stop_loss else None,
            "premium_target": round(self.premium_target, 2) if self.premium_target else None,
            "last_premium_tick_at": self.last_premium_tick_at or "",
            "premium_tick_age_ms": round(self.premium_tick_age_ms, 0),
            "premium_data_status": self.premium_data_status,
            "premium_instrument_token": self.premium_instrument_token,
            "premium_source": self.premium_source,
        }
        if self.execution_type == "option_buying":
            d.update({
                "option_type": self.option_type,
                "strike": self.strike,
                "expiry": self.expiry,
                "lot_size": self.lot_size,
                "lots": self.lots,
                "underlying_symbol": self.underlying_symbol,
                "underlying_entry": round(self.underlying_entry, 2) if self.underlying_entry else None,
                "underlying_current": round(self.underlying_current, 2) if self.underlying_current else None,
                "risk_reward": round(self.risk_reward, 2) if self.risk_reward else None,
            })
        if include_diagnostics:
            d.update({
                "decision_id": self.decision_id,
                "analysis_cycle_id": self.analysis_cycle_id,
                "candle_version": self.candle_version,
                "strategy_version": self.strategy_version,
                "ai_direction": self.ai_direction,
                "ai_confidence": self.ai_confidence,
                "opportunity_score": self.opportunity_score,
                "trade_grade": self.trade_grade,
                "source_provider": self.source_provider,
                "instrument_token": self.instrument_token,
                "data_timestamp": self.data_timestamp,
                "entry_reason": self.entry_reason,
                "test_origin": self.test_origin,
                "source_provenance": self.source_provenance,
            })
        return d

    def to_persistence_dict(self) -> dict[str, Any]:
        """Return dict suitable for DB persistence."""
        d = self.to_dict(include_diagnostics=True)
        d["current_premium"] = self.premium_current or 0.0
        d["underlying_current"] = self.underlying_current
        d["status"] = "OPEN" if self.exit_reason is None else "CLOSED"
        return d


@dataclass
class BlockedAttempt:
    """Record of a blocked execution attempt with exact reason."""
    attempt_id: str = ""
    timestamp: str = ""
    underlying_symbol: str = ""
    direction: str = ""
    analysis_cycle_id: str = ""
    stage: str = ""
    block_code: str = ""
    block_reason: str = ""
    actual_value: str = ""
    required_value: str = ""
    settings_snapshot: dict[str, Any] | None = None
    risk_snapshot: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "timestamp": self.timestamp,
            "underlying_symbol": self.underlying_symbol,
            "direction": self.direction,
            "analysis_cycle_id": self.analysis_cycle_id,
            "stage": self.stage,
            "block_code": self.block_code,
            "block_reason": self.block_reason,
            "actual_value": self.actual_value,
            "required_value": self.required_value,
            "settings_snapshot": self.settings_snapshot,
            "risk_snapshot": self.risk_snapshot,
        }


class PaperBroker:
    """
    Realistic paper broker using real market ticks for SL/Target monitoring.
    Phase 2D: premium ticks by instrument_token, SL/target on premium,
    persistence, restart recovery, market-close exit.
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
        self._blocked_attempts: list[BlockedAttempt] = []
        self._max_blocked_attempts = 50

        # Phase 2D: premium tick router integration
        self._premium_router = None
        # Phase 2D: persistence
        self._db_service = None
        # Phase 2D: max favorable/adverse tracking
        self._max_favorable: dict[str, float] = {}
        self._max_adverse: dict[str, float] = {}
        # Phase 2D: market-close exit tracking
        self._market_close_exit_done = False

    def set_trade_lifecycle(self, tlc: TradeLifecycleManager):
        self._trade_lifecycle = tlc

    def set_pnl_engine(self, engine: PnLEngine):
        self._pnl_engine = engine

    def set_event_service(self, svc: LifecycleEventService):
        self._event_service = svc

    def set_premium_router(self, router):
        """Set the PremiumTickRouter for option tick routing."""
        self._premium_router = router

    def set_db_service(self, db_svc):
        """Set the paper trading DB service for persistence."""
        self._db_service = db_svc

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
        self._blocked_attempts.clear()
        self._max_favorable.clear()
        self._max_adverse.clear()
        self._market_close_exit_done = False
        self._account = PaperAccount(self._account.initial_capital)
        if self._premium_router:
            self._premium_router.reset()
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
        trade_grade: str = "",
        source_provider: str = "",
        instrument_token: int = 0,
        data_timestamp: str = "",
        entry_reason: str = "",
        # Execution model fields
        execution_type: str = "synthetic_spot",
        option_type: str | None = None,
        option_strike: float | None = None,
        option_expiry: str | None = None,
        option_premium: float | None = None,
        option_lot_size: int | None = None,
        option_lots: int | None = None,
        underlying_symbol: str | None = None,
        underlying_entry_price: float | None = None,
        # Enhanced option fields
        premium_entry: float | None = None,
        premium_stop_loss: float | None = None,
        premium_target: float | None = None,
        strike: float | None = None,
        expiry: str | None = None,
        lot_size: int | None = None,
        lots: int | None = None,
        underlying_stop_loss: float | None = None,
        underlying_target: float | None = None,
        risk_reward: float | None = None,
        premium_source: str = "",
        execution_symbol: str = "",
        exchange: str = "NSE",
        test_origin: str = "",
        # Phase 2D fields
        premium_instrument_token: int = 0,
        source_provenance: str = "",
        settings_snapshot: dict | None = None,
        risk_snapshot: dict | None = None,
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
        now_ts = _now()

        # Determine premium fields
        pe = premium_entry if premium_entry is not None else option_premium
        psl = premium_stop_loss or stop_loss
        pt = premium_target or target
        ls = lot_size or option_lot_size or 0
        l = lots or option_lots or 1
        st = strike or option_strike
        ex = expiry or option_expiry

        position = PaperPosition(
            trade_id=trade_id,
            symbol=symbol,
            execution_symbol=execution_symbol or symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry,
            current_price=entry,
            stop_loss=psl,
            target=pt,
            created_at=now_ts,
            updated_at=now_ts,
            decision_id=decision_id,
            analysis_cycle_id=analysis_cycle_id,
            candle_version=candle_version,
            strategy_version=strategy_version or "1.0",
            ai_direction=ai_direction or side,
            ai_confidence=ai_confidence,
            opportunity_score=opportunity_score,
            trade_grade=trade_grade,
            source_provider=source_provider or "paper",
            instrument_token=instrument_token,
            data_timestamp=data_timestamp,
            entry_reason=entry_reason or side,
            execution_type=execution_type,
            underlying_symbol=underlying_symbol or symbol,
            exchange=exchange,
            option_type=option_type,
            expiry=ex,
            strike=st,
            premium_entry=pe,
            premium_current=pe,
            premium_stop_loss=psl,
            premium_target=pt,
            lot_size=ls,
            lots=l,
            underlying_entry=underlying_entry_price,
            underlying_stop_loss=underlying_stop_loss,
            underlying_target=underlying_target,
            risk_reward=risk_reward,
            premium_source=premium_source,
            test_origin=test_origin,
            # Phase 2D
            premium_instrument_token=premium_instrument_token or instrument_token,
            premium_data_status=PREMIUM_STATUS_WAITING,
            source_provenance=source_provenance,
            settings_snapshot=settings_snapshot,
            risk_snapshot=risk_snapshot,
        )
        self._positions[trade_id] = position
        self._account.open_positions += 1
        self._account.used_margin += cost
        self._account.available_cash -= cost

        # Persist to DB
        self._persist_position(position)

        # Register with premium tick router
        token = premium_instrument_token or instrument_token
        if token > 0 and self._premium_router:
            needs_sub = self._premium_router.register_position(trade_id, token)
            log_info("PaperBroker: premium token registered",
                     trade_id=trade_id, token=token,
                     needs_subscription=needs_sub)
            self._record_position_event(trade_id, "OPTION_SUBSCRIBED",
                                        {"premium": pe, "token": token})

        # Record event
        self._record_position_event(trade_id, "PAPER_POSITION_CREATED",
                                    {"premium": pe, "lots": l, "lot_size": ls})

        # Feed lifecycle
        if self._trade_lifecycle:
            try:
                from orchestrator.decision_context import DecisionContext
                trade = self._trade_lifecycle.create_trade(
                    DecisionContext(
                        symbol=symbol, exchange="NSE", trace_id=trade_id,
                        ai_direction=side, entry_price=entry,
                        stop_loss=psl, target=pt, quantity=quantity,
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

        # Track max favorable/adverse
        self._max_favorable[trade_id] = 0.0
        self._max_adverse[trade_id] = 0.0

        log_info("PaperBroker: position opened",
                 symbol=symbol, direction=direction, qty=quantity, entry=entry)
        d = {"success": True, "broker_order_id": broker_order_id, "status": "filled", "price": entry}
        d["trade_id"] = trade_id
        return d

    # ── Premium Tick Handler ──

    def on_premium_tick(self, trade_id: str, premium: float, instrument_token: int, timestamp: str | None = None):
        """
        Process an option premium tick for a specific position.
        Called by PremiumTickRouter.
        """
        pos = self._positions.get(trade_id)
        if not pos:
            return

        if pos.exit_reason is not None:
            return  # Already closed

        ts = timestamp or _now()
        result = pos.update_premium(premium, ts)

        if not result.get("updated"):
            return

        # Track max favorable/adverse
        pnl = result.get("unrealized_pnl", 0.0)
        if pnl > self._max_favorable.get(trade_id, 0.0):
            self._max_favorable[trade_id] = pnl
        if pnl < self._max_adverse.get(trade_id, 0.0):
            self._max_adverse[trade_id] = pnl

        # Persist premium update
        self._persist_position_update(trade_id, {
            "premium_current": premium,
            "current_premium": premium,
            "premium_data_status": PREMIUM_STATUS_LIVE,
            "last_premium_tick_at": ts,
            "updated_at": ts,
            "unrealized_pnl": round(pnl, 2),
        })

        # Record event periodically (not on every tick to avoid DB spam)
        # Only record when status changes or at significant thresholds
        self._record_position_event(trade_id, "PREMIUM_UPDATED",
                                    {"premium": premium, "pnl": round(pnl, 2)})

        # Check SL
        if result.get("sl_hit"):
            log_info("PaperBroker: stop loss hit",
                     trade_id=trade_id, premium=premium,
                     sl=pos.premium_stop_loss)
            self._close_position(trade_id, premium, EXIT_STOP_LOSS_HIT)
            return

        # Check Target
        if result.get("target_hit"):
            log_info("PaperBroker: target hit",
                     trade_id=trade_id, premium=premium,
                     target=pos.premium_target)
            self._close_position(trade_id, premium, EXIT_TARGET_HIT)

    # ── Real-time underlying tick handler ──

    def on_tick(self, tick: Tick):
        """Process real market tick for underlying price tracking and
        synthetic_spot SL/Target monitoring.

        Option premium SL/Target is handled by on_premium_tick — NOT here.
        """
        if not self._running or self._paused:
            return
        price = tick.price
        if price <= 0:
            return

        for pos in list(self._positions.values()):
            if pos.symbol != tick.symbol and pos.symbol != f"token:{tick.symbol}":
                continue

            # For option_buying: only update underlying_current
            if pos.execution_type == "option_buying":
                pos.underlying_current = price
                continue

            # For synthetic_spot: full price/P&L/SL/target lifecycle
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
        """Internal close — calculates realized P&L, persists, cleans up."""
        pos = self._positions.pop(trade_id, None)
        if not pos:
            return

        if pos.exit_reason is not None:
            return  # Already closed — idempotent

        # Calculate realized P&L: (exit_premium - premium_entry) * quantity
        pe = pos.premium_entry or pos.entry_price
        realized = (exit_price - pe) * pos.quantity

        pos.realized_pnl = realized
        pos.exit_reason = reason
        pos.exit_price = exit_price
        pos.updated_at = _now()
        pos.premium_current = exit_price

        self._account.open_positions -= 1
        self._account.closed_trades += 1
        self._account.total_realized_pnl += realized
        self._account.total_pnl = self._account.total_realized_pnl + self._account.total_unrealized_pnl

        # Release capital: entry_price * quantity (used margin) + P&L
        margin_freed = pos.entry_price * pos.quantity
        self._account.available_cash += margin_freed + realized
        self._account.used_margin -= margin_freed

        if realized > 0:
            self._account.win_count += 1
        else:
            self._account.loss_count += 1

        # Build duration
        duration = 0
        try:
            entry_dt = datetime.fromisoformat(pos.created_at)
            exit_dt = datetime.fromisoformat(pos.updated_at)
            duration = int((exit_dt - entry_dt).total_seconds())
        except Exception:
            pass

        # Record close event
        self._record_position_event(trade_id, "POSITION_CLOSED", {
            "exit_price": exit_price,
            "reason": reason,
            "realized_pnl": round(realized, 2),
        })
        self._record_position_event(trade_id, "TRADE_PERSISTED", {
            "realized_pnl": round(realized, 2),
        })

        # Build trade record
        record = pos.to_dict(include_diagnostics=True)
        record["exit_price"] = exit_price
        record["exit_reason"] = reason
        record["realized_pnl"] = round(realized, 2)
        record["closed_at"] = _now()
        record["exit_premium"] = exit_price
        record["premium_exit"] = exit_price
        record["pnl_percent"] = round((realized / (pe * pos.quantity)) * 100, 2) if pe and pos.quantity else 0.0
        record["duration_seconds"] = duration
        record["max_favorable"] = round(self._max_favorable.get(trade_id, 0.0), 2)
        record["max_adverse"] = round(self._max_adverse.get(trade_id, 0.0), 2)
        self._history.append(record)

        # Persist to DB
        self._persist_closed_trade(record)

        # Delete open position from DB
        self._delete_persisted_position(trade_id)

        # Unregister from premium tick router
        if self._premium_router and pos.premium_instrument_token > 0:
            token_to_unsub = self._premium_router.unregister_position(trade_id)
            if token_to_unsub:
                log_info("PaperBroker: token unsubscribed",
                         trade_id=trade_id, token=token_to_unsub)

        # Clean up tracking
        self._max_favorable.pop(trade_id, None)
        self._max_adverse.pop(trade_id, None)

        # PnL engine cleanup
        if self._pnl_engine:
            try:
                self._pnl_engine.remove_position(pos.symbol)
                self._pnl_engine.add_realized_pnl(realized)
            except Exception as e:
                log_error("PaperBroker: P&L close update failed",
                          symbol=pos.symbol, trade_id=trade_id, pnl=realized, error=str(e))

        # Trade lifecycle
        if self._trade_lifecycle:
            try:
                self._trade_lifecycle.close_trade(trade_id, exit_price)
            except Exception as e:
                log_error("PaperBroker: lifecycle close failed",
                          symbol=pos.symbol, trade_id=trade_id, error=str(e))

        log_info("PaperBroker: position closed",
                 symbol=pos.symbol, reason=reason, pnl=round(realized, 2))

    def close_position(self, trade_id: str, reason: str = EXIT_MANUAL) -> bool:
        """Close a position manually. Returns True if closed."""
        pos = self._positions.get(trade_id)
        if not pos:
            return False
        if pos.exit_reason is not None:
            return False  # Already closed — idempotent

        # Use current premium as exit price
        exit_price = pos.premium_current or pos.current_price
        self._close_position(trade_id, exit_price, reason)
        return True

    def force_market_close_exit(self):
        """Force-close all open positions at current premium (market close)."""
        if self._market_close_exit_done:
            return
        trade_ids = list(self._positions.keys())
        if not trade_ids:
            self._market_close_exit_done = True
            return

        log_info("PaperBroker: force market close exit",
                 positions_count=len(trade_ids))

        for trade_id in trade_ids:
            pos = self._positions.get(trade_id)
            if not pos or pos.exit_reason is not None:
                continue

            exit_price = pos.premium_current or pos.current_price
            emergency_reason = ""
            exit_source = "current_premium"

            # Check premium freshness
            status = pos.check_stale()
            if status != PREMIUM_STATUS_LIVE:
                exit_price = pos.premium_entry or pos.entry_price
                emergency_reason = f"stale_premium_during_force_exit: {status}"
                exit_source = "entry_price_emergency"

            pos.exit_price_source = exit_source
            pos.emergency_exit_reason = emergency_reason

            self._close_position(trade_id, exit_price, EXIT_MARKET_CLOSE)

        self._market_close_exit_done = True
        log_info("PaperBroker: force market close exit completed")

    # ── Premium tick routing integration ──

    def get_premium_tokens_needing_subscription(self) -> list[int]:
        """Get all unique premium tokens for open positions."""
        tokens = set()
        for pos in self._positions.values():
            if pos.premium_instrument_token > 0:
                tokens.add(pos.premium_instrument_token)
        return list(tokens)

    # ── Restart Recovery ──

    def restore_positions(self, position_dicts: list[dict]) -> dict[str, Any]:
        """
        Restore open positions from persisted state on startup.

        Returns diagnostic dict with counts.
        """
        restored = 0
        failed = 0
        tokens_resubscribed = set()

        for pd in position_dicts:
            try:
                trade_id = pd.get("trade_id", "")
                if not trade_id:
                    failed += 1
                    continue
                if trade_id in self._positions:
                    continue  # already loaded

                pos = PaperPosition(
                    trade_id=trade_id,
                    symbol=pd.get("symbol", ""),
                    execution_symbol=pd.get("execution_symbol", ""),
                    direction=pd.get("direction", "LONG"),
                    quantity=int(pd.get("quantity", 0)),
                    entry_price=float(pd.get("entry_price", 0.0)),
                    current_price=float(pd.get("current_premium", 0.0) or pd.get("premium_current", 0.0)),
                    stop_loss=pd.get("premium_stop_loss") or pd.get("stop_loss"),
                    target=pd.get("premium_target") or pd.get("target"),
                    created_at=pd.get("created_at", ""),
                    updated_at=pd.get("updated_at", ""),
                    decision_id=pd.get("decision_id", ""),
                    analysis_cycle_id=pd.get("analysis_cycle_id", ""),
                    strategy_version=pd.get("strategy_version", "1.0"),
                    ai_confidence=float(pd.get("ai_confidence", 0.0)),
                    opportunity_score=float(pd.get("opportunity_score", 0.0)),
                    trade_grade=pd.get("trade_grade", ""),
                    execution_type=pd.get("execution_type", "option_buying"),
                    underlying_symbol=pd.get("underlying_symbol", pd.get("symbol")),
                    exchange=pd.get("exchange", "NSE"),
                    option_type=pd.get("option_type"),
                    expiry=pd.get("expiry"),
                    strike=pd.get("strike"),
                    premium_entry=pd.get("premium_entry"),
                    premium_current=pd.get("premium_current"),
                    premium_stop_loss=pd.get("premium_stop_loss"),
                    premium_target=pd.get("premium_target"),
                    lot_size=pd.get("lot_size"),
                    lots=pd.get("lots"),
                    underlying_entry=pd.get("underlying_entry"),
                    risk_reward=pd.get("risk_reward"),
                    premium_source=pd.get("premium_source", ""),
                    instrument_token=int(pd.get("instrument_token", 0)),
                    premium_instrument_token=int(pd.get("premium_instrument_token", 0) or pd.get("instrument_token", 0)),
                    premium_data_status=PREMIUM_STATUS_WAITING,
                    source_provenance=pd.get("source_provenance", ""),
                    test_origin=pd.get("test_origin", ""),
                )

                # Restore capital reservation
                cost = pos.entry_price * pos.quantity
                self._account.open_positions += 1
                self._account.used_margin += cost
                self._account.available_cash -= cost

                self._positions[trade_id] = pos
                restored += 1

                # Track for resubscription
                token = pos.premium_instrument_token
                if token > 0:
                    tokens_resubscribed.add(token)
                    if self._premium_router:
                        self._premium_router.register_position(trade_id, token)

                log_info("PaperBroker: position restored",
                         trade_id=trade_id, symbol=pos.symbol,
                         token=token)

            except Exception as e:
                log_error("PaperBroker: position restore failed",
                          trade_id=pd.get("trade_id", "?"), error=str(e))
                failed += 1

        return {
            "positions_found": len(position_dicts),
            "positions_restored": restored,
            "positions_failed": failed,
            "tokens_resubscribed": list(tokens_resubscribed),
            "last_recovery_at": _now(),
            "recovery_errors": [],
        }

    # ── Persistence helpers ──

    def _persist_position(self, pos: PaperPosition):
        """Persist a newly created position to DB."""
        if not self._db_service:
            return
        try:
            d = pos.to_persistence_dict()
            self._db_service.insert_position(d)
        except Exception as e:
            log_error("PaperBroker: persist position failed",
                      trade_id=pos.trade_id, error=str(e))

    def _persist_position_update(self, trade_id: str, updates: dict):
        """Update a position in DB."""
        if not self._db_service:
            return
        try:
            self._db_service.update_position(trade_id, updates)
        except Exception as e:
            pass  # Non-critical, don't spam logs

    def _persist_closed_trade(self, record: dict):
        """Persist a closed trade to DB."""
        if not self._db_service:
            return
        try:
            self._db_service.insert_trade(record)
        except Exception as e:
            log_error("PaperBroker: persist trade failed",
                      trade_id=record.get("trade_id"), error=str(e))

    def _delete_persisted_position(self, trade_id: str):
        """Delete an open position from DB after closing."""
        if not self._db_service:
            return
        try:
            self._db_service.delete_position(trade_id)
        except Exception as e:
            pass

    def _record_position_event(self, trade_id: str, event_type: str, details: dict | None = None):
        """Record a lifecycle event."""
        if not self._db_service:
            return
        try:
            self._db_service.insert_position_event(trade_id, event_type, details)
        except Exception as e:
            pass

    # ── Queries ──

    def get_position(self, symbol: str) -> PaperPosition | None:
        for pos in self._positions.values():
            if pos.symbol == symbol:
                return pos
        return None

    def get_position_by_id(self, trade_id: str) -> PaperPosition | None:
        return self._positions.get(trade_id)

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

    def get_trade_position_events(self, trade_id: str) -> list[dict]:
        """Get lifecycle events for a position."""
        if not self._db_service:
            return []
        try:
            return self._db_service.get_position_events(trade_id)
        except Exception:
            return []

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

    def record_blocked_attempt(
        self,
        underlying_symbol: str = "",
        direction: str = "",
        analysis_cycle_id: str = "",
        stage: str = "",
        block_code: str = "",
        block_reason: str = "",
        actual_value: str = "",
        required_value: str = "",
        settings_snapshot: dict | None = None,
        risk_snapshot: dict | None = None,
    ) -> BlockedAttempt:
        attempt = BlockedAttempt(
            attempt_id=f"ba_{uuid.uuid4().hex[:8]}",
            timestamp=_now(),
            underlying_symbol=underlying_symbol,
            direction=direction,
            analysis_cycle_id=analysis_cycle_id,
            stage=stage,
            block_code=block_code,
            block_reason=block_reason,
            actual_value=actual_value,
            required_value=required_value,
            settings_snapshot=settings_snapshot,
            risk_snapshot=risk_snapshot,
        )
        self._blocked_attempts.append(attempt)
        if len(self._blocked_attempts) > self._max_blocked_attempts:
            self._blocked_attempts = self._blocked_attempts[-self._max_blocked_attempts:]

        # Persist to DB
        if self._db_service:
            try:
                self._db_service.insert_execution_attempt(attempt.to_dict())
            except Exception:
                pass

        log_info("PaperBroker: blocked attempt recorded",
                 code=block_code, symbol=underlying_symbol, reason=block_reason)
        return attempt

    def get_blocked_attempts(self, limit: int = 50) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._blocked_attempts[-limit:]]


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

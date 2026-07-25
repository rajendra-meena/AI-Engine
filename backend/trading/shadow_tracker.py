"""
Shadow Trade Tracker — manages virtual trades using real market ticks.
Never touches Zerodha, PaperBroker, or ExecutionGateway.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from trading.shadow_trade import ShadowTrade
from trading.market_stream import MarketStreamManager
from models.tick import Tick


def _new_id() -> str:
    return f"sh_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ShadowTradeTracker:
    """
    Manages virtual shadow trades using real validated market ticks.

    - Never calls Zerodha, PaperBroker, or ExecutionGateway
    - Uses MarketStreamManager for price updates
    - Monitors SL/Target via real ticks
    - Tracks P&L, R-multiple, MAE, MFE
    """

    def __init__(self, stream_manager: MarketStreamManager | None = None):
        self._stream_manager = stream_manager
        self._trades: dict[str, ShadowTrade] = {}
        self._history: list[ShadowTrade] = []
        self._open_by_symbol: dict[str, str] = {}  # symbol -> trade_id

    def set_stream_manager(self, mgr: MarketStreamManager):
        self._stream_manager = mgr

    # ── Creation ──

    def create_shadow_trade(
        self,
        strategy_version_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        quantity: int,
        stop_loss: float | None = None,
        target: float | None = None,
        risk_amount: float = 0.0,
        risk_reward: float = 0.0,
        ai_score: int = 0,
        ai_confidence: int = 0,
        market_regime: str = "",
        timeframe: str = "15m",
        decision_id: str = "",
        trade_plan_id: str = "",
    ) -> ShadowTrade | None:
        """Create a new shadow trade. Returns None if position already exists."""
        if symbol in self._open_by_symbol:
            return None  # anti-pyramiding

        if not entry_price or entry_price <= 0:
            return None

        trade = ShadowTrade(
            shadow_trade_id=_new_id(),
            strategy_version_id=strategy_version_id,
            decision_id=decision_id,
            trade_plan_id=trade_plan_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            quantity=quantity,
            risk_amount=risk_amount,
            risk_reward=risk_reward,
            entry_timestamp=_now(),
            ai_score=ai_score,
            ai_confidence=ai_confidence,
            market_regime=market_regime,
            timeframe=timeframe,
            status="open",
        )
        self._trades[trade.shadow_trade_id] = trade
        self._open_by_symbol[symbol] = trade.shadow_trade_id
        return trade

    # ── Tick handler (called by MarketStreamManager) ──

    def on_tick(self, tick: Tick):
        """Process real market tick for shadow SL/Target monitoring."""
        price = tick.price
        if price <= 0:
            return

        trade_id = self._open_by_symbol.get(tick.symbol)
        if not trade_id:
            return

        trade = self._trades.get(trade_id)
        if not trade or trade.status != "open":
            return

        # Update unrealized P&L
        if trade.direction == "LONG":
            trade.unrealized_pnl = (price - trade.entry_price) * trade.quantity
        else:
            trade.unrealized_pnl = (trade.entry_price - price) * trade.quantity

        # Update MAE/MFE
        if trade.direction == "LONG":
            trade.mae = min(trade.mae or 0, price - trade.entry_price)
            trade.mfe = max(trade.mfe or 0, price - trade.entry_price)
        else:
            trade.mae = min(trade.mae or 0, trade.entry_price - price)
            trade.mfe = max(trade.mfe or 0, trade.entry_price - price)
        # Check SL
        if trade.stop_loss is not None:
            sl_hit = (trade.direction == "LONG" and price <= trade.stop_loss) or \
                     (trade.direction == "SHORT" and price >= trade.stop_loss)
            if sl_hit:
                self._close_trade(trade_id, trade.stop_loss, "stop_loss")
                return

        # Check Target
        if trade.target is not None:
            target_hit = (trade.direction == "LONG" and price >= trade.target) or \
                         (trade.direction == "SHORT" and price <= trade.target)
            if target_hit:
                self._close_trade(trade_id, trade.target, "target")

    # ── Close ──

    def close_trade(self, trade_id: str, reason: str = "manual") -> bool:
        trade = self._trades.get(trade_id)
        if not trade or trade.status != "open":
            return False
        self._close_trade(trade_id, None, reason)
        return True

    def _close_trade(self, trade_id: str, exit_price: float | None, reason: str):
        trade = self._trades.get(trade_id)
        if not trade:
            return

        if exit_price is None:
            exit_price = trade.entry_price

        if trade.direction == "LONG":
            trade.realized_pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            trade.realized_pnl = (trade.entry_price - exit_price) * trade.quantity

        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.unrealized_pnl = 0.0
        trade.status = "closed"
        trade.exit_timestamp = _now()

        risk = abs(trade.entry_price - (trade.stop_loss or trade.entry_price)) * trade.quantity
        trade.r_multiple = trade.realized_pnl / risk if risk > 0 else 0

        self._open_by_symbol.pop(trade.symbol, None)
        self._history.append(trade)

    # ── Queries ──

    def get_trade(self, trade_id: str) -> ShadowTrade | None:
        return self._trades.get(trade_id)

    def get_open_trades(self) -> list[ShadowTrade]:
        return [t for t in self._trades.values() if t.status == "open"]

    def get_closed_trades(self) -> list[ShadowTrade]:
        return list(self._history)

    def get_all_trades(self) -> list[ShadowTrade]:
        return list(self._trades.values())

    def get_performance(self) -> dict[str, Any]:
        closed = self._history
        total = len(closed)
        wins = [t for t in closed if t.realized_pnl > 0]
        losses = [t for t in closed if t.realized_pnl <= 0]
        win_count = len(wins)
        loss_count = len(losses)
        gp = sum(t.realized_pnl for t in wins)
        gl = abs(sum(t.realized_pnl for t in losses))
        r_vals = [t.r_multiple for t in closed if t.r_multiple != 0]
        return {
            "total_trades": total,
            "open_trades": len(self.get_open_trades()),
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": round(win_count / max(total, 1) * 100, 1),
            "gross_profit": round(gp, 2),
            "gross_loss": round(gl, 2),
            "net_pnl": round(gp - gl, 2),
            "profit_factor": round(gp / max(gl, 0.01), 2) if gl > 0 else 0,
            "expectancy": round((gp - gl) / max(total, 1), 2),
            "avg_r": round(sum(r_vals) / max(len(r_vals), 1), 2) if r_vals else 0,
        }

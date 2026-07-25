"""BacktestBroker — completely isolated execution environment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backtest.backtest_models import BacktestConfig, BacktestTrade


@dataclass
class BacktestPosition:
    symbol: str = ""
    direction: str = "LONG"
    quantity: int = 0
    entry_price: float = 0.0
    entry_time: str = ""
    stop_loss: float | None = None
    target: float | None = None
    gross_pnl: float = 0.0
    brokerage: float = 0.0
    slippage_cost: float = 0.0
    net_pnl: float = 0.0
    mae: float = 0.0
    mfe: float = 0.0
    ai_score: int = 0
    ai_confidence: int = 0
    strategy_score: int = 0
    regime: str = ""
    trace_id: str = ""
    decision_id: str = ""
    trade_plan_id: str = ""
    exit_price: float | None = None
    exit_time: str | None = None
    exit_reason: str = ""
    intrabar_ambiguity: bool = False


class BacktestBroker:
    """Isolated backtest execution — never touches Zerodha or PaperBroker."""

    def __init__(self, config: BacktestConfig):
        self._config = config
        self._positions: dict[str, BacktestPosition] = {}
        self._trades: list[BacktestTrade] = []
        self._equity: list[float] = [config.initial_capital]
        self._equity_times: list[str] = []
        self._cash = config.initial_capital
        self._peak_equity = config.initial_capital
        self._max_dd_pct = 0.0

    @property
    def positions(self) -> dict[str, BacktestPosition]:
        return self._positions

    @property
    def trades(self) -> list[BacktestTrade]:
        return self._trades

    @property
    def equity_curve(self) -> list[dict[str, Any]]:
        return [{"time": t, "equity": e} for t, e in zip(self._equity_times, self._equity)]

    def open_position(
        self, symbol: str, direction: str, quantity: int, price: float,
        timestamp: str, stop_loss: float | None = None, target: float | None = None,
        ai_score: int = 0, ai_confidence: int = 0, strategy_score: int = 0,
        regime: str = "", trace_id: str = "", decision_id: str = "", trade_plan_id: str = "",
    ) -> bool:
        if symbol in self._positions:
            return False
        entry_price = self._apply_slippage(price, direction)
        cost = entry_price * quantity
        brokerage = self._calc_brokerage(cost)
        if cost + brokerage > self._cash:
            return False
        self._cash -= cost + brokerage
        pos = BacktestPosition(
            symbol=symbol, direction=direction, quantity=quantity,
            entry_price=entry_price, entry_time=timestamp,
            stop_loss=stop_loss, target=target,
            brokerage=brokerage, slippage_cost=abs(entry_price - price) * quantity,
            ai_score=ai_score, ai_confidence=ai_confidence,
            strategy_score=strategy_score, regime=regime,
            trace_id=trace_id, decision_id=decision_id, trade_plan_id=trade_plan_id,
        )
        self._positions[symbol] = pos
        return True

    def process_candle(self, candle: dict, timestamp: str) -> list[BacktestTrade]:
        closed: list[BacktestTrade] = []
        high = float(candle.get("high", 0))
        low = float(candle.get("low", 0))
        close = float(candle.get("close", 0))

        for sym in list(self._positions.keys()):
            pos = self._positions[sym]

            if pos.direction == "LONG":
                pos.mae = min(pos.mae or 0, (low - pos.entry_price) * pos.quantity)
                pos.mfe = max(pos.mfe or 0, (high - pos.entry_price) * pos.quantity)
            else:
                pos.mae = min(pos.mae or 0, (pos.entry_price - high) * pos.quantity)
                pos.mfe = max(pos.mfe or 0, (pos.entry_price - low) * pos.quantity)

            sl_hit = pos.stop_loss is not None and (
                (pos.direction == "LONG" and low <= pos.stop_loss) or
                (pos.direction == "SHORT" and high >= pos.stop_loss)
            )
            target_hit = pos.target is not None and (
                (pos.direction == "LONG" and high >= pos.target) or
                (pos.direction == "SHORT" and low <= pos.target)
            )

            exit_price = None
            reason = ""
            ambiguity = False

            if sl_hit and target_hit:
                rule = self._config.intrabar_rule
                if rule == "conservative":
                    exit_price, reason = pos.stop_loss, "stop_loss"
                elif rule == "optimistic":
                    exit_price, reason = pos.target, "target"
                else:
                    continue
                ambiguity = True
            elif sl_hit:
                exit_price, reason = pos.stop_loss, "stop_loss"
            elif target_hit:
                exit_price, reason = pos.target, "target"

            if exit_price is not None:
                trade = self._close_position(sym, exit_price, timestamp, reason, ambiguity)
                if trade:
                    closed.append(trade)

        total_equity = self._cash
        for pos in self._positions.values():
            if pos.direction == "LONG":
                total_equity += (close - pos.entry_price) * pos.quantity
            else:
                total_equity += (pos.entry_price - close) * pos.quantity
        self._equity.append(total_equity)
        self._equity_times.append(timestamp)
        if total_equity > self._peak_equity:
            self._peak_equity = total_equity
        dd = (self._peak_equity - total_equity) / self._peak_equity * 100 if self._peak_equity > 0 else 0
        if dd > self._max_dd_pct:
            self._max_dd_pct = dd
        return closed

    def close_position(self, symbol: str, timestamp: str, reason: str = "manual") -> BacktestTrade | None:
        return self._close_position(symbol, None, timestamp, reason)

    def close_all(self, timestamp: str, reason: str = "backtest_end") -> list[BacktestTrade]:
        closed = []
        for sym in list(self._positions.keys()):
            t = self._close_position(sym, None, timestamp, reason)
            if t:
                closed.append(t)
        return closed

    def _close_position(self, symbol: str, exit_price: float | None, timestamp: str,
                        reason: str, ambiguity: bool = False) -> BacktestTrade | None:
        pos = self._positions.pop(symbol, None)
        if not pos:
            return None
        if exit_price is None:
            exit_price = pos.entry_price
        exit_actual = self._apply_slippage(exit_price, "SELL" if pos.direction == "LONG" else "BUY")
        exit_slip = abs(exit_actual - exit_price) * pos.quantity
        if pos.direction == "LONG":
            gross = (exit_actual - pos.entry_price) * pos.quantity
        else:
            gross = (pos.entry_price - exit_actual) * pos.quantity
        exit_brokerage = self._calc_brokerage(exit_actual * pos.quantity)
        net = gross - pos.brokerage - exit_brokerage - exit_slip
        self._cash += (exit_actual * pos.quantity) - exit_brokerage - exit_slip
        risk = abs(pos.entry_price - (pos.stop_loss or pos.entry_price)) * pos.quantity
        r = net / risk if risk > 0 else 0
        trade = BacktestTrade(
            symbol=pos.symbol, direction=pos.direction, quantity=pos.quantity,
            entry_price=pos.entry_price, entry_time=pos.entry_time,
            exit_price=exit_actual, exit_time=timestamp,
            stop_loss=pos.stop_loss, target=pos.target,
            gross_pnl=gross, brokerage=pos.brokerage + exit_brokerage,
            slippage_cost=pos.slippage_cost + exit_slip, net_pnl=net,
            r_multiple=r, mae=pos.mae, mfe=pos.mfe,
            exit_reason=reason, intrabar_ambiguity=ambiguity,
            ai_score=pos.ai_score, ai_confidence=pos.ai_confidence,
            strategy_score=pos.strategy_score, regime=pos.regime,
            trace_id=pos.trace_id, decision_id=pos.decision_id, trade_plan_id=pos.trade_plan_id,
        )
        self._trades.append(trade)
        return trade

    def _apply_slippage(self, price: float, side: str) -> float:
        model, val = self._config.slippage_model, self._config.slippage_value
        if model == "fixed":
            return price + val if side == "BUY" else price - val
        if model == "percent":
            return price * (1 + val / 100) if side == "BUY" else price * (1 - val / 100)
        if model == "bps":
            return price * (1 + val / 10000) if side == "BUY" else price * (1 - val / 10000)
        return price

    def _calc_brokerage(self, value: float) -> float:
        model, val = self._config.brokerage_model, self._config.brokerage_value
        if model == "fixed":
            return val
        if model == "percent":
            return value * val / 100
        return 0.0

    def get_summary(self) -> dict[str, Any]:
        return {
            "initial_capital": self._config.initial_capital,
            "final_equity": round(self._equity[-1], 2) if self._equity else 0,
            "net_pnl": round(self._equity[-1] - self._config.initial_capital, 2) if self._equity else 0,
            "max_drawdown_pct": round(self._max_dd_pct, 2),
            "total_trades": len(self._trades),
        }

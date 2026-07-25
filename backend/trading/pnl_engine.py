"""
Centralized P&L Engine — single source of truth for all P&L calculations.

Calculates:
- Position-level unrealized/realized P&L
- Trade-level P&L
- Portfolio-level P&L
- Day P&L
- Exposure
- Margin utilization

Supports: LONG, SHORT, partial fills, multiple fills, partial exits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PositionPnL:
    """P&L for a single position."""
    symbol: str = ""
    direction: str = "LONG"
    quantity: int = 0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    day_pnl: float = 0.0
    return_pct: float = 0.0
    exposure: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_price": round(self.entry_price, 2),
            "current_price": round(self.current_price, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "day_pnl": round(self.day_pnl, 2),
            "return_pct": round(self.return_pct, 2),
            "exposure": round(self.exposure, 2),
        }


@dataclass
class PortfolioPnL:
    """Aggregate portfolio P&L."""
    total_unrealized: float = 0.0
    total_realized: float = 0.0
    total_pnl: float = 0.0
    day_pnl: float = 0.0
    total_exposure: float = 0.0
    total_equity: float = 0.0
    available_margin: float = 0.0
    used_margin: float = 0.0
    margin_utilization_pct: float = 0.0
    positions: list[PositionPnL] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_unrealized": round(self.total_unrealized, 2),
            "total_realized": round(self.total_realized, 2),
            "total_pnl": round(self.total_pnl, 2),
            "day_pnl": round(self.day_pnl, 2),
            "total_exposure": round(self.total_exposure, 2),
            "total_equity": round(self.total_equity, 2),
            "available_margin": round(self.available_margin, 2),
            "used_margin": round(self.used_margin, 2),
            "margin_utilization_pct": round(self.margin_utilization_pct, 2),
            "positions": [p.to_dict() for p in self.positions],
            "last_updated": self.last_updated or datetime.now(timezone.utc).isoformat(),
        }


class PnLEngine:
    """
    Centralized P&L Engine — one source of truth.

    Receives:
    - Position updates (from trade lifecycle)
    - Price updates (from market data stream)
    - Fill events (from order lifecycle)

    Produces:
    - PositionPnL per position
    - PortfolioPnL aggregated
    - Events for WebSocket broadcast
    """

    def __init__(self, initial_capital: float = 100000.0):
        self._initial_capital = initial_capital
        self._positions: dict[str, PositionPnL] = {}
        self._realized_pnl: float = 0.0
        self._day_start_equity = initial_capital
        self._last_pnl: PortfolioPnL = PortfolioPnL()
        self._callbacks: list[callable] = []

    def on_callback(self, cb: callable):
        """Register a callback for P&L updates."""
        self._callbacks.append(cb)

    # ── Position updates ──

    def update_position(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        entry_price: float,
        current_price: float | None = None,
    ):
        """Update or create a position record."""
        pos = self._positions.get(symbol)
        if not pos:
            pos = PositionPnL(symbol=symbol, direction=direction)
            self._positions[symbol] = pos

        pos.quantity = quantity
        pos.entry_price = entry_price
        pos.direction = direction
        if current_price is not None:
            pos.current_price = current_price

        self._recalc_position(pos)
        self._recalc_portfolio()

    def remove_position(self, symbol: str):
        """Remove a closed position."""
        self._positions.pop(symbol, None)
        self._recalc_portfolio()

    def update_price(self, symbol: str, price: float):
        """Update current price for a position (from market tick)."""
        pos = self._positions.get(symbol)
        if not pos:
            return
        pos.current_price = price
        self._recalc_position(pos)
        self._recalc_portfolio()

    def add_realized_pnl(self, pnl: float):
        """Add realized P&L from a closed trade."""
        self._realized_pnl += pnl
        self._recalc_portfolio()

    def batch_update_prices(self, price_map: dict[str, float]):
        """Update prices for multiple symbols at once."""
        for symbol, price in price_map.items():
            pos = self._positions.get(symbol)
            if pos:
                pos.current_price = price
                self._recalc_position(pos)
        self._recalc_portfolio()

    # ── Internal calculations ──

    def _recalc_position(self, pos: PositionPnL):
        """Recalculate a single position's P&L."""
        if pos.direction == "LONG":
            price_diff = pos.current_price - pos.entry_price
        else:
            price_diff = pos.entry_price - pos.current_price

        pos.unrealized_pnl = price_diff * pos.quantity
        pos.total_pnl = pos.unrealized_pnl + pos.realized_pnl
        pos.exposure = pos.current_price * pos.quantity

        if pos.entry_price > 0:
            pos.return_pct = (price_diff / pos.entry_price) * 100

        # Day P&L = unrealized (simplified)
        pos.day_pnl = pos.unrealized_pnl

    def _recalc_portfolio(self):
        """Recalculate aggregate portfolio P&L."""
        portfolio = PortfolioPnL()
        portfolio.total_unrealized = sum(p.unrealized_pnl for p in self._positions.values())
        portfolio.total_realized = self._realized_pnl
        portfolio.total_pnl = portfolio.total_unrealized + portfolio.total_realized
        portfolio.total_exposure = sum(p.exposure for p in self._positions.values())
        portfolio.positions = list(self._positions.values())
        portfolio.day_pnl = portfolio.total_pnl
        portfolio.total_equity = self._initial_capital + portfolio.total_pnl
        portfolio.available_margin = max(0, self._initial_capital - abs(portfolio.total_exposure))
        portfolio.used_margin = min(self._initial_capital, abs(portfolio.total_exposure))
        if self._initial_capital > 0:
            portfolio.margin_utilization_pct = (portfolio.used_margin / self._initial_capital) * 100
        portfolio.last_updated = datetime.now(timezone.utc).isoformat()
        self._last_pnl = portfolio

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(portfolio)
            except Exception:
                pass

    # ── Queries ──

    def get_position_pnl(self, symbol: str) -> PositionPnL | None:
        return self._positions.get(symbol)

    def get_portfolio_pnl(self) -> PortfolioPnL:
        return self._last_pnl

    def get_all_positions_pnl(self) -> list[PositionPnL]:
        return list(self._positions.values())

    def reset(self):
        self._positions.clear()
        self._realized_pnl = 0.0
        self._recalc_portfolio()


# Singleton
_instance: PnLEngine | None = None


def get_pnl_engine() -> PnLEngine:
    assert _instance is not None, "PnLEngine not initialized"
    return _instance


def init_pnl_engine(initial_capital: float = 100000.0) -> PnLEngine:
    global _instance
    _instance = PnLEngine(initial_capital)
    return _instance

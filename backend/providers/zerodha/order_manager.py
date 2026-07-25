"""
Zerodha Kite Connect — Order Manager

Handles all order-related operations via Kite Connect API:

- Place orders (Market, Limit, SL, SL-M)
- Modify orders
- Cancel orders
- Position management
- Holdings and margins
- Order history and trade book
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from utils.logger import log_info, log_warn, log_error


class KiteOrderError(Exception):
    """Base exception for Kite order errors."""
    pass


class OrderManager:
    """
    Manages order execution through Kite Connect.

    Wraps all Kite order APIs with error handling, logging, and
    normalized return types.
    """

    def __init__(self, kite=None):
        self._kite = kite

    def set_kite(self, kite):
        """Set or update the KiteConnect instance."""
        self._kite = kite

    @property
    def is_ready(self) -> bool:
        return self._kite is not None

    # ── Order placement ──

    def place_order(
        self,
        tradingsymbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: float = 0.0,
        product: str = "MIS",
        validity: str = "DAY",
        variety: str = "regular",
        trigger_price: float | None = None,
        stoploss: float | None = None,
        squareoff: float | None = None,
        trailing_stoploss: int | None = None,
        tag: str = "",
    ) -> dict[str, Any]:
        """
        Place an order on Kite.

        Args:
            tradingsymbol: Trading symbol (e.g. "NIFTY", "RELIANCE")
            exchange: Exchange (e.g. "NSE", "BSE", "NFO")
            transaction_type: "BUY" or "SELL"
            quantity: Order quantity
            order_type: "MARKET", "LIMIT", "SL", "SL-M"
            price: Price for limit orders
            product: "MIS", "NRML", "CNC"
            validity: "DAY", "IOC"
            variety: "regular", "amo", "co", "iceberg"
            trigger_price: Trigger price for SL orders
            stoploss: Stoploss for bracket orders
            squareoff: Squareoff for bracket orders
            trailing_stoploss: Trailing stoploss for bracket orders
            tag: Optional order tag

        Returns:
            Order result dict with order_id.

        Raises:
            KiteOrderError: If order placement fails.
        """
        if not self._kite:
            raise KiteOrderError("Kite not connected")

        try:
            params = {
                "tradingsymbol": tradingsymbol,
                "exchange": exchange,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "order_type": order_type,
                "product": product,
                "validity": validity,
                "variety": variety,
            }

            if price > 0 and order_type in ("LIMIT", "SL"):
                params["price"] = price
            if trigger_price is not None:
                params["trigger_price"] = trigger_price
            if stoploss is not None:
                params["stoploss"] = stoploss
            if squareoff is not None:
                params["squareoff"] = squareoff
            if trailing_stoploss is not None:
                params["trailing_stoploss"] = trailing_stoploss
            if tag:
                params["tag"] = tag

            order_id = self._kite.place_order(**params)
            log_info(
                "OrderManager: order placed",
                order_id=order_id,
                symbol=tradingsymbol,
                type=order_type,
                tx=transaction_type,
                qty=quantity,
            )
            return {"success": True, "order_id": order_id, "status": "pending"}

        except Exception as e:
            log_error(
                "OrderManager: order placement failed",
                symbol=tradingsymbol,
                error=str(e),
            )
            raise KiteOrderError(f"Order placement failed: {e}") from e

    # ── Order modification ──

    def modify_order(
        self,
        order_id: str,
        price: float | None = None,
        quantity: int | None = None,
        order_type: str | None = None,
        trigger_price: float | None = None,
        variety: str = "regular",
    ) -> dict[str, Any]:
        """
        Modify an existing order.

        Args:
            order_id: The order ID to modify
            price: New price
            quantity: New quantity
            order_type: New order type
            trigger_price: New trigger price
            variety: Order variety

        Returns:
            Modified order result.
        """
        if not self._kite:
            raise KiteOrderError("Kite not connected")

        try:
            params: dict[str, Any] = {"variety": variety, "order_id": order_id}
            if price is not None:
                params["price"] = price
            if quantity is not None:
                params["quantity"] = quantity
            if order_type is not None:
                params["order_type"] = order_type
            if trigger_price is not None:
                params["trigger_price"] = trigger_price

            modified_id = self._kite.modify_order(**params)
            log_info("OrderManager: order modified", order_id=order_id)
            return {"success": True, "order_id": modified_id}

        except Exception as e:
            log_error("OrderManager: order modification failed", order_id=order_id, error=str(e))
            raise KiteOrderError(f"Order modification failed: {e}") from e

    # ── Order cancellation ──

    def cancel_order(self, order_id: str, variety: str = "regular") -> dict[str, Any]:
        """Cancel an order by ID."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")

        try:
            self._kite.cancel_order(variety=variety, order_id=order_id)
            log_info("OrderManager: order cancelled", order_id=order_id)
            return {"success": True, "order_id": order_id}
        except Exception as e:
            log_error("OrderManager: cancellation failed", order_id=order_id, error=str(e))
            raise KiteOrderError(f"Order cancellation failed: {e}") from e

    # ── Position management ──

    def get_positions(self) -> list[dict[str, Any]]:
        """Get current open positions."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            positions = self._kite.positions()
            # Flatten day + net positions
            result = []
            for ptype in ("net", "day"):
                for pos in positions.get(ptype, []):
                    pos["position_type"] = ptype
                    result.append(pos)
            return result
        except Exception as e:
            log_error("OrderManager: get positions failed", error=str(e))
            raise KiteOrderError(f"Get positions failed: {e}") from e

    def exit_position(self, tradingsymbol: str, exchange: str = "NSE") -> dict[str, Any]:
        """Exit an open position."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            self._kite.exit_position(tradingsymbol=tradingsymbol, exchange=exchange)
            log_info("OrderManager: position exited", symbol=tradingsymbol)
            return {"success": True, "symbol": tradingsymbol}
        except Exception as e:
            log_error("OrderManager: exit position failed", symbol=tradingsymbol, error=str(e))
            raise KiteOrderError(f"Exit position failed: {e}") from e

    # ── Holdings ──

    def get_holdings(self) -> list[dict[str, Any]]:
        """Get equity holdings."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            return self._kite.holdings()
        except Exception as e:
            log_error("OrderManager: get holdings failed", error=str(e))
            raise KiteOrderError(f"Get holdings failed: {e}") from e

    # ── Margins and funds ──

    def get_margins(self) -> dict[str, Any]:
        """Get available margins and funds."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            margins = self._kite.margins()
            equity = margins.get("equity", {})
            commodity = margins.get("commodity", {})
            return {
                "equity": {
                    "available_cash": equity.get("available", {}).get("cash", 0),
                    "available_intraday_payin": equity.get("available", {}).get("intraday_payin", 0),
                    "available_limit": equity.get("available", {}).get("limit", 0),
                    "used_margin": equity.get("used", {}).get("dealer", 0),
                    "m2m_realised": equity.get("utilised", {}).get("m2m_realised", 0),
                    "m2m_unrealised": equity.get("utilised", {}).get("m2m_unrealised", 0),
                },
                "commodity": {
                    "available_cash": commodity.get("available", {}).get("cash", 0),
                    "available_limit": commodity.get("available", {}).get("limit", 0),
                },
            }
        except Exception as e:
            log_error("OrderManager: get margins failed", error=str(e))
            raise KiteOrderError(f"Get margins failed: {e}") from e

    # ── Orders and trades ──

    def get_orders(self) -> list[dict[str, Any]]:
        """Get all orders (pending + executed)."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            return self._kite.orders()
        except Exception as e:
            log_error("OrderManager: get orders failed", error=str(e))
            raise KiteOrderError(f"Get orders failed: {e}") from e

    def get_order_history(self, order_id: str) -> list[dict[str, Any]]:
        """Get history for a specific order."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            return self._kite.order_history(order_id)
        except Exception as e:
            log_error("OrderManager: order history failed", order_id=order_id, error=str(e))
            raise KiteOrderError(f"Order history failed: {e}") from e

    def get_trades(self) -> list[dict[str, Any]]:
        """Get executed trades."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            return self._kite.trades()
        except Exception as e:
            log_error("OrderManager: get trades failed", error=str(e))
            raise KiteOrderError(f"Get trades failed: {e}") from e

    def get_position_trades(self, tradingsymbol: str, exchange: str = "NSE") -> list[dict[str, Any]]:
        """Get trades for a specific position."""
        if not self._kite:
            raise KiteOrderError("Kite not connected")
        try:
            return self._kite.position_trades(tradingsymbol=tradingsymbol, exchange=exchange)
        except Exception as e:
            log_error("OrderManager: position trades failed", symbol=tradingsymbol, error=str(e))
            raise KiteOrderError(f"Position trades failed: {e}") from e

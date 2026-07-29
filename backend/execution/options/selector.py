"""
Option Selector — converts underlying + direction into an option contract.

Rules:
  - Underlying BUY/LONG  → Call Option (CE)
  - Underlying SELL/SHORT → Put Option (PE)
  - Default strike: ATM (nearest to underlying LTP)
  - Default expiry: nearest weekly
  - Strike rounding per index: NIFTY=50, BANKNIFTY=100, SENSEX=1
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from core.enums import normalize_direction, TradeDirection

# Index strike rounding intervals
STRIKE_INTERVALS: dict[str, int] = {
    "NIFTY 50": 50,
    "BANKNIFTY": 100,
    "SENSEX": 1,
    "FINNIFTY": 50,
    "MIDCPNIFTY": 25,
}

# Default lot sizes (from options/models.py — verified live data)
DEFAULT_LOT_SIZES: dict[str, int] = {
    "NIFTY 50": 65,
    "BANKNIFTY": 30,
    "SENSEX": 20,
    "FINNIFTY": 60,
    "MIDCPNIFTY": 120,
}


class OptionSelector:
    """Selects option contract from underlying symbol + direction + price."""

    @staticmethod
    def round_strike(price: float, interval: int) -> float:
        """Round a price to the nearest strike interval."""
        return round(price / interval) * interval

    @staticmethod
    def get_strike_interval(symbol: str) -> int:
        """Get strike rounding interval for an index symbol."""
        return STRIKE_INTERVALS.get(symbol, 50)

    @staticmethod
    def get_lot_size(symbol: str) -> int:
        """Get lot size for an index symbol."""
        return DEFAULT_LOT_SIZES.get(symbol, 25)

    @staticmethod
    def nearest_weekly_expiry() -> date:
        """Return the nearest weekly expiry date (Thursday)."""
        from datetime import timezone as dt_timezone
        today = datetime.now(dt_timezone.utc).date()
        days_until_thu = (3 - today.weekday()) % 7
        if days_until_thu == 0:
            # Expiry today if before 3:30 PM IST, otherwise next week
            now_ist = datetime.now(dt_timezone.utc).hour * 60 + datetime.now(dt_timezone.utc).minute + 330
            if now_ist >= 930:  # past 3:30 PM IST
                days_until_thu = 7
        return today + timedelta(days=days_until_thu or 7)

    @staticmethod
    def select_option_type(direction_raw: str) -> str:
        """BUY/LONG → CE, SELL/SHORT → PE."""
        d = normalize_direction(direction_raw)
        if d == TradeDirection.LONG:
            return "CE"
        if d == TradeDirection.SHORT:
            return "PE"
        raise ValueError(f"Cannot select option type for direction: {direction_raw}")

    @classmethod
    def select(cls, symbol: str, direction: str, underlying_price: float) -> dict[str, Any]:
        """
        Select an option contract for the given underlying.

        Computes the ATM strike from the live underlying price, resolves
        expiry and lot size. When the Zerodha instrument manager is available,
        also resolves the real instrument token, trading symbol, and exchange.

        Returns serializable dict with option selection details.
        """
        option_type = cls.select_option_type(direction)
        interval = cls.get_strike_interval(symbol)
        strike = cls.round_strike(underlying_price, interval)
        expiry = cls.nearest_weekly_expiry()
        lot_size = cls.get_lot_size(symbol)
        expiry_compact = expiry.isoformat()

        # Resolve real instrument metadata from Zerodha instrument master
        instrument_token = 0
        trading_symbol = ""
        exchange = "NFO"

        try:
            from main import zerodha_engine as _ze
            if _ze and hasattr(_ze, '_instrument_manager') and _ze._instrument_manager and _ze._instrument_manager.is_loaded:
                im = _ze._instrument_manager
                # Map internal name to Kite trading symbol
                kite_symbol = im.map_to_kite_symbol(symbol)
                if not kite_symbol:
                    kite_symbol = symbol
                # Look up the option instrument by symbol prefix, expiry and strike
                expiry_str = expiry_compact[:10]
                for inst in getattr(im, '_instruments', []) or []:
                    ts = inst.get("tradingsymbol", "")
                    seg = inst.get("segment", "")
                    inst_type = inst.get("instrument_type", "")
                    inst_expiry = inst.get("expiry", "")
                    inst_strike = inst.get("strike", 0)
                    if (seg == "NFO" and inst_type in ("OPTIDX", "OPTSTK")
                            and ts.startswith(kite_symbol)
                            and inst_expiry == expiry_str
                            and abs(inst_strike - strike) < interval):
                        instrument_token = inst.get("instrument_token", 0)
                        trading_symbol = ts
                        exchange = inst.get("exchange", "NFO")
                        lot_size = inst.get("lot_size", lot_size)
                        break
        except ImportError:
            pass
        except Exception:
            pass

        return {
            "option_type": option_type,
            "expiry": expiry_compact,
            "strike": strike,
            "strike_interval": interval,
            "expiry_type": "weekly",
            "lot_size": lot_size,
            "instrument_token": instrument_token,
            "trading_symbol": trading_symbol,
            "exchange": exchange,
        }
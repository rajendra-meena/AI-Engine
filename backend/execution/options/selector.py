"""
Option Selector — converts underlying + direction into an option contract.

Uses the Zerodha instrument master to resolve the exact:
- tradingsymbol (from broker dump, never string-concatenated)
- instrument_token
- exchange
- lot_size and tick_size
- nearest valid expiry from available contracts
- nearest available strike to ATM

Falls back to computed values when instrument master is unavailable.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from core.enums import normalize_direction, TradeDirection

# Index strike rounding intervals
STRIKE_INTERVALS: dict[str, int] = {
    "NIFTY 50": 50,
    "NIFTY": 50,
    "BANKNIFTY": 100,
    "SENSEX": 1,
    "FINNIFTY": 50,
    "MIDCPNIFTY": 25,
}

# Default lot sizes
DEFAULT_LOT_SIZES: dict[str, int] = {
    "NIFTY 50": 65,
    "BANKNIFTY": 30,
    "SENSEX": 20,
    "FINNIFTY": 60,
    "MIDCPNIFTY": 120,
}

# Underlying symbol normalization map for Zerodha Kite
UNDERLYING_ALIASES: dict[str, str] = {
    "NIFTY 50": "NIFTY",
    "NIFTY": "NIFTY",
    "NSE:NIFTY 50": "NIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "NIFTY BANK": "BANKNIFTY",
    "BANK NIFTY": "BANKNIFTY",
    "SENSEX": "SENSEX",
    "BSE SENSEX": "SENSEX",
    "FINNIFTY": "FINNIFTY",
    "MIDCPNIFTY": "MIDCPNIFTY",
}


def normalize_underlying(symbol: str) -> str:
    """Normalize an internal display symbol to the broker's underlying name."""
    return UNDERLYING_ALIASES.get(symbol.upper(), symbol.upper())


def _get_zerodha_instrument_manager():
    """Get the Zerodha instrument manager from the auto-trade engine singleton."""
    try:
        from api.auto_trade import _zerodha_engine as _ze
        if _ze and hasattr(_ze, '_instrument_manager'):
            im = _ze._instrument_manager
            if im and im.is_loaded:
                return im
    except Exception:
        pass
    return None


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
            now_ist = datetime.now(dt_timezone.utc).hour * 60 + datetime.now(dt_timezone.utc).minute + 330
            if now_ist >= 930:
                days_until_thu = 7
        return today + timedelta(days=days_until_thu or 7)

    @staticmethod
    def select_option_type(direction_raw: str) -> str:
        """BUY/LONG -> CE, SELL/SHORT -> PE."""
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

        Uses the Zerodha instrument master when available to resolve the exact
        tradingsymbol, instrument_token, exchange, lot_size, and tick_size.
        Falls back to computed values when instrument master is unavailable.
        """
        option_type = cls.select_option_type(direction)
        interval = cls.get_strike_interval(symbol)
        normalized = normalize_underlying(symbol)

        im = _get_zerodha_instrument_manager()
        if im:
            return cls._resolve_from_master(im, symbol, normalized, option_type, underlying_price, interval)

        # Fallback: calendar-based
        strike = cls.round_strike(underlying_price, interval)
        expiry = cls.nearest_weekly_expiry()
        lot_size = cls.get_lot_size(symbol)
        return {
            "option_type": option_type,
            "expiry": expiry.isoformat()[:10],
            "strike": strike,
            "strike_interval": interval,
            "expiry_type": "weekly",
            "lot_size": lot_size,
            "instrument_token": 0,
            "trading_symbol": "",
            "exchange": "NFO",
            "normalized_underlying": normalized,
        }

    @classmethod
    def _resolve_from_master(cls, im, display_symbol, normalized_underlying, option_type, underlying_price, interval):
        """Resolve contract from instrument master."""
        exchange = cls._determine_exchange(im, normalized_underlying)
        expiry_str = cls._resolve_nearest_expiry(im, normalized_underlying, option_type, exchange)
        if not expiry_str:
            expiry_str = cls.nearest_weekly_expiry().isoformat()[:10]

        available_strikes = cls._get_strikes_for_expiry(im, normalized_underlying, expiry_str, option_type, exchange)
        atm_strike = cls._nearest_strike(underlying_price, available_strikes) if available_strikes else cls.round_strike(underlying_price, interval)

        instrument = cls._find_instrument(im, normalized_underlying, expiry_str, atm_strike, option_type, exchange)
        if instrument:
            return {
                "option_type": option_type,
                "expiry": expiry_str,
                "strike": float(instrument.get("strike", atm_strike)),
                "strike_interval": interval,
                "expiry_type": "weekly",
                "lot_size": instrument.get("lot_size", cls.get_lot_size(display_symbol)),
                "instrument_token": instrument.get("instrument_token", 0),
                "trading_symbol": instrument.get("tradingsymbol", ""),
                "exchange": instrument.get("exchange", exchange),
                "normalized_underlying": normalized_underlying,
                "tick_size": instrument.get("tick_size", 0.05),
            }

        # Fallback within instrument-master scope but no exact match
        lot_size = cls.get_lot_size(display_symbol)
        return {
            "option_type": option_type,
            "expiry": expiry_str,
            "strike": atm_strike or cls.round_strike(underlying_price, interval),
            "strike_interval": interval,
            "expiry_type": "weekly",
            "lot_size": lot_size,
            "instrument_token": 0,
            "trading_symbol": "",
            "exchange": exchange,
            "normalized_underlying": normalized_underlying,
        }

    @classmethod
    def _determine_exchange(cls, im, normalized_underlying: str) -> str:
        for inst in getattr(im, '_instruments', []) or []:
            ts = inst.get("tradingsymbol", "").upper()
            seg = inst.get("segment", "")
            inst_type = inst.get("instrument_type", "")
            if seg in ("NFO", "BFO") and inst_type in ("OPTIDX", "OPTSTK") and ts.startswith(normalized_underlying):
                return seg
        return "NFO"

    @classmethod
    def _resolve_nearest_expiry(cls, im, normalized_underlying: str, option_type: str, exchange: str) -> str | None:
        from datetime import timezone as dt_timezone
        today = datetime.now(dt_timezone.utc).date()
        expiries: set[str] = set()
        for inst in getattr(im, '_instruments', []) or []:
            ts = inst.get("tradingsymbol", "").upper()
            seg = inst.get("segment", "")
            inst_type = inst.get("instrument_type", "")
            inst_expiry = inst.get("expiry", "")
            inst_strike = inst.get("strike", 0)
            if (seg == exchange and inst_type in ("OPTIDX", "OPTSTK")
                    and ts.startswith(normalized_underlying)
                    and inst_expiry and inst_expiry >= today.isoformat()
                    and inst_strike > 0):
                expiries.add(inst_expiry)
        return sorted(expiries)[0] if expiries else None

    @classmethod
    def _get_strikes_for_expiry(cls, im, normalized_underlying: str, expiry: str, option_type: str, exchange: str) -> list[float]:
        strikes: set[float] = set()
        for inst in getattr(im, '_instruments', []) or []:
            ts = inst.get("tradingsymbol", "").upper()
            seg = inst.get("segment", "")
            inst_type = inst.get("instrument_type", "")
            inst_expiry = inst.get("expiry", "")
            inst_strike = inst.get("strike", 0)
            if (seg == exchange and inst_type in ("OPTIDX", "OPTSTK")
                    and ts.startswith(normalized_underlying)
                    and inst_expiry == expiry
                    and inst_strike > 0):
                strikes.add(float(inst_strike))
        return sorted(strikes)

    @classmethod
    def _nearest_strike(cls, price: float, available_strikes: list[float]) -> float:
        if not available_strikes:
            return 0.0
        return min(available_strikes, key=lambda s: abs(s - price))

    @classmethod
    def _find_instrument(cls, im, normalized_underlying: str, expiry: str, strike: float, option_type: str, exchange: str) -> dict | None:
        interval = STRIKE_INTERVALS.get(normalized_underlying, 50)
        for inst in getattr(im, '_instruments', []) or []:
            ts = inst.get("tradingsymbol", "").upper()
            seg = inst.get("segment", "")
            inst_type = inst.get("instrument_type", "")
            inst_expiry = inst.get("expiry", "")
            inst_strike = inst.get("strike", 0)
            if (seg == exchange and inst_type in ("OPTIDX", "OPTSTK")
                    and ts.startswith(normalized_underlying)
                    and inst_expiry == expiry
                    and abs(float(inst_strike) - strike) < max(float(interval), 1)):
                return inst
        return None

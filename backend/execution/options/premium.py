"""
Premium Fetcher — gets live option premium from Zerodha via the Auto Trade
engine's _zerodha_engine (the authoritative singleton).

Uses the exact broker tradingsymbol resolved by OptionSelector.
Never constructs symbols via string concatenation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from utils.logger import log_info, log_warn


class PremiumFetcher:
    """Fetches option premium from Zerodha or controlled-test fixture."""

    @staticmethod
    async def fetch_premium(
        symbol: str = "",
        option_type: str = "",
        strike: float = 0.0,
        underlying_price: float = 0.0,
        expiry: str = "",
        lot_size: int = 0,
        source: str = "ZERODHA",
        trading_symbol: str = "",
        instrument_token: int = 0,
    ) -> dict[str, Any]:
        """
        Fetch option premium from Zerodha.

        Uses the exact broker tradingsymbol (preferred) or instrument_token
        to request the quote. Never constructs symbols from parts.

        Controlled tests may use source='CONTROLLED_TEST_FIXTURE'.
        """
        is_controlled_test = (source == "CONTROLLED_TEST_FIXTURE")

        if is_controlled_test:
            fixture_premium = round(underlying_price * 0.007, 2)
            log_info("PREMIUM_SOURCE: controlled_test_fixture",
                     symbol=symbol, premium=fixture_premium)
            return {
                "premium": fixture_premium,
                "bid": round(fixture_premium * 0.98, 2),
                "ask": round(fixture_premium * 1.02, 2),
                "source": "CONTROLLED_TEST_FIXTURE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Get the authoritative Kite client from auto_trade._zerodha_engine
        _kite = None
        _ze = None
        try:
            from api.auto_trade import _zerodha_engine as _ze
            if _ze and hasattr(_ze, '_kite_provider') and _ze._kite_provider:
                _kp = _ze._kite_provider
                if hasattr(_kp, 'auth') and _kp.auth:
                    _kite = getattr(_kp.auth, 'kite', None)
        except Exception:
            pass

        if not _kite:
            log_warn("PREMIUM_SOURCE: kite client unavailable", zerodha_engine_available=_ze is not None)
            return {
                "premium": 0.0, "bid": 0, "ask": 0,
                "source": "ZERODHA_KITE_QUOTE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "ZERODHA_SESSION_UNAVAILABLE",
                "error_detail": "Kite client not available from the auto-trade engine.",
            }

        # Determine the quote request key: use trading_symbol if available,
        # otherwise try instrument_token, otherwise construct from parts (last resort)
        quote_key = None
        quote_source = ""
        if trading_symbol:
            # Determine exchange prefix from the trading symbol's instrument
            exch = "NFO"
            try:
                if _ze and hasattr(_ze, '_instrument_manager') and _ze._instrument_manager:
                    im = _ze._instrument_manager
                    inst = im.get_by_symbol(trading_symbol, "NFO") or im.get_by_symbol(trading_symbol, "BFO")
                    if inst:
                        exch = inst.get("exchange", "NFO")
            except Exception:
                pass
            quote_key = f"{exch}:{trading_symbol}"
            quote_source = "tradingsymbol"
        elif instrument_token > 0:
            quote_key = instrument_token
            quote_source = "instrument_token"

        if not quote_key:
            log_warn("PREMIUM_SOURCE: no quote key — no trading_symbol or instrument_token",
                     symbol=symbol, strike=strike, option_type=option_type)
            return {
                "premium": 0.0, "bid": 0, "ask": 0,
                "source": "ZERODHA_KITE_QUOTE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "ZERODHA_OPTION_INSTRUMENT_NOT_FOUND",
                "error_detail": f"No tradingsymbol or instrument token for {symbol} {strike:.0f} {option_type}.",
            }

        # Request the quote
        try:
            log_info("PREMIUM_SOURCE: requesting quote",
                     key=quote_key, source=quote_source)
            quote = _kite.ltp([quote_key]) if isinstance(quote_key, str) else _kite.ltp([str(quote_key)])
        except Exception as e:
            log_warn("PREMIUM_SOURCE: quote request failed",
                     key=str(quote_key)[:40], error=str(e)[:100])
            return {
                "premium": 0.0, "bid": 0, "ask": 0,
                "source": "ZERODHA_KITE_QUOTE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "ZERODHA_QUOTE_API_ERROR",
                "error_detail": f"Quote request failed: {str(e)[:100]}",
            }

        # Parse response
        response_key = str(quote_key) if isinstance(quote_key, str) else quote_key
        try:
            if isinstance(response_key, str) and quote and response_key in quote:
                premium = quote[response_key].get("last_price", 0)
                if premium and premium > 0:
                    log_info("PREMIUM_SOURCE: zerodha quote ok",
                             key=str(quote_key)[:40], premium=premium)
                    return {
                        "premium": premium,
                        "bid": quote[response_key].get("bid", 0),
                        "ask": quote[response_key].get("ask", 0),
                        "source": "ZERODHA_KITE_QUOTE",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
            # Try as integer key if string failed
            if isinstance(quote_key, int) and quote and str(quote_key) in quote:
                premium = quote[str(quote_key)].get("last_price", 0)
                if premium and premium > 0:
                    return {
                        "premium": premium, "bid": 0, "ask": 0,
                        "source": "ZERODHA_KITE_QUOTE",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
        except Exception as e:
            log_warn("PREMIUM_SOURCE: quote response parse error", error=str(e)[:100])

        log_warn("PREMIUM_SOURCE: quote response had no valid premium",
                 key=str(quote_key)[:40], has_response=bool(quote),
                 response_keys=list(quote.keys()) if isinstance(quote, dict) else [])
        return {
            "premium": 0.0, "bid": 0, "ask": 0,
            "source": "ZERODHA_KITE_QUOTE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": "ZERODHA_QUOTE_RESPONSE_KEY_MISMATCH",
            "error_detail": f"Quote response did not contain key {str(quote_key)[:40]}",
        }

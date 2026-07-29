"""
Premium Fetcher — gets live option premium from Zerodha.
Simulated fallback is ONLY allowed when explicitly requested for controlled tests.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from execution.options.selector import OptionSelector
from utils.logger import log_info, log_warn


class PremiumFetcher:
    """Fetches option premium from Zerodha or controlled-test fixture."""

    @staticmethod
    async def fetch_premium(
        symbol: str,
        option_type: str,
        strike: float,
        underlying_price: float,
        expiry: str = "",
        lot_size: int = 0,
        source: str = "ZERODHA",
    ) -> dict[str, Any]:
        """
        Fetch option premium from Zerodha or a controlled-test fixture.

        For normal live-paper operation (source='ZERODHA'):
        - Requires valid Zerodha session
        - Requires real NFO instrument
        - Returns real quote or raises with exact block code

        Controlled tests may use source='CONTROLLED_TEST_FIXTURE'.

        Returns dict with premium, bid, ask, source, timestamp.
        """
        is_controlled_test = (source == "CONTROLLED_TEST_FIXTURE")

        if is_controlled_test:
            # Controlled test: generate a fixture premium
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

        # Try live Zerodha quote
        try:
            from main import zerodha_engine as _ze
            if _ze and hasattr(_ze, '_kite_provider') and _ze._kite_provider:
                kite = getattr(_ze._kite_provider, 'auth', None)
                if kite and hasattr(kite, 'kite') and kite.kite:
                    # Build proper NFO trading symbol
                    # Expected format: NFO:SYMBOLYYMMDDSTRIKETYPE
                    # e.g. NFO:NIFTY26080624800CE
                    expiry_compact = expiry.replace("-", "")[2:] if expiry else ""
                    nfo_symbol = f"NFO:{symbol.upper()}{expiry_compact}{strike:.0f}{option_type}"
                    try:
                        quote = kite.kite.ltp([nfo_symbol])
                        if quote and nfo_symbol in quote:
                            premium = quote[nfo_symbol].get("last_price", 0)
                            if premium and premium > 0:
                                log_info("PREMIUM_SOURCE: zerodha",
                                         symbol=nfo_symbol, premium=premium)
                                return {
                                    "premium": premium,
                                    "bid": quote[nfo_symbol].get("bid", 0),
                                    "ask": quote[nfo_symbol].get("ask", 0),
                                    "source": "ZERODHA_KITE_QUOTE",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                    except Exception as e:
                        log_warn("PREMIUM_SOURCE: zerodha quote failed",
                                 symbol=nfo_symbol, error=str(e)[:100])
        except ImportError:
            pass
        except Exception as e:
            log_warn("PREMIUM_SOURCE: zerodha engine error", error=str(e)[:100])

        # For ZERODHA source, simulated fallback is NOT allowed
        # Return a blocked result with exact code
        ze_available = False
        try:
            from main import zerodha_engine as _ze
            ze_available = _ze is not None
        except Exception:
            ze_available = False

        log_warn("PREMIUM_SOURCE: ZERODHA quote unavailable — blocking",
                 symbol=symbol, strike=strike, option_type=option_type,
                 zerodha_available=ze_available)
        return {
            "premium": 0.0,
            "bid": 0,
            "ask": 0,
            "source": "ZERODHA_KITE_QUOTE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": "ZERODHA_OPTION_QUOTE_UNAVAILABLE",
            "error_detail": (
                f"Could not get Zerodha quote for {symbol} {strike:.0f} {option_type}. "
                f"Zerodha engine available: {ze_available}"
            ),
        }
"""
Premium Fetcher — gets live option premium from Zerodha or simulated fallback.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from execution.options.selector import OptionSelector
from utils.logger import log_info


class PremiumFetcher:
    """Fetches option premium from Zerodha or simulates."""

    @staticmethod
    async def fetch_premium(
        symbol: str,
        option_type: str,
        strike: float,
        underlying_price: float,
        source: str = "simulated",
    ) -> dict[str, Any]:
        """
        Fetch option premium.

        Try Zerodha quote via kite_provider if available.
        Fall back to simulated premium with explicit log.

        Returns dict with premium, bid, ask, source, timestamp.
        """
        # Try live Zerodha quote
        try:
            from services.zerodha_market_data_engine import ZerodhaMarketDataEngine
            # Access the instrument manager via the engine
            # Lazy import to avoid circular dependency
            from main import zerodha_engine as _ze
            if _ze and hasattr(_ze, '_kite_provider') and _ze._kite_provider:
                kite = getattr(_ze._kite_provider, 'auth', None)
                if kite and hasattr(kite, 'kite'):
                    # Build NFO symbol
                    expiry_str = ""  # would come from selector
                    nfo_symbol = f"NFO:{symbol.upper()}{expiry_str}{strike:.0f}{option_type}"
                    try:
                        quote = kite.kite.ltp(f"NFO:{nfo_symbol}")
                        if quote and nfo_symbol in quote:
                            premium = quote[nfo_symbol].get("last_price", 0)
                            if premium > 0:
                                log_info("PREMIUM_SOURCE: zerodha",
                                         symbol=nfo_symbol, premium=premium)
                                return {
                                    "premium": premium,
                                    "bid": 0,
                                    "ask": 0,
                                    "source": "zerodha",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                    except Exception:
                        pass
        except ImportError:
            pass
        except Exception:
            pass

        # Simulated fallback
        atr_fraction = random.uniform(0.003, 0.008)
        simulated_premium = round(underlying_price * atr_fraction, 2)

        log_info("PREMIUM_SOURCE: simulated",
                 symbol=symbol, premium=simulated_premium,
                 underlying_price=underlying_price)

        return {
            "premium": simulated_premium,
            "bid": round(simulated_premium * 0.98, 2),
            "ask": round(simulated_premium * 1.02, 2),
            "source": "simulated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
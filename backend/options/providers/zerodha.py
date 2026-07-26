"""
MarketMind AI — Zerodha Option Chain Provider

Implements OptionDataProvider using Zerodha Kite Connect's option_chain() API.
Requires an authenticated Kite instance (via KiteProvider or standalone).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Any

from options.models import (
    OptionChainSnapshot,
    OptionChainSlice,
    OptionChainSource,
    OptionInstrument,
    OptionQuote,
    OptionType,
)
from options.providers.base import OptionDataProvider, ProviderCapabilities

from utils.logger import log_info, log_warn, log_error


class ZerodhaOptionProvider(OptionDataProvider):
    """
    Option chain data provider backed by Zerodha Kite Connect.

    Usage:
        provider = ZerodhaOptionProvider(kite_provider)
        await provider.connect()
        chain = await provider.fetch_chain_snapshot("NIFTY 50")
    """

    def __init__(self, kite_provider: Any = None):
        self._kite = None
        self._kite_provider = kite_provider
        self._connected = False
        self._last_fetch: datetime | None = None
        self._fetch_count = 0
        self._error_count = 0

    async def connect(self) -> bool:
        """Establish connection. Reuses existing KiteProvider if provided."""
        try:
            if self._kite_provider and hasattr(self._kite_provider, "auth"):
                self._kite = self._kite_provider.auth.kite
                if self._kite and self._kite_provider.auth.is_authenticated:
                    self._connected = True
                    log_info("ZerodhaOptionProvider connected via KiteProvider")
                    return True

            log_warn("ZerodhaOptionProvider: no authenticated Kite instance available")
            return False

        except Exception as e:
            log_error("ZerodhaOptionProvider connect failed", error=str(e))
            return False

    async def disconnect(self) -> None:
        self._connected = False
        self._kite = None
        log_info("ZerodhaOptionProvider disconnected")

    async def health(self) -> dict[str, Any]:
        return {
            "provider": "ZERODHA",
            "connected": self._connected,
            "kite_available": self._kite is not None,
            "fetch_count": self._fetch_count,
            "error_count": self._error_count,
            "last_fetch": (
                self._last_fetch.isoformat() if self._last_fetch else None
            ),
        }

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="ZERODHA",
            source=OptionChainSource.ZERODHA,
            supports_live_chain=True,
            supports_historical=False,
            supports_greeks=False,
            supports_multi_expiry=True,
            underlyings=("NIFTY 50", "BANKNIFTY", "SENSEX"),
        )

    async def fetch_chain_snapshot(
        self,
        underlying: str,
        expiries: list[date] | None = None,
    ) -> OptionChainSnapshot:
        if not self._connected or not self._kite:
            raise RuntimeError("ZerodhaOptionProvider not connected")

        kite_symbol = self._map_symbol(underlying)
        if not kite_symbol:
            raise ValueError(f"Unknown underlying: {underlying}")

        try:
            raw = await asyncio.to_thread(self._kite.option_chain, kite_symbol)
            self._fetch_count += 1
            self._last_fetch = datetime.now(timezone.utc)
        except Exception as e:
            self._error_count += 1
            log_error("ZerodhaOptionProvider fetch_chain failed", error=str(e))
            raise RuntimeError(f"Option chain fetch failed: {e}") from e

        spot_price = 0.0
        expiries_dict: dict[date, OptionChainSlice] = {}

        for expiry_str, instruments in raw.items():
            try:
                expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            if expiries and expiry_dt not in expiries:
                continue

            strikes: list[float] = []
            ce_quotes: dict[float, OptionQuote] = {}
            pe_quotes: dict[float, OptionQuote] = {}

            for inst_data in instruments:
                try:
                    ins_token = int(inst_data.get("instrument_token", 0))
                    ins_strike = float(inst_data.get("strike", 0))
                    ins_type = inst_data.get("instrument_type", "")
                    ins_expiry_str = inst_data.get("expiry", "")
                    ins_trading = inst_data.get("tradingsymbol", "")
                    ins_lot = int(inst_data.get("lot_size", 25))
                    ins_tick = float(inst_data.get("tick_size", 0.05))

                    quote_data = inst_data.get("quote", {})
                    ins_ltp = float(quote_data.get("last_price", 0))
                    ins_oi = int(quote_data.get("oi", 0))
                    ins_vol = int(quote_data.get("volume", 0))
                    ins_bid = float(quote_data.get("bid", 0))
                    ins_ask = float(quote_data.get("ask", 0))

                    if ins_type not in ("CE", "PE"):
                        continue

                    opt_type = OptionType.CE if ins_type == "CE" else OptionType.PE

                    instrument = OptionInstrument(
                        symbol=ins_trading,
                        underlying=underlying,
                        expiry=expiry_dt,
                        strike=ins_strike,
                        option_type=opt_type,
                        exchange="NSE",
                        instrument_token=ins_token,
                        lot_size=ins_lot,
                        tick_size=ins_tick,
                        trading_symbol=ins_trading,
                    )

                    quote = OptionQuote(
                        instrument=instrument,
                        ltp=ins_ltp,
                        bid=ins_bid,
                        ask=ins_ask,
                        oi=ins_oi,
                        volume=ins_vol,
                        timestamp=datetime.now(timezone.utc),
                    )

                    if ins_strike not in strikes:
                        strikes.append(ins_strike)

                    if ins_type == "CE":
                        ce_quotes[ins_strike] = quote
                    else:
                        pe_quotes[ins_strike] = quote

                    # Approximate spot from ATM CE strike
                    if ins_type == "CE" and ins_ltp > 0 and ins_oi > 1000:
                        if spot_price == 0 or abs(ins_strike - spot_price) < abs(
                            ins_strike - spot_price
                        ):
                            spot_price = ins_strike

                except (ValueError, TypeError, KeyError):
                    continue

            if strikes:
                strikes.sort()
                expiries_dict[expiry_dt] = OptionChainSlice(
                    underlying=underlying,
                    expiry=expiry_dt,
                    strikes=strikes,
                    ce_quotes=ce_quotes,
                    pe_quotes=pe_quotes,
                    spot_price=spot_price,
                    fetched_at=datetime.now(timezone.utc),
                    source=OptionChainSource.ZERODHA,
                )

        return OptionChainSnapshot(
            underlying=underlying,
            spot_price=spot_price,
            expiries=expiries_dict,
            fetched_at=datetime.now(timezone.utc),
            source=OptionChainSource.ZERODHA,
        )

    async def fetch_chain_slice(
        self,
        underlying: str,
        expiry: date,
    ) -> OptionChainSlice:
        snapshot = await self.fetch_chain_snapshot(underlying, expiries=[expiry])
        s = snapshot.get_slice(expiry)
        if s is None:
            raise ValueError(f"No data for {underlying} expiry {expiry}")
        return s

    async def fetch_option_quote(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        option_type: str,
    ) -> OptionQuote | None:
        s = await self.fetch_chain_slice(underlying, expiry)
        ot = OptionType.CE if option_type == "CE" else OptionType.PE
        return s.get_quote(strike, ot)

    async def fetch_instruments(
        self,
        underlying: str,
        expiry: date | None = None,
    ) -> list[OptionInstrument]:
        snapshot = await self.fetch_chain_snapshot(underlying)
        instruments: list[OptionInstrument] = []
        target_expiries = [expiry] if expiry else list(snapshot.expiries.keys())
        for exp in target_expiries:
            s = snapshot.get_slice(exp)
            if not s:
                continue
            for q in s.ce_quotes.values():
                instruments.append(q.instrument)
            for q in s.pe_quotes.values():
                instruments.append(q.instrument)
        return instruments

    async def get_available_expiries(
        self,
        underlying: str,
    ) -> list[date]:
        snapshot = await self.fetch_chain_snapshot(underlying)
        return snapshot.available_expiries

    @staticmethod
    def _map_symbol(underlying: str) -> str | None:
        mapping = {
            "NIFTY 50": "NIFTY 50",
            "BANKNIFTY": "NIFTY BANK",
            "BANK NIFTY": "NIFTY BANK",
            "SENSEX": "SENSEX",
        }
        return mapping.get(underlying)

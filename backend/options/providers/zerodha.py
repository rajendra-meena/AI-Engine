"""
MarketMind AI — Zerodha Option Chain Provider

Builds option chains from the real Zerodha Kite Connect API:
  kite.instruments("NFO") → filter by underlying → batch quote → assemble

No synthetic or non-existent API methods are used.
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

# Kite exchange → segment mapping for NFO options
_KITE_EXCHANGE = "NFO"


class ZerodhaOptionProvider(OptionDataProvider):
    """
    Zerodha option chain provider using real Kite SDK methods.
    Uses kite.instruments('NFO') + kite.quote() — no non-existent methods.
    """

    _NSE_SYMBOL_MAP = {
        "NIFTY 50": "NIFTY",
        "BANKNIFTY": "NIFTY BANK",
        "BANK NIFTY": "NIFTY BANK",
        "SENSEX": "SENSEX",
    }

    def __init__(self, kite_provider: Any = None):
        self._kite = None
        self._kite_provider = kite_provider
        self._connected = False
        self._last_fetch: datetime | None = None
        self._fetch_count = 0
        self._error_count = 0
        # Cached NFO instruments — refreshed lazily
        self._nfo_instruments: list[dict[str, Any]] = []
        self._instruments_loaded = False

    async def connect(self) -> bool:
        """Establish connection via existing KiteProvider."""
        try:
            if self._kite_provider and hasattr(self._kite_provider, "auth"):
                self._kite = self._kite_provider.auth.kite
                if self._kite and self._kite_provider.auth.is_authenticated:
                    self._connected = True
                    log_info("ZerodhaOptionProvider connected via KiteProvider")
                    return True
            log_warn("ZerodhaOptionProvider: no authenticated Kite instance")
            return False
        except Exception as e:
            log_error("ZerodhaOptionProvider connect failed", error=str(e))
            return False

    async def disconnect(self) -> None:
        self._connected = False
        self._kite = None
        self._nfo_instruments.clear()
        self._instruments_loaded = False
        log_info("ZerodhaOptionProvider disconnected")

    async def health(self) -> dict[str, Any]:
        return {
            "provider": "ZERODHA",
            "connected": self._connected,
            "kite_available": self._kite is not None,
            "fetch_count": self._fetch_count,
            "error_count": self._error_count,
            "instruments_loaded": self._instruments_loaded,
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

    async def _load_nfo_instruments(self) -> None:
        """Fetch and cache the NFO instrument master via kite.instruments()."""
        if not self._kite:
            raise RuntimeError("ZerodhaOptionProvider not connected")
        self._nfo_instruments = await asyncio.to_thread(
            self._kite.instruments, _KITE_EXCHANGE
        )
        self._instruments_loaded = True
        log_info("ZerodhaOptionProvider: NFO instruments loaded",
                 count=len(self._nfo_instruments))

    def _get_nfo_instruments(self) -> list[dict[str, Any]]:
        return list(self._nfo_instruments)

    async def fetch_chain_snapshot(
        self,
        underlying: str,
        expiries: list[date] | None = None,
    ) -> OptionChainSnapshot:
        if not self._connected or not self._kite:
            raise RuntimeError("ZerodhaOptionProvider not connected")

        name = self._NSE_SYMBOL_MAP.get(underlying)
        if not name:
            raise ValueError(f"Unknown underlying: {underlying}")

        try:
            return await self._do_fetch_chain(name, underlying, expiries)
        except (RuntimeError, ValueError):
            raise
        except Exception as e:
            self._error_count += 1
            raise RuntimeError(f"Option chain fetch failed: {e}") from e

    async def _do_fetch_chain(
        self,
        name: str,
        underlying: str,
        expiries: list[date] | None = None,
    ) -> OptionChainSnapshot:
        # Load NFO instruments if not cached
        if not self._instruments_loaded or not self._nfo_instruments:
            await self._load_nfo_instruments()

        # Filter contracts for this underlying, CE and PE only
        contract_filter = [
            i for i in self._nfo_instruments
            if i.get("name") == name
            and i.get("instrument_type") in ("CE", "PE")
            and i.get("segment") == "NFO-OPT"
        ]

        if not contract_filter:
            log_warn("ZerodhaOptionProvider: no contracts found",
                     underlying=underlying, name=name)
            return OptionChainSnapshot(
                underlying=underlying, spot_price=0.0,
                expiries={}, source=OptionChainSource.ZERODHA,
            )

        # Group by expiry
        by_expiry: dict[date, list[dict[str, Any]]] = {}
        for c in contract_filter:
            exp = c.get("expiry")
            if not exp or not isinstance(exp, date):
                continue
            if expiries and exp not in expiries:
                continue
            by_expiry.setdefault(exp, []).append(c)

        # Build NFO-prefixed tradingsymbols for batch quote lookup
        nfo_symbols: list[str] = []
        symbol_by_token: dict[int, str] = {}
        for exp_conts in by_expiry.values():
            for c in exp_conts:
                tsym = c.get("tradingsymbol", "")
                token = int(c.get("instrument_token", 0))
                if tsym and token:
                    nfosym = f"NFO:{tsym}"
                    nfo_symbols.append(nfosym)
                    symbol_by_token[token] = nfosym

        # Fetch batch quotes via kite.quote() — takes varargs of "EXCHANGE:SYMBOL"
        quote_map: dict[str, dict[str, Any]] = {}
        if nfo_symbols:
            try:
                raw_quotes = await asyncio.to_thread(
                    self._kite.quote, *nfo_symbols
                )
                quote_map = raw_quotes
            except Exception as e:
                log_warn("ZerodhaOptionProvider: batch quote failed", error=str(e))

        # Fallback ltp for tokens without full quotes
        ltp_map: dict[str, float] = {}
        if not quote_map and nfo_symbols:
            try:
                raw_ltps = await asyncio.to_thread(
                    self._kite.ltp, *nfo_symbols
                )
                for sym in nfo_symbols:
                    lt = raw_ltps.get(sym, {})
                    ltp_map[sym] = lt.get("last_price", 0)
            except Exception as e:
                log_warn("ZerodhaOptionProvider: batch ltp failed", error=str(e))

        def _get_qdata(token_id: int) -> dict[str, Any]:
            """Look up quote data by token using NFO:symbol map key."""
            qsym = symbol_by_token.get(token_id)
            if qsym:
                return quote_map.get(qsym, {})
            return {}

        spot_price = 0.0
        slices: dict[date, OptionChainSlice] = {}

        for expiry_dt, conts in sorted(by_expiry.items()):
            strikes_list: list[float] = []
            ce_quotes: dict[float, OptionQuote] = {}
            pe_quotes: dict[float, OptionQuote] = {}

            for c in conts:
                try:
                    token_id = int(c.get("instrument_token", 0))
                    strike = float(c.get("strike", 0))
                    ins_type = c.get("instrument_type", "")
                    tradingsymbol = c.get("tradingsymbol", "")
                    lot_size = int(c.get("lot_size", 0))
                    tick_size = float(c.get("tick_size", 0.05))

                    if strike <= 0:
                        continue

                    opt_type = OptionType.CE if ins_type == "CE" else OptionType.PE

                    # Get quote data via NFO:symbol key
                    qdata = _get_qdata(token_id)
                    ltp_val = float(qdata.get("last_price", ltp_map.get(symbol_by_token.get(token_id, ""), 0)))
                    oi_val = int(qdata.get("oi", 0))
                    vol_val = int(qdata.get("volume", 0))
                    bid_val = 0.0
                    ask_val = 0.0
                    depth = qdata.get("depth", {})
                    if depth:
                        bid_data = depth.get("bid", [{}])
                        ask_data = depth.get("offer", [{}])
                        if bid_data and isinstance(bid_data, list):
                            bid_val = float(bid_data[0].get("price", 0)) if bid_data else 0
                        if ask_data and isinstance(ask_data, list):
                            ask_val = float(ask_data[0].get("price", 0)) if ask_data else 0

                    instrument = OptionInstrument(
                        symbol=tradingsymbol,
                        underlying=underlying,
                        expiry=expiry_dt,
                        strike=strike,
                        option_type=opt_type,
                        exchange="NFO",
                        instrument_token=token,
                        lot_size=lot_size,
                        tick_size=tick_size,
                        trading_symbol=tradingsymbol,
                    )

                    quote = OptionQuote(
                        instrument=instrument,
                        ltp=ltp_val,
                        bid=bid_val,
                        ask=ask_val,
                        oi=oi_val,
                        volume=vol_val,
                        timestamp=datetime.now(timezone.utc),
                    )

                    if strike not in strikes_list:
                        strikes_list.append(strike)

                    if ins_type == "CE":
                        ce_quotes[strike] = quote
                    else:
                        pe_quotes[strike] = quote

                    # Approximate spot price from nearest-to-ATM LTP option
                    if ins_type == "CE" and ltp_val > 0:
                        if spot_price == 0:
                            spot_price = strike
                        elif abs(strike - spot_price) < abs(strike - spot_price):
                            spot_price = strike

                except (ValueError, TypeError, KeyError):
                    continue

            if strikes_list:
                strikes_list.sort()
                slices[expiry_dt] = OptionChainSlice(
                    underlying=underlying,
                    expiry=expiry_dt,
                    strikes=strikes_list,
                    ce_quotes=ce_quotes,
                    pe_quotes=pe_quotes,
                    spot_price=spot_price,
                    fetched_at=datetime.now(timezone.utc),
                    source=OptionChainSource.ZERODHA,
                )

        self._fetch_count += 1
        self._last_fetch = datetime.now(timezone.utc)
        return OptionChainSnapshot(
            underlying=underlying,
            spot_price=spot_price,
            expiries=slices,
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

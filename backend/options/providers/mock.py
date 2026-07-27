"""
MarketMind AI — Mock Option Chain Provider

Deterministic, in-memory option chain provider for unit testing.
No external dependencies. Generates realistic chain data around a configurable spot.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Any

from options.models import (
    OptionChainSnapshot,
    OptionChainSlice,
    OptionChainSource,
    OptionInstrument,
    OptionQuote,
    OptionType,
    DEFAULT_LOT_SIZES,
)
from options.providers.base import OptionDataProvider, ProviderCapabilities

from utils.logger import log_info


def _strike_range(spot: float, count: int = 21, step: float = 50.0) -> list[float]:
    """Generate symmetric strike range around spot."""
    half = count // 2
    base = round(spot / step) * step
    return [base + (i - half) * step for i in range(count)]


class MockOptionProvider(OptionDataProvider):
    """
    Deterministic option chain provider for testing.

    Generates a realistic option chain around a configurable spot price.
    All data is in-memory; no external calls.

    Usage:
        provider = MockOptionProvider(spot=24500.0)
        await provider.connect()
        chain = await provider.fetch_chain_snapshot("NIFTY 50")
    """

    def __init__(
        self,
        spot: float = 24500.0,
        base_volatility: float = 18.0,
        base_oi: int = 5000,
        base_volume: int = 500,
        expiry_days: list[int] | None = None,
        stale_offset_seconds: float = 0.0,
        fail_next_fetch: bool = False,
        fail_next_chain_fetch: bool = False,
        empty_chain: bool = False,
        malformed_chain: bool = False,
    ):
        self._spot = spot
        self._base_vol = base_volatility
        self._base_oi = base_oi
        self._base_volume = base_volume  # renamed: was overwriting _base_vol
        self._expiry_days = expiry_days or [3, 10, 17, 24]
        self._connected = False
        self._fetch_count = 0
        self._request_log: list[dict[str, Any]] = []
        self._stale_offset_seconds = stale_offset_seconds
        self._fail_next_fetch = fail_next_fetch  # fails fetch_chain_snapshot only
        self._fail_next_chain_fetch = fail_next_chain_fetch  # fails fetch_chain_snapshot only (alt name)
        self._fail_next_instruments = False  # fails fetch_instruments only
        self._empty_chain = empty_chain
        self._malformed_chain = malformed_chain

    async def connect(self) -> bool:
        self._connected = True
        log_info("MockOptionProvider connected", spot=self._spot)
        return True

    async def disconnect(self) -> None:
        self._connected = False
        log_info("MockOptionProvider disconnected")

    async def health(self) -> dict[str, Any]:
        return {
            "provider": "MOCK",
            "connected": self._connected,
            "spot": self._spot,
            "fetch_count": self._fetch_count,
            "request_log_size": len(self._request_log),
        }

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="MOCK",
            source=OptionChainSource.MOCK,
            supports_live_chain=True,
            supports_historical=False,
            supports_greeks=False,
            supports_multi_expiry=True,
            underlyings=("NIFTY 50", "BANKNIFTY", "SENSEX"),
        )

    def set_spot(self, spot: float) -> None:
        self._spot = spot

    def set_stale_offset(self, seconds: float) -> None:
        self._stale_offset_seconds = seconds

    def set_fail_next_fetch(self, fail: bool = True) -> None:
        """Fail the next fetch_chain_snapshot call."""
        self._fail_next_fetch = fail

    def set_fail_next_chain_fetch(self, fail: bool = True) -> None:
        """Fail the next fetch_chain_snapshot call (alt name)."""
        self._fail_next_chain_fetch = fail

    def set_fail_next_instruments(self, fail: bool = True) -> None:
        """Fail the next fetch_instruments call."""
        self._fail_next_instruments = fail

    def set_empty_chain(self, empty: bool = True) -> None:
        self._empty_chain = empty

    def set_malformed_chain(self, malformed: bool = True) -> None:
        self._malformed_chain = malformed

    def get_request_log(self) -> list[dict[str, Any]]:
        return list(self._request_log)

    async def fetch_chain_snapshot(
        self,
        underlying: str,
        expiries: list[date] | None = None,
    ) -> OptionChainSnapshot:
        self._request_log.append(
            {
                "method": "fetch_chain_snapshot",
                "underlying": underlying,
                "expiries": [e.isoformat() for e in (expiries or [])],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._fetch_count += 1

        if self._fail_next_fetch:
            self._fail_next_fetch = False
            raise RuntimeError("Mock provider forced fetch failure")

        if self._fail_next_chain_fetch:
            self._fail_next_chain_fetch = False
            raise RuntimeError("Mock provider forced chain fetch failure")

        fetched_at = datetime.now(timezone.utc)
        if self._stale_offset_seconds > 0:
            fetched_at = fetched_at - __import__("datetime").timedelta(seconds=self._stale_offset_seconds)

        if self._empty_chain:
            return OptionChainSnapshot(
                underlying=underlying,
                spot_price=self._spot,
                expiries={},
                fetched_at=fetched_at,
                source=OptionChainSource.MOCK,
            )

        if self._malformed_chain:
            return OptionChainSnapshot(
                underlying=underlying,
                spot_price=-1,
                expiries={},
                fetched_at=fetched_at,
                source=OptionChainSource.MOCK,
            )

        today = date.today()
        expiry_dates = [
            today + timedelta(days=d) for d in self._expiry_days
        ]
        if expiries:
            expiry_dates = [e for e in expiry_dates if e in expiries]

        lot_size = DEFAULT_LOT_SIZES.get(underlying, 25)
        strikes = _strike_range(self._spot)

        slices: dict[date, OptionChainSlice] = {}
        for exp in expiry_dates:
            dte = max((exp - today).days, 1)
            ce_quotes = self._build_quotes(
                underlying, exp, strikes, OptionType.CE, dte, lot_size
            )
            pe_quotes = self._build_quotes(
                underlying, exp, strikes, OptionType.PE, dte, lot_size
            )
            slices[exp] = OptionChainSlice(
                underlying=underlying,
                expiry=exp,
                strikes=strikes,
                ce_quotes=ce_quotes,
                pe_quotes=pe_quotes,
                spot_price=self._spot,
                fetched_at=fetched_at,
                source=OptionChainSource.MOCK,
            )

        return OptionChainSnapshot(
            underlying=underlying,
            spot_price=self._spot,
            expiries=slices,
            fetched_at=fetched_at,
            source=OptionChainSource.MOCK,
        )

    async def fetch_chain_slice(
        self,
        underlying: str,
        expiry: date,
    ) -> OptionChainSlice:
        snapshot = await self.fetch_chain_snapshot(underlying, expiries=[expiry])
        s = snapshot.get_slice(expiry)
        if s is None:
            raise ValueError(f"No mock data for {underlying} expiry {expiry}")
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
        if self._fail_next_instruments:
            self._fail_next_instruments = False
            raise RuntimeError("Mock provider forced instruments fetch failure")

        # Build instruments from scratch without consuming the chain fetch fail flag
        today = date.today()
        expiry_dates = [today + timedelta(days=d) for d in self._expiry_days]
        lot_size = DEFAULT_LOT_SIZES.get(underlying, 25)
        strikes = _strike_range(self._spot)

        instruments: list[OptionInstrument] = []
        target_expiries = [expiry] if expiry else expiry_dates
        for exp in target_expiries:
            dte = max((exp - today).days, 1)
            for strike in strikes:
                for opt_type in (OptionType.CE, OptionType.PE):
                    h = int(hashlib.md5(f"{underlying}:{exp}:{strike}:{opt_type.value}".encode()).hexdigest()[:8], 16)
                    instrument = OptionInstrument(
                        symbol=f"{underlying} {exp.strftime('%d%b').upper()} {strike:.0f} {opt_type.value}",
                        underlying=underlying,
                        expiry=exp,
                        strike=strike,
                        option_type=opt_type,
                        exchange="NSE",
                        instrument_token=h % 1_000_000,
                        lot_size=lot_size,
                        tick_size=0.05,
                        trading_symbol=f"{underlying} {exp.strftime('%d%b').upper()} {strike:.0f} {opt_type.value}",
                    )
                    instruments.append(instrument)
        return instruments

    async def get_available_expiries(
        self,
        underlying: str,
    ) -> list[date]:
        today = date.today()
        return [today + timedelta(days=d) for d in self._expiry_days]

    def _build_quotes(
        self,
        underlying: str,
        expiry: date,
        strikes: list[float],
        option_type: OptionType,
        dte: int,
        lot_size: int,
    ) -> dict[float, OptionQuote]:
        result: dict[float, OptionQuote] = {}
        for strike in strikes:
            moneyness = (strike - self._spot) / self._spot if option_type == OptionType.CE else (self._spot - strike) / self._spot
            distance_pct = abs(moneyness) * 100

            intrinsic = max(
                (self._spot - strike) if option_type == OptionType.CE else (strike - self._spot),
                0,
            )
            time_value = max(self._spot * (self._base_vol / 100) * (dte / 365) ** 0.5 * max(1.0 - abs(moneyness) * 2, 0.3), 0.1)
            premium = round(intrinsic + time_value, 2)
            premium = max(premium, 0.05)

            seed = f"{underlying}:{expiry}:{strike}:{option_type.value}"
            h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
            oi = max(self._base_oi - int(distance_pct * 100) + (h % 1000), 50)
            vol = max(self._base_volume - int(distance_pct * 50) + (h % 200), 10)
            spread = round(max(0.1, premium * 0.02), 2)

            instrument = OptionInstrument(
                symbol=f"{underlying} {expiry.strftime('%d%b').upper()} {strike:.0f} {option_type.value}",
                underlying=underlying,
                expiry=expiry,
                strike=strike,
                option_type=option_type,
                exchange="NSE",
                instrument_token=h % 1_000_000,
                lot_size=lot_size,
                trading_symbol=f"{underlying} {expiry.strftime('%d%b').upper()} {strike:.0f} {option_type.value}",
            )

            quote = OptionQuote(
                instrument=instrument,
                ltp=premium,
                bid=round(max(premium - spread / 2, 0.05), 2),
                ask=round(premium + spread / 2, 2),
                oi=oi,
                volume=vol,
                timestamp=datetime.now(timezone.utc),
            )
            result[strike] = quote
        return result

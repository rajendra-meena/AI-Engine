"""
MarketMind AI — Options Engine Configuration

Validated settings loaded from environment variables with safe defaults.
All option-engine-specific knobs live here.  No credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from options.models import DEFAULT_LOT_SIZES


@dataclass(frozen=True)
class OptionEngineConfig:
    """Immutable, validated configuration for the Options Buying Engine."""

    # ── Provider ──
    provider: str = "MOCK"  # "ZERODHA" or "MOCK"

    # ── Underlying Universe ──
    underlyings: tuple[str, ...] = ("NIFTY 50", "BANKNIFTY")
    lot_sizes: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_LOT_SIZES))

    # ── Chain Freshness ──
    chain_max_age_seconds: float = 15.0
    chain_poll_interval_seconds: float = 5.0
    chain_stale_after_seconds: float = 60.0
    instrument_refresh_interval_seconds: float = 300.0
    provider_timeout_seconds: float = 10.0
    provider_error_initial_backoff_seconds: float = 2.0
    provider_error_max_backoff_seconds: float = 60.0
    market_closed_poll_interval_seconds: float = 300.0

    # ── AI Decision Freshness ──
    ai_max_age_seconds: float = 30.0
    require_analysis_cycle_id: bool = True

    # ── Strike Selection ──
    otm_range: tuple[float, float] = (0.5, 3.0)  # OTM% range to consider
    min_oi: int = 500
    min_volume: int = 100
    max_spread_pct: float = 5.0

    # ── Risk / Sizing ──
    max_capital_per_trade: float = 50_000.0
    max_daily_loss_pct: float = 3.0
    max_positions_per_underlying: int = 1
    max_total_positions: int = 3

    # ── Entry / Exit ──
    default_sl_pct: float = 20.0
    default_target_1_pct: float = 40.0
    default_target_2_pct: float = 80.0
    default_trail_trigger_pct: float = 30.0
    default_trail_offset_pct: float = 10.0
    min_rr: float = 2.0
    min_confidence: float = 0.5

    # ── Invalidation ──
    decision_ttl_seconds: float = 60.0
    reentry_cooldown_seconds: float = 300.0

    # ── Shadow / Paper ──
    shadow_enabled: bool = True
    real_orders_blocked: bool = True

    # ── Timeframe Filtering ──
    allowed_timeframes: tuple[str, ...] = ("INTRADAY",)

    # ── Logging ──
    log_decisions: bool = True
    log_chain_snapshots: bool = False

    def __post_init__(self) -> None:
        # Provider validation
        valid_providers = {"ZERODHA", "MOCK"}
        if self.provider.upper() not in valid_providers:
            raise ValueError(
                f"provider must be one of {valid_providers}, got {self.provider!r}"
            )
        # Lot sizes validation
        for sym, lot in self.lot_sizes.items():
            if lot <= 0:
                raise ValueError(f"lot_sizes[{sym!r}] must be > 0, got {lot}")
        # Range validation
        if len(self.otm_range) != 2 or self.otm_range[0] >= self.otm_range[1]:
            raise ValueError(
                f"otm_range must be (low, high) with low < high, got {self.otm_range}"
            )
        # Risk validation
        if self.max_capital_per_trade <= 0:
            raise ValueError("max_capital_per_trade must be > 0")
        if not (0.0 < self.max_daily_loss_pct <= 100.0):
            raise ValueError("max_daily_loss_pct must be in (0, 100]")
        if not (0.0 < self.min_confidence <= 1.0):
            raise ValueError("min_confidence must be in (0, 1.0]")
        # Freshness validation
        if self.chain_poll_interval_seconds <= 0:
            raise ValueError("chain_poll_interval_seconds must be > 0")
        if self.chain_max_age_seconds <= 0:
            raise ValueError("chain_max_age_seconds must be > 0")
        if self.chain_stale_after_seconds < self.chain_max_age_seconds:
            raise ValueError(
                f"chain_stale_after_seconds ({self.chain_stale_after_seconds}) "
                f"must be >= chain_max_age_seconds ({self.chain_max_age_seconds})"
            )
        if self.provider_timeout_seconds <= 0:
            raise ValueError("provider_timeout_seconds must be > 0")

    def get_lot_size(self, underlying: str) -> int:
        return self.lot_sizes.get(underlying, 25)

    @classmethod
    def from_env(cls) -> OptionEngineConfig:
        """Build config from environment variables, falling back to defaults."""
        raw_provider = os.getenv("OPTIONS_ENGINE_PROVIDER", "MOCK").upper()
        raw_underlyings = os.getenv("OPTIONS_ENGINE_UNDERLYINGS", "NIFTY 50,BANKNIFTY")
        underlyings = tuple(s.strip() for s in raw_underlyings.split(",") if s.strip())

        return cls(
            provider=raw_provider,
            underlyings=underlyings,
            chain_max_age_seconds=float(
                os.getenv("OPTIONS_CHAIN_MAX_AGE_SECONDS", "15")
            ),
            chain_poll_interval_seconds=float(
                os.getenv("OPTIONS_CHAIN_POLL_INTERVAL_SECONDS", "5")
            ),
            chain_stale_after_seconds=float(
                os.getenv("OPTIONS_CHAIN_STALE_AFTER_SECONDS", "60")
            ),
            instrument_refresh_interval_seconds=float(
                os.getenv("OPTIONS_INSTRUMENT_REFRESH_INTERVAL_SECONDS", "300")
            ),
            provider_timeout_seconds=float(
                os.getenv("OPTIONS_PROVIDER_TIMEOUT_SECONDS", "10")
            ),
            provider_error_initial_backoff_seconds=float(
                os.getenv("OPTIONS_PROVIDER_ERROR_INITIAL_BACKOFF_SECONDS", "2")
            ),
            provider_error_max_backoff_seconds=float(
                os.getenv("OPTIONS_PROVIDER_ERROR_MAX_BACKOFF_SECONDS", "60")
            ),
            market_closed_poll_interval_seconds=float(
                os.getenv("OPTIONS_MARKET_CLOSED_POLL_INTERVAL_SECONDS", "300")
            ),
            ai_max_age_seconds=float(os.getenv("OPTIONS_AI_MAX_AGE_SECONDS", "30")),
            min_oi=int(os.getenv("OPTIONS_MIN_OI", "500")),
            min_volume=int(os.getenv("OPTIONS_MIN_VOLUME", "100")),
            max_spread_pct=float(os.getenv("OPTIONS_MAX_SPREAD_PCT", "5")),
            max_capital_per_trade=float(
                os.getenv("OPTIONS_MAX_CAPITAL_PER_TRADE", "50000")
            ),
            max_daily_loss_pct=float(
                os.getenv("OPTIONS_MAX_DAILY_LOSS_PCT", "3")
            ),
            max_positions_per_underlying=int(
                os.getenv("OPTIONS_MAX_POSITIONS_PER_UNDERLYING", "1")
            ),
            max_total_positions=int(os.getenv("OPTIONS_MAX_TOTAL_POSITIONS", "3")),
            default_sl_pct=float(os.getenv("OPTIONS_DEFAULT_SL_PCT", "20")),
            default_target_1_pct=float(
                os.getenv("OPTIONS_DEFAULT_TARGET_1_PCT", "40")
            ),
            default_target_2_pct=float(
                os.getenv("OPTIONS_DEFAULT_TARGET_2_PCT", "80")
            ),
            default_trail_trigger_pct=float(
                os.getenv("OPTIONS_DEFAULT_TRAIL_TRIGGER_PCT", "30")
            ),
            default_trail_offset_pct=float(
                os.getenv("OPTIONS_DEFAULT_TRAIL_OFFSET_PCT", "10")
            ),
            min_rr=float(os.getenv("OPTIONS_MIN_RR", "2")),
            min_confidence=float(os.getenv("OPTIONS_MIN_CONFIDENCE", "0.5")),
            decision_ttl_seconds=float(
                os.getenv("OPTIONS_DECISION_TTL_SECONDS", "60")
            ),
            reentry_cooldown_seconds=float(
                os.getenv("OPTIONS_REENTRY_COOLDOWN_SECONDS", "300")
            ),
            shadow_enabled=os.getenv("OPTIONS_SHADOW_ENABLED", "true").lower()
            == "true",
            real_orders_blocked=os.getenv("OPTIONS_REAL_ORDERS_BLOCKED", "true").lower()
            == "true",
            log_decisions=os.getenv("OPTIONS_LOG_DECISIONS", "true").lower() == "true",
            log_chain_snapshots=os.getenv("OPTIONS_LOG_CHAIN_SNAPSHOTS", "false").lower()
            == "true",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize config for API responses and logging."""
        return {
            "provider": self.provider,
            "underlyings": list(self.underlyings),
            "chain_max_age_seconds": self.chain_max_age_seconds,
            "chain_poll_interval_seconds": self.chain_poll_interval_seconds,
            "chain_stale_after_seconds": self.chain_stale_after_seconds,
            "instrument_refresh_interval_seconds": self.instrument_refresh_interval_seconds,
            "provider_timeout_seconds": self.provider_timeout_seconds,
            "ai_max_age_seconds": self.ai_max_age_seconds,
            "min_oi": self.min_oi,
            "min_volume": self.min_volume,
            "max_spread_pct": self.max_spread_pct,
            "max_capital_per_trade": self.max_capital_per_trade,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_positions_per_underlying": self.max_positions_per_underlying,
            "max_total_positions": self.max_total_positions,
            "default_sl_pct": self.default_sl_pct,
            "default_target_1_pct": self.default_target_1_pct,
            "default_target_2_pct": self.default_target_2_pct,
            "min_rr": self.min_rr,
            "min_confidence": self.min_confidence,
            "decision_ttl_seconds": self.decision_ttl_seconds,
            "reentry_cooldown_seconds": self.reentry_cooldown_seconds,
            "shadow_enabled": self.shadow_enabled,
            "real_orders_blocked": self.real_orders_blocked,
        }

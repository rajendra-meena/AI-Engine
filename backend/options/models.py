"""
MarketMind AI — Options Engine Domain Models

Immutable domain objects for options analysis, decisions, positions, and execution.
All models are validated at construction via __post_init__.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from enum import Enum
from typing import Any


# ── Enums ──


class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


class OptionDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class OptionDecisionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    EXECUTED = "EXECUTED"


class OptionPositionStatus(str, Enum):
    PENDING_ENTRY = "PENDING_ENTRY"
    OPEN = "OPEN"
    SL_HIT = "SL_HIT"
    TARGET_HIT = "TARGET_HIT"
    TRAIL_EXIT = "TRAIL_EXIT"
    DECAY_EXIT = "DECAY_EXIT"
    MANUAL_EXIT = "MANUAL_EXIT"
    EXPIRED = "EXPIRED"


class OptionChainSource(str, Enum):
    ZERODHA = "ZERODHA"
    MOCK = "MOCK"


class OptionTimeframe(str, Enum):
    INTRADAY = "INTRADAY"
    SWING = "SWING"
    POSITIONAL = "POSITIONAL"


class FreshnessState(str, Enum):
    UNKNOWN = "UNKNOWN"
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class ReadinessStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    LOADING_INSTRUMENTS = "LOADING_INSTRUMENTS"
    WAITING_FOR_CHAIN = "WAITING_FOR_CHAIN"
    READY = "READY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    STOPPED = "STOPPED"


# ── Underlying Instruments ──

# Indian index lot sizes — validated against live NSE data in production.
# These are the hard-coded fallback defaults for unit testing and mock mode.
DEFAULT_LOT_SIZES: dict[str, int] = {
    "NIFTY 50": 25,
    "BANKNIFTY": 15,
    "SENSEX": 20,
    "FINNIFTY": 40,
    "MIDCPNIFTY": 75,
}

WEEKLY_EXPIRY_WEEKDAY = 3  # Thursday (0=Mon, 3=Thu)


# ── Core Models ──


@dataclass(frozen=True, slots=True)
class UnderlyingSnapshot:
    """Point-in-time snapshot of the underlying instrument for the decision engine."""

    symbol: str
    ltp: float
    prev_close: float
    day_open: float
    day_high: float
    day_low: float
    day_volume: int
    oi_change_pct: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.ltp <= 0:
            raise ValueError(f"ltp must be positive, got {self.ltp}")
        if self.day_high < self.day_low:
            raise ValueError("day_high must be >= day_low")

    @property
    def day_range(self) -> float:
        return self.day_high - self.day_low

    @property
    def prev_day_range(self) -> float:
        return self.day_high - self.day_low


@dataclass(frozen=True, slots=True)
class OptionInstrument:
    """A single option contract identified by its key attributes."""

    symbol: str
    underlying: str
    expiry: date
    strike: float
    option_type: OptionType
    exchange: str = "NSE"
    instrument_token: int = 0
    lot_size: int = 25
    tick_size: float = 0.05
    trading_symbol: str = ""

    def __post_init__(self):
        if self.strike < 0:
            raise ValueError(f"strike must be non-negative, got {self.strike}")
        if self.lot_size <= 0:
            raise ValueError(f"lot_size must be positive, got {self.lot_size}")

    @property
    def key(self) -> str:
        """Unique key for this instrument: UNDERLYING-EXPIRY-STRIKE-TYPE."""
        return (
            f"{self.underlying}-{self.expiry.isoformat()}-"
            f"{self.strike:.0f}-{self.option_type.value}"
        )


@dataclass(frozen=True, slots=True)
class OptionQuote:
    """Live or mock quote for an option instrument."""

    instrument: OptionInstrument
    ltp: float
    bid: float = 0.0
    ask: float = 0.0
    oi: int = 0
    volume: int = 0
    iv: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.ltp < 0:
            raise ValueError(f"ltp must be non-negative, got {self.ltp}")
        if self.oi < 0:
            raise ValueError(f"oi must be non-negative, got {self.oi}")
        if self.volume < 0:
            raise ValueError(f"volume must be non-negative, got {self.volume}")

    @property
    def spread(self) -> float:
        if self.ask <= 0 or self.bid <= 0:
            return 0.0
        return self.ask - self.bid

    @property
    def is_tradeable(self) -> bool:
        return self.ltp > 0 and self.oi > 0


@dataclass(frozen=True, slots=True)
class OptionChainSlice:
    """A slice of the option chain: all strikes for a single expiry."""

    underlying: str
    expiry: date
    strikes: list[float]
    ce_quotes: dict[float, OptionQuote]
    pe_quotes: dict[float, OptionQuote]
    spot_price: float
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: OptionChainSource = OptionChainSource.ZERODHA

    def __post_init__(self):
        if not self.strikes:
            raise ValueError("strikes list must not be empty")

    def get_quote(self, strike: float, option_type: OptionType) -> OptionQuote | None:
        if option_type == OptionType.CE:
            return self.ce_quotes.get(strike)
        return self.pe_quotes.get(strike)

    def atm_strike(self) -> float:
        closest = min(self.strikes, key=lambda s: abs(s - self.spot_price))
        return closest

    def otm_strikes(self, option_type: OptionType, count: int = 5) -> list[OptionQuote]:
        quotes = self.ce_quotes if option_type == OptionType.CE else self.pe_quotes
        if option_type == OptionType.CE:
            otm = [q for s, q in quotes.items() if s > self.spot_price]
        else:
            otm = [q for s, q in quotes.items() if s < self.spot_price]
        otm.sort(key=lambda q: q.instrument.strike)
        return otm[:count]

    def itm_strikes(self, option_type: OptionType, count: int = 3) -> list[OptionQuote]:
        quotes = self.ce_quotes if option_type == OptionType.CE else self.pe_quotes
        if option_type == OptionType.CE:
            itm = [q for s, q in quotes.items() if s <= self.spot_price]
        else:
            itm = [q for s, q in quotes.items() if s >= self.spot_price]
        itm.sort(key=lambda q: q.instrument.strike, reverse=True)
        return itm[:count]


@dataclass(frozen=True, slots=True)
class OptionChainSnapshot:
    """Full option chain across multiple expiries for a single underlying."""

    underlying: str
    spot_price: float
    expiries: dict[date, OptionChainSlice]
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: OptionChainSource = OptionChainSource.ZERODHA

    @property
    def available_expiries(self) -> list[date]:
        return sorted(self.expiries.keys())

    def get_slice(self, expiry: date) -> OptionChainSlice | None:
        return self.expiries.get(expiry)

    def nearest_expiry(self) -> date | None:
        if not self.expiries:
            return None
        today = date.today()
        future = [e for e in self.expiries if e >= today]
        if not future:
            return min(self.expiries.keys())
        return min(future)


@dataclass(slots=True)
class OptionStrikeAnalysis:
    """Analysis result for a single strike, produced by the strike analyzer."""

    strike: float
    option_type: OptionType
    option_quote: OptionQuote
    underlying_snapshot: UnderlyingSnapshot
    itm_pct: float = 0.0
    otm_pct: float = 0.0
    distance_from_atm: int = 0
    oi_rank: int = 0
    volume_rank: int = 0
    iv_rank: float = 0.0
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.option_type == OptionType.CE:
            self.otm_pct = (
                ((self.strike - self.underlying_snapshot.ltp) / self.underlying_snapshot.ltp * 100)
                if self.underlying_snapshot.ltp > 0
                else 0.0
            )
        else:
            self.otm_pct = (
                ((self.underlying_snapshot.ltp - self.strike) / self.underlying_snapshot.ltp * 100)
                if self.underlying_snapshot.ltp > 0
                else 0.0
            )
        self.itm_pct = -self.otm_pct if self.otm_pct < 0 else 0.0


@dataclass(frozen=True, slots=True)
class OptionDecision:
    """A validated option trade decision ready for risk sizing."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    analysis_cycle_id: str = ""
    underlying: str = ""
    underlying_ltp: float = 0.0
    option_type: OptionType = OptionType.CE
    direction: OptionDirection = OptionDirection.LONG
    strike: float = 0.0
    expiry: date = field(default_factory=date.today)
    option_quote: OptionQuote | None = None
    timeframe: OptionTimeframe = OptionTimeframe.INTRADAY
    confidence: float = 0.0
    entry_price: float = 0.0
    sl_price: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    trail_trigger: float = 0.0
    trail_offset: float = 0.0
    risk_reward: float = 0.0
    status: OptionDecisionStatus = OptionDecisionStatus.PENDING
    reject_reason: str = ""
    strategy_version: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.strike < 0:
            raise ValueError(f"strike must be non-negative, got {self.strike}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    @property
    def idempotency_key(self) -> str:
        return (
            f"{self.analysis_cycle_id}:{self.underlying}:{self.expiry.isoformat()}:"
            f"{self.strike:.0f}:{self.option_type.value}:{self.strategy_version}"
        )

    @property
    def is_approved(self) -> bool:
        return self.status == OptionDecisionStatus.APPROVED

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass(slots=True)
class OptionPosition:
    """An active or closed option position with P&L tracking."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    decision_id: str = ""
    underlying: str = ""
    option_type: OptionType = OptionType.CE
    direction: OptionDirection = OptionDirection.LONG
    strike: float = 0.0
    expiry: date = field(default_factory=date.today)
    lot_size: int = 25
    quantity: int = 0
    entry_price: float = 0.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: OptionPositionStatus = OptionPositionStatus.PENDING_ENTRY
    sl_price: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    trail_trigger: float = 0.0
    trail_offset: float = 0.0
    current_price: float = 0.0
    highest_premium: float = 0.0
    lowest_premium: float = float("inf")
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    exit_price: float = 0.0
    exit_time: datetime | None = None
    exit_reason: str = ""
    option_quote_at_entry: OptionQuote | None = None

    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError(f"quantity must be non-negative, got {self.quantity}")
        if self.lot_size <= 0:
            raise ValueError(f"lot_size must be positive, got {self.lot_size}")

    def update_pnl(self, current_price: float) -> None:
        self.current_price = current_price
        self.highest_premium = max(self.highest_premium, current_price)
        self.lowest_premium = min(self.lowest_premium, current_price)
        if self.direction == OptionDirection.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity

    @property
    def total_cost(self) -> float:
        return self.entry_price * self.quantity

    @property
    def pnl_pct(self) -> float:
        if self.total_cost <= 0:
            return 0.0
        return (self.unrealized_pnl / self.total_cost) * 100

    @property
    def is_open(self) -> bool:
        return self.status == OptionPositionStatus.OPEN

    def close(self, price: float, reason: str) -> None:
        self.exit_price = price
        self.exit_time = datetime.now(timezone.utc)
        self.exit_reason = reason
        self.update_pnl(price)
        self.realized_pnl = self.unrealized_pnl
        self.status = OptionPositionStatus.MANUAL_EXIT


@dataclass(frozen=True, slots=True)
class OptionRiskCheck:
    """Result of pre-trade risk validation."""

    allowed: bool
    max_lots: int
    capital_per_lot: float
    max_capital: float
    margin_required: float
    reason: str = ""
    breaker_active: bool = False
    daily_loss_remaining: float = 0.0


@dataclass(frozen=True, slots=True)
class OptionSizing:
    """Position sizing result for an option trade."""

    lots: int
    quantity: int
    capital_required: float
    margin_required: float
    risk_amount: float
    risk_pct: float
    method: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OptionChainFreshness:
    """Tracks how stale an option chain snapshot is."""

    underlying: str
    fetched_at: datetime
    max_age_seconds: float = 15.0

    @property
    def age_seconds(self) -> float:
        delta = datetime.now(timezone.utc) - self.fetched_at
        return max(delta.total_seconds(), 0.0)

    @property
    def is_fresh(self) -> bool:
        return self.age_seconds <= self.max_age_seconds

    @property
    def is_stale(self) -> bool:
        return not self.is_fresh


@dataclass(frozen=True, slots=True)
class AIDecisionFingerprint:
    """Fingerprint of the AI decision that produced an option recommendation."""

    analysis_cycle_id: str
    candle_version: str
    candle_ts: str
    ai_signal: str
    confidence: float
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_fresh(self) -> bool:
        max_age = 30.0  # 30 second window
        age = (datetime.now(timezone.utc) - self.fetched_at).total_seconds()
        return age <= max_age


@dataclass(frozen=True, slots=True)
class ExitOrder:
    """Describes an exit order to close an option position."""

    position_id: str
    exit_price: float
    exit_reason: str
    exit_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    quantity: int = 0
    realized_pnl: float = 0.0


# ── Phase 57B Models ──


@dataclass(frozen=True, slots=True)
class ChainValidationResult:
    """Result of structural chain validation."""

    accepted: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    contract_count: int = 0
    ce_count: int = 0
    pe_count: int = 0
    expiry_count: int = 0
    invalid_contract_count: int = 0
    schema_version: str = "1.0"


@dataclass(frozen=True, slots=True)
class InstrumentRefreshResult:
    """Result of an instrument refresh operation."""

    success: bool
    underlying: str
    instrument_count: int = 0
    expiry_count: int = 0
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class OptionChainRefreshResult:
    """Result of a chain refresh operation for one underlying."""

    success: bool
    underlying: str
    chain_version: int = 0
    instrument_version: int = 0
    validation: ChainValidationResult | None = None
    freshness: FreshnessState = FreshnessState.UNKNOWN
    error: str = ""
    error_code: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    analysis_cycle_id: str = ""


@dataclass(frozen=True, slots=True)
class OptionEngineReadiness:
    """Readiness state of the Options Engine."""

    engine_running: bool = False
    provider_ready: bool = False
    instruments_loaded: bool = False
    chain_available: bool = False
    chain_fresh: bool = False
    freshness: FreshnessState = FreshnessState.UNKNOWN
    status: ReadinessStatus = ReadinessStatus.NOT_STARTED
    blocked_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    last_success_at: datetime | None = None
    last_attempt_at: datetime | None = None
    last_error: str = ""
    consecutive_failures: int = 0
    chain_version: int = 0
    underlying_statuses: dict[str, str] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        return self.status == ReadinessStatus.READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_running": self.engine_running,
            "provider_ready": self.provider_ready,
            "instruments_loaded": self.instruments_loaded,
            "chain_available": self.chain_available,
            "chain_fresh": self.chain_fresh,
            "freshness": self.freshness.value,
            "status": self.status.value,
            "blocked_reasons": list(self.blocked_reasons),
            "warnings": list(self.warnings),
            "last_success_at": (
                self.last_success_at.isoformat() if self.last_success_at else None
            ),
            "last_attempt_at": (
                self.last_attempt_at.isoformat() if self.last_attempt_at else None
            ),
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "chain_version": self.chain_version,
            "underlying_statuses": dict(self.underlying_statuses),
        }


@dataclass(slots=True)
class OptionChainCacheStatus:
    """Status of the option chain cache for a single underlying."""

    underlying: str
    has_data: bool = False
    chain_version: int = 0
    instrument_version: int = 0
    freshness: FreshnessState = FreshnessState.UNKNOWN
    data_age_seconds: float = -1.0
    last_success_at: datetime | None = None
    last_attempt_at: datetime | None = None
    last_error: str = ""
    consecutive_failures: int = 0
    expiry_count: int = 0
    contract_count: int = 0
    schema_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "underlying": self.underlying,
            "has_data": self.has_data,
            "chain_version": self.chain_version,
            "instrument_version": self.instrument_version,
            "freshness": self.freshness.value,
            "data_age_seconds": round(self.data_age_seconds, 2),
            "last_success_at": (
                self.last_success_at.isoformat() if self.last_success_at else None
            ),
            "last_attempt_at": (
                self.last_attempt_at.isoformat() if self.last_attempt_at else None
            ),
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "expiry_count": self.expiry_count,
            "contract_count": self.contract_count,
        }


@dataclass(frozen=True, slots=True)
class FreshnessInfo:
    """Detailed freshness tracking for a cached snapshot."""

    state: FreshnessState = FreshnessState.UNKNOWN
    age_seconds: float = -1.0
    max_age_seconds: float = 15.0
    stale_after_seconds: float = 60.0
    timestamp_source: str = ""
    fetched_at: datetime | None = None
    provider_timestamp: datetime | None = None
    received_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "age_seconds": round(self.age_seconds, 2),
            "max_age_seconds": self.max_age_seconds,
            "stale_after_seconds": self.stale_after_seconds,
            "timestamp_source": self.timestamp_source,
        }

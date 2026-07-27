"""
Market session rules for the Auto Trade Workspace.

Enforces session-based trading gates:
- Opening volatility window (no trades first 15 minutes)
- Entry cutoff time (no new entries after configured time)
- Force-exit time (close all intraday positions)
- Market close detection

Uses Asia/Kolkata timezone consistently.
If an exchange calendar is not available, uses fixed time rules
that match NSE/BSE equity derivatives market hours.
"""

from __future__ import annotations

from datetime import datetime, time, timezone, timedelta
from typing import Any

# ── Fixed market hours (NSE/BSE equity derivatives) ──
# Market opens at 09:15 IST, closes at 15:30 IST
# Derived from Indian Standard Time (UTC+05:30)

MARKET_OPEN_TIME = time(9, 15, tzinfo=timezone.utc)  # 09:15 IST = 03:45 UTC
IST_OFFSET = timedelta(hours=5, minutes=30)


def _ist_now() -> datetime:
    """Return current time in IST (Asia/Kolkata)."""
    utc_now = datetime.now(timezone.utc)
    return utc_now.astimezone(timezone(timedelta(hours=5, minutes=30)))


def _ist_time(hour: int, minute: int = 0) -> time:
    """Create a time object in IST timezone."""
    return time(hour, minute, tzinfo=timezone(IST_OFFSET))


# ── Configurable session parameters ──

class MarketSessionConfig:
    """Immutable session configuration with safe defaults."""

    def __init__(
        self,
        avoid_first_minutes: int = 15,
        new_entry_start: time | None = None,
        new_entry_cutoff: time | None = None,
        force_exit_time: time | None = None,
        market_close_time: time | None = None,
    ):
        self.avoid_first_minutes = max(0, avoid_first_minutes)
        # 09:30 IST = open 09:15 + 15 min default
        self.new_entry_start = new_entry_start or _ist_time(9, 30)
        # 15:00 IST — stop new entries 30 min before close
        self.new_entry_cutoff = new_entry_cutoff or _ist_time(15, 0)
        # 15:20 IST — force-exit all intraday positions
        self.force_exit_time = force_exit_time or _ist_time(15, 20)
        # 15:30 IST — market close
        self.market_close_time = market_close_time or _ist_time(15, 30)


# ── Session result ──

class SessionResult:
    """
    Result of a session check.

    Attributes:
        can_trade: Whether a new entry is allowed.
        is_market_hours: Whether the market is currently open.
        reason: Human-readable reason if blocked.
        code: Machine-readable block code if blocked.
        current_time_ist: Current time as ISO string in IST.
        next_market_open: Next market open time (if currently closed).
    """

    def __init__(
        self,
        can_trade: bool = False,
        is_market_hours: bool = False,
        reason: str = "",
        code: str = "",
        current_time_ist: str = "",
        next_market_open: str = "",
    ):
        self.can_trade = can_trade
        self.is_market_hours = is_market_hours
        self.reason = reason
        self.code = code
        self.current_time_ist = current_time_ist
        self.next_market_open = next_market_open

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_trade": self.can_trade,
            "is_market_hours": self.is_market_hours,
            "reason": self.reason,
            "code": self.code,
            "current_time_ist": self.current_time_ist,
            "next_market_open": self.next_market_open,
        }


# ── Default config ──

DEFAULT_SESSION_CONFIG = MarketSessionConfig()


def is_market_open(now: datetime | None = None) -> bool:
    """Check if the market is currently open (weekday 09:15-15:30 IST)."""
    dt = now.astimezone(timezone(IST_OFFSET)) if now else _ist_now()
    # Weekday check (Monday=0, Sunday=6)
    if dt.weekday() >= 5:  # Saturday or Sunday
        return False
    open_time = dt.replace(hour=9, minute=15, second=0, microsecond=0)
    close_time = dt.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_time <= dt <= close_time


def check_session(
    config: MarketSessionConfig | None = None,
    now: datetime | None = None,
) -> SessionResult:
    """
    Check whether new entries are allowed based on market session rules.

    Returns a SessionResult with can_trade, reason, and block code.
    """
    cfg = config or DEFAULT_SESSION_CONFIG
    dt = _ist_now() if now is None else now.astimezone(timezone(IST_OFFSET))
    current_ist = dt.isoformat()

    # Weekend check
    if dt.weekday() >= 5:
        return SessionResult(
            can_trade=False,
            is_market_hours=False,
            reason="Market closed: weekend",
            code="MARKET_CLOSED_WEEKEND",
            current_time_ist=current_ist,
        )

    # Current time as time object for comparison
    current_t = dt.timetz()
    open_t = time(9, 15, tzinfo=timezone(IST_OFFSET))
    close_t = time(15, 30, tzinfo=timezone(IST_OFFSET))

    # Before market open
    if current_t < open_t:
        return SessionResult(
            can_trade=False,
            is_market_hours=False,
            reason=f"Market opens at 09:15 IST (current: {dt.strftime('%H:%M')} IST)",
            code="BEFORE_MARKET_OPEN",
            current_time_ist=current_ist,
        )

    # After market close
    if current_t >= close_t:
        return SessionResult(
            can_trade=False,
            is_market_hours=False,
            reason=f"Market closed at 15:30 IST (current: {dt.strftime('%H:%M')} IST)",
            code="AFTER_MARKET_CLOSE",
            current_time_ist=current_ist,
        )

    # Opening volatility window (first N minutes)
    opening_end = datetime.combine(dt.date(), open_t, tzinfo=timezone(IST_OFFSET))
    opening_end = opening_end.replace(minute=15 + cfg.avoid_first_minutes)
    if dt < opening_end:
        mins_left = int((opening_end - dt).total_seconds() / 60)
        return SessionResult(
            can_trade=False,
            is_market_hours=True,
            reason=f"Opening volatility window: {mins_left}m remaining (avoids first {cfg.avoid_first_minutes}m)",
            code="OPENING_VOLATILITY_WINDOW",
            current_time_ist=current_ist,
        )

    # Entry cutoff
    if cfg.new_entry_cutoff and current_t >= cfg.new_entry_cutoff:
        return SessionResult(
            can_trade=False,
            is_market_hours=True,
            reason=f"New entry cutoff at {cfg.new_entry_cutoff.strftime('%H:%M')} IST reached",
            code="ENTRY_CUTOFF_REACHED",
            current_time_ist=current_ist,
        )

    # All gates passed
    return SessionResult(
        can_trade=True,
        is_market_hours=True,
        reason="Market session OK",
        code="",
        current_time_ist=current_ist,
    )


def is_force_exit_time(
    config: MarketSessionConfig | None = None,
    now: datetime | None = None,
) -> bool:
    """
    Check if it's time to force-exit all intraday positions.
    Returns True if current time >= force_exit_time.
    """
    cfg = config or DEFAULT_SESSION_CONFIG
    dt = _ist_now() if now is None else now.astimezone(timezone(IST_OFFSET))
    return dt.timetz() >= cfg.force_exit_time

"""
MarketMind AI — Market Calendar

Centralised market timing rules for Indian markets (NSE/BSE).

All future modules must call these helpers instead of re-implementing
timezone conversions or market-hour checks.

Market hours: 9:15 AM to 3:30 PM IST, Monday–Friday.
"""

from datetime import datetime, timezone, timedelta

from core.settings import UTC_OFFSET_HOURS


# ── Market hours (IST) ──

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15     # 9:15 AM IST
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30    # 3:30 PM IST

# Session phase boundaries (minutes from open)
OPENING_PHASE_END = 30      # First 30 minutes = Opening
CLOSING_PHASE_START = 345   # Last 30 minutes = Closing (375 - 30 = 345)
SESSION_TOTAL_MINUTES = 375  # 9:15 → 15:30 = 6h15m = 375 minutes


def _now_ist() -> datetime:
    """Return current time in IST."""
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=UTC_OFFSET_HOURS)


def is_market_open(dt: datetime | None = None) -> bool:
    """Check if the Indian stock market is currently open.

    Market hours: 9:15 AM to 3:30 PM IST, Monday–Friday.
    """
    now = dt if dt else _now_ist()
    day = now.weekday()  # Monday=0, Sunday=6
    if day >= 5:  # Saturday=5, Sunday=6
        return False
    total_min = now.hour * 60 + now.minute
    open_min = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
    close_min = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE
    return open_min <= total_min < close_min


def is_trading_day(dt: datetime | None = None) -> bool:
    """Check if today is a trading day (weekday, not a holiday placeholder)."""
    now = dt if dt else _now_ist()
    day = now.weekday()
    if day >= 5:
        return False
    # TODO: Add holiday calendar check in a future phase
    return True


def minutes_from_market_open(dt: datetime | None = None) -> int:
    """Get minutes elapsed since market open (9:15 AM IST).

    Returns negative if market hasn't opened yet.
    """
    now = dt if dt else _now_ist()
    today_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    diff = (now - today_open).total_seconds()
    return int(diff // 60)


def current_session(dt: datetime | None = None) -> str:
    """Determine the current market session phase.

    Returns one of: 'PreMarket', 'Opening', 'Mid', 'Closing', 'Closed'
    """
    if not is_market_open(dt):
        # Check if it's before or after market hours
        now = dt if dt else _now_ist()
        day = now.weekday()
        if day >= 5:
            return "Closed"
        total_min = now.hour * 60 + now.minute
        open_min = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
        if total_min < open_min:
            return "PreMarket"
        return "Closed"

    mins = minutes_from_market_open(dt)
    if mins < 0:
        return "PreMarket"
    if mins <= OPENING_PHASE_END:
        return "Opening"
    if mins >= CLOSING_PHASE_START:
        return "Closing"
    return "Mid"


def next_trading_day(from_date: datetime | None = None) -> str:
    """Get the next trading day as YYYY-MM-DD string.

    Skips weekends. Does NOT account for holidays (future).
    """
    d = from_date or _now_ist()
    d = d + timedelta(days=1)
    while d.weekday() >= 5:
        d = d + timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def current_trading_day(from_date: datetime | None = None) -> str:
    """Get the current or most recent trading day as YYYY-MM-DD string.

    If today is a weekend, returns the last Friday.
    """
    d = from_date or _now_ist()
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    return d.strftime("%Y-%m-%d")

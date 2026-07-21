"""
MarketMind AI — Market Data Service

Orchestrates fetching, caching, and returning daily & intraday market data.
This service wraps the CSV cache and yfinance calls into a clean API.
"""

import asyncio
from datetime import date, datetime, timezone, timedelta

import yfinance as yf

from core.constants import (
    DAILY_LOOKBACK_DEFAULT_DAYS,
    DAILY_OVERLAP_DAYS,
    INTRADAY_MAX_DAYS_FAST,
    INTRADAY_MAX_DAYS_DEFAULT,
    DAILY_REFS_LOOKBACK_DAYS,
    DAILY_REFS_WEEKLY_WINDOW,
    DAILY_REFS_MIN_CANDLES,
    CACHE_FLUSH_BUFFER_SEC,
    FAST_INTERVALS,
    BACKTEST_DAILY_INTERVAL,
)
from core.intervals import interval_to_minutes
from cache.csv_cache import (
    load_daily_csv,
    write_full_daily_csv,
    load_intraday_csv,
    write_full_intraday_csv,
)
from utils.helpers import get_ticker_from_display, parse_date_str
from utils.logger import log_info, log_warn


# ── Daily data ──


async def fetch_daily_data(symbol: str, start_date: date, end_date: date):
    """
    Fetch daily OHLC data for the given symbol and date range.

    Uses a CSV cache: if the cache covers the requested range, returns instantly.
    Only calls yfinance for missing days.

    Returns:
        dict with {"symbol": str, "data": list}
    """
    ticker = get_ticker_from_display(symbol)
    today = date.today()

    # 1. Try disk cache
    cached_records, cached_last_date_str, _ = load_daily_csv(ticker)
    cached_last_date = date.fromisoformat(cached_last_date_str) if cached_last_date_str else None

    need_fetch = _check_daily_cache_needs_refresh(
        cached_records, cached_last_date, start_date, end_date, today
    )

    if need_fetch:
        cached_records = await _refresh_daily_cache(ticker, cached_records, cached_last_date, start_date, end_date)

    # Filter to requested range
    filtered = [
        d for d in cached_records
        if start_date <= date.fromisoformat(d["Date"]) <= end_date
    ]

    return {"symbol": symbol, "data": filtered}


def _check_daily_cache_needs_refresh(cached_records, cached_last_date, start_date, end_date, today):
    """Determine if the daily CSV cache needs updating."""
    if cached_last_date is None or cached_last_date < end_date:
        return True

    fetch_start_needed = start_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)
    earliest_cached = (
        date.fromisoformat(cached_records[0]["Date"]) if cached_records else today
    )
    if earliest_cached > fetch_start_needed:
        return True

    return False


async def _refresh_daily_cache(ticker, cached_records, cached_last_date, start_date, end_date):
    """Fetch missing daily data from yfinance and merge with cache."""
    ticker_obj = yf.Ticker(ticker)

    if cached_last_date and cached_last_date < end_date:
        fetch_start = cached_last_date - timedelta(days=DAILY_OVERLAP_DAYS)
    else:
        fetch_start = start_date - timedelta(days=DAILY_LOOKBACK_DEFAULT_DAYS)

    log_info("Fetching daily data", ticker=ticker, start=str(fetch_start), end=str(end_date + timedelta(days=1)))

    df = await asyncio.to_thread(
        ticker_obj.history, start=fetch_start, end=end_date + timedelta(days=1)
    )

    if df.empty:
        log_warn("yfinance returned no daily data", ticker=ticker)
        return cached_records or []

    df = df.reset_index()
    new_records = []
    for _, row in df.iterrows():
        date_val = row["Date"]
        new_records.append({
            "Date": parse_date_str(date_val),
            "Open": float(row["Open"]),
            "High": float(row["High"]),
            "Low": float(row["Low"]),
            "Close": float(row["Close"]),
            "Volume": float(row.get("Volume", 0)),
        })

    if cached_records:
        existing_dates = {r["Date"] for r in cached_records}
        fresh = [r for r in new_records if r["Date"] not in existing_dates]
        merged = cached_records + fresh
        merged.sort(key=lambda r: r["Date"])
        write_full_daily_csv(ticker, merged)
        return merged
    else:
        write_full_daily_csv(ticker, new_records)
        return new_records


# ── Intraday data ──


async def fetch_intraday_data(symbol: str, interval: str, days: int):
    """
    Fetch intraday candle data for the given symbol, interval, and lookback days.

    Returns:
        dict with {"symbol", "candles", "dailyRefs", "cached", "cache_size"}
    """
    ticker = get_ticker_from_display(symbol)

    # 1. Load intraday cache
    cached_candles, latest_cached_time = load_intraday_csv(ticker, interval)

    # 2. Determine if we need to fetch from yfinance
    now_utc = datetime.now(timezone.utc)
    need_fetch = _check_intraday_cache_needs_refresh(latest_cached_time, interval, now_utc)

    if need_fetch:
        cached_candles = await _refresh_intraday_cache(ticker, interval, cached_candles, days)

    # Trim to requested days
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = [c for c in cached_candles if datetime.fromisoformat(c["time"]) >= cutoff]

    # Deduplicate by time (safety)
    deduped = _deduplicate_candles(result)

    # Fetch daily reference levels
    daily_refs = await _fetch_daily_reference_levels(ticker)

    return {
        "symbol": symbol,
        "candles": deduped,
        "dailyRefs": daily_refs,
        "cached": not need_fetch,
        "cache_size": len(deduped),
    }


def _check_intraday_cache_needs_refresh(latest_cached_time, interval, now_utc):
    """Check if a new intraday candle should have closed since the last cache timestamp."""
    if not latest_cached_time:
        return True

    try:
        interval_mins = interval_to_minutes(interval)
        if interval_mins <= 0:
            return True

        latest_dt = datetime.fromisoformat(latest_cached_time)
        delta = timedelta(minutes=interval_mins)
        next_candle_time = latest_dt + delta

        # Only fetch if the next candle should have already closed
        if next_candle_time > now_utc - timedelta(seconds=CACHE_FLUSH_BUFFER_SEC):
            return False
    except Exception:
        return True

    return True


async def _refresh_intraday_cache(ticker, interval, cached_candles, days):
    """Fetch missing intraday data from yfinance and merge with cache."""
    max_days = INTRADAY_MAX_DAYS_FAST if interval in FAST_INTERVALS else INTRADAY_MAX_DAYS_DEFAULT
    period = f"{min(days, max_days)}d"

    log_info("Fetching intraday data", ticker=ticker, interval=interval, period=period)

    df = await asyncio.to_thread(
        yf.Ticker(ticker).history, period=period, interval=interval
    )

    if df.empty:
        log_warn("yfinance returned no intraday data", ticker=ticker, interval=interval)
        return cached_candles

    df = df.reset_index()
    existing_times = {c["time"] for c in cached_candles}
    new_candles = []

    for _, row in df.iterrows():
        dt = row["Datetime"]
        time_str = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
        if time_str not in existing_times:
            new_candles.append({
                "time": time_str,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row.get("Volume", 0)),
            })

    if new_candles:
        cached_candles.extend(new_candles)
        cached_candles.sort(key=lambda c: c["time"])
        write_full_intraday_csv(ticker, interval, cached_candles)

    return cached_candles


async def _fetch_daily_reference_levels(ticker):
    """Fetch daily OHLC data for reference levels (prev day, weekly high/low)."""
    try:
        df_daily = await asyncio.to_thread(
            yf.Ticker(ticker).history, period=f"{DAILY_REFS_LOOKBACK_DAYS}d", interval=BACKTEST_DAILY_INTERVAL
        )
        if df_daily.empty:
            return None

        df_daily = df_daily.reset_index()
        dailies = []
        for _, row in df_daily.iterrows():
            date_val = row["Date"] if "Date" in df_daily.columns else row.get("Datetime")
            dailies.append({
                "date": parse_date_str(date_val),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            })

        if len(dailies) >= DAILY_REFS_MIN_CANDLES:
            prev = dailies[-2]
            weekly_high = max(d["high"] for d in dailies[-DAILY_REFS_WEEKLY_WINDOW:])
            weekly_low = min(d["low"] for d in dailies[-DAILY_REFS_WEEKLY_WINDOW:])
            return {
                "prevDayHigh": prev["high"],
                "prevDayLow": prev["low"],
                "prevDayClose": prev["close"],
                "prevDayOpen": prev["open"],
                "weeklyHigh": weekly_high,
                "weeklyLow": weekly_low,
                "prevDayRange": round(prev["high"] - prev["low"], 2),
                "prevDayMidpoint": round((prev["high"] + prev["low"]) / 2, 2),
                "prevDayVWAP": round((prev["high"] + prev["low"] + prev["close"]) / 3, 2),
            }
    except Exception:
        return None

    return None


async def get_cache_status(symbol: str):
    """Return cache metadata (last_updated, total_days) for a symbol."""
    ticker = get_ticker_from_display(symbol)
    records, last_date, total = load_daily_csv(ticker)
    return {
        "symbol": symbol,
        "last_updated": last_date or "never",
        "total_days": total,
    }


# ── Helpers ──


def _deduplicate_candles(candles: list) -> list:
    """Remove candles with duplicate timestamps, preserving order."""
    seen = set()
    deduped = []
    for c in candles:
        if c["time"] not in seen:
            seen.add(c["time"])
            deduped.append(c)
    return deduped

"""
MarketMind AI - Backend Server
FastAPI server with dual-layer caching (in-memory + disk CSV/JSON).
Fetches historical index data via yfinance.
"""

import json
import os
import csv
import asyncio
from datetime import date, timedelta, datetime, timezone
from typing import Optional
from functools import lru_cache

import yfinance as yf

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, save_prediction, get_predictions, get_prediction_by_id, get_pending_predictions, update_prediction_result, get_prediction_stats, check_prediction_result, deduplicate_predictions, delete_prediction

app = FastAPI(title="MarketMind AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_DIR = "data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Yahoo Finance tickers for Indian indices
SYMBOL_MAP = {
    "NIFTY 50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}

# For display name lookup
DISPLAY_NAMES = {v: k for k, v in SYMBOL_MAP.items()}

# ── Pydantic models for prediction API ──

class PredictionCreate(BaseModel):
    symbol: str
    interval: str = "15m"
    predicted_date: str
    direction: str
    trend_label: str | None = None
    confidence: int | None = None
    suggested_bias: str | None = None
    entry_zone: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    predicted_high: float | None = None
    predicted_low: float | None = None
    predicted_close: float | None = None
    rsi: float | None = None
    atr: float | None = None
    adx: float | None = None
    support_levels: list | None = None
    resistance_levels: list | None = None
    fibonacci_levels: dict | None = None
    buy_scenario: dict | None = None
    sell_scenario: dict | None = None
    notes: str | None = None


def get_csv_path(ticker: str) -> str:
    safe = ticker.replace("^", "").replace(".", "_")
    return os.path.join(CACHE_DIR, f"{safe}.csv")


def get_ticker_from_display(display_name: str) -> str:
    return SYMBOL_MAP.get(display_name, display_name)


def load_cached_csv(ticker: str):
    """Load cached CSV data into a list of dicts, returns (records, last_date, total_days)."""
    path = get_csv_path(ticker)
    if not os.path.exists(path):
        return [], None, 0
    records = []
    last_date = None
    try:
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "Date": row["Date"],
                    "Open": float(row["Open"]),
                    "High": float(row["High"]),
                    "Low": float(row["Low"]),
                    "Close": float(row["Close"]),
                    "Volume": float(row.get("Volume", 0)),
                })
                last_date = row["Date"]
    except Exception:
        return [], None, 0
    return records, last_date, len(records)


def append_to_csv(ticker: str, records: list):
    """Append new records to CSV, overwriting if file is empty."""
    path = get_csv_path(ticker)
    file_exists = os.path.exists(path) and os.path.getsize(path) > 0
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        for r in records:
            writer.writerow([r["Date"], r["Open"], r["High"], r["Low"], r["Close"], r["Volume"]])


def write_full_csv(ticker: str, records: list):
    """Write full dataset to CSV (used after fresh fetch)."""
    path = get_csv_path(ticker)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        for r in records:
            writer.writerow([r["Date"], r["Open"], r["High"], r["Low"], r["Close"], r["Volume"]])


@app.get("/api/data")
async def get_data(
    symbol: str = Query("NIFTY 50", description="Index display name"),
    start: str = Query(None, description="Start date YYYY-MM-DD"),
    end: str = Query(None, description="End date YYYY-MM-DD"),
):
    """Fetch historical index data with dual-layer caching."""
    ticker = get_ticker_from_display(symbol)
    today = date.today()

    if end is None:
        end_date = today
    else:
        end_date = date.fromisoformat(end)

    if start is None:
        start_date = end_date - timedelta(days=365)
    else:
        start_date = date.fromisoformat(start)

    try:
        # 1. Try disk cache first
        cached_records, cached_last_date_str, _ = load_cached_csv(ticker)
        cached_last_date = date.fromisoformat(cached_last_date_str) if cached_last_date_str else None

        need_fetch = False

        # If cache doesn't cover the requested end date, fetch missing days
        if cached_last_date is None or cached_last_date < end_date:
            need_fetch = True

        # If cache doesn't cover far enough back for indicators, fetch earlier
        fetch_start_needed = start_date - timedelta(days=365)
        earliest_cached = date.fromisoformat(cached_records[0]["Date"]) if cached_records else today

        if earliest_cached > fetch_start_needed:
            need_fetch = True

        if need_fetch:
            ticker_obj = yf.Ticker(ticker)

            # Determine fetch range
            if cached_last_date and cached_last_date < end_date:
                # Only fetch missing days
                fetch_start = cached_last_date - timedelta(days=5)  # 5 day overlap
            else:
                fetch_start = fetch_start_needed

            df = await asyncio.to_thread(
                ticker_obj.history, start=fetch_start, end=end_date + timedelta(days=1)
            )

            if not df.empty:
                df = df.reset_index()
                new_records = []
                for _, row in df.iterrows():
                    date_val = row["Date"]
                    date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)[:10]
                    new_records.append({
                        "Date": date_str,
                        "Open": float(row["Open"]),
                        "High": float(row["High"]),
                        "Low": float(row["Low"]),
                        "Close": float(row["Close"]),
                        "Volume": float(row.get("Volume", 0)),
                    })

                # Merge with cache
                if cached_records:
                    existing_dates = {r["Date"] for r in cached_records}
                    fresh = [r for r in new_records if r["Date"] not in existing_dates]
                    cached_records = cached_records + fresh
                    cached_records.sort(key=lambda r: r["Date"])
                    write_full_csv(ticker, cached_records)
                else:
                    cached_records = new_records
                    write_full_csv(ticker, cached_records)

        # Filter to requested range
        filtered = [
            d for d in cached_records
            if start_date <= date.fromisoformat(d["Date"]) <= end_date
        ]

        return {"symbol": symbol, "data": filtered}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "data": [], "error": str(e)}


@app.get("/api/intraday")
async def get_intraday(
    symbol: str = Query("NIFTY 50", description="Index display name"),
    interval: str = Query("15m", description="Intraday interval: 1m, 2m, 5m, 15m, 30m, 60m"),
    days: int = Query(3, description="Number of days of intraday data"),
):
    """Fetch intraday candles with disk caching.

    Strategy:
    1. Load cached CSV (symbol_interval.csv) — if it has all candles up to now, return instantly.
    2. Only call yfinance if a new candle has likely closed since the cache's latest timestamp.
    3. Merge, write back, return.
    This means yfinance is called at most once per candle interval, not on every frontend poll.
    """
    ticker = get_ticker_from_display(symbol)
    cache_key = f"{ticker}_{interval}"

    try:
        from datetime import datetime, timezone, timedelta as dt_timedelta

        # 1. Load intraday cache
        cache_path = os.path.join(CACHE_DIR, f"{cache_key.replace('^', '').replace('.', '_')}.csv")
        cached_candles = []
        latest_cached_time = None
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        c = {
                            "time": row["time"],
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": float(row.get("volume", 0)),
                        }
                        cached_candles.append(c)
                        latest_cached_time = row["time"]
            except Exception:
                cached_candles = []
                latest_cached_time = None

        # 2. Determine if we need to fetch
        now_utc = datetime.now(timezone.utc)
        need_fetch = True

        # Convert interval to minutes
        interval_num = int(interval.replace("m", "").replace("h", ""))
        is_minutes = "m" in interval
        is_hours = "h" in interval

        if latest_cached_time:
            try:
                latest_dt = datetime.fromisoformat(latest_cached_time)
                # Expected candle close: latest_dt + interval
                next_candle_time = latest_dt + dt_timedelta(minutes=interval_num if is_minutes else interval_num * 60)
                # Only fetch if the next candle should have already closed (plus 30s buffer)
                if next_candle_time > now_utc - dt_timedelta(seconds=30):
                    need_fetch = False
            except Exception:
                need_fetch = True

        if need_fetch:
            max_days = 2 if interval in ("1m", "2m") else 60
            period = f"{min(days, max_days)}d"
            df = await asyncio.to_thread(yf.Ticker(ticker).history, period=period, interval=interval)

            if not df.empty:
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

                    # Write full cache
                    with open(cache_path, "w", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(["time", "open", "high", "low", "close", "volume"])
                        for c in cached_candles:
                            writer.writerow([c["time"], c["open"], c["high"], c["low"], c["close"], c["volume"]])

        # Trim to requested days
        cutoff = datetime.now(timezone.utc) - dt_timedelta(days=days)
        result = [c for c in cached_candles if datetime.fromisoformat(c["time"]) >= cutoff]

        # Deduplicate by time before returning (safety)
        seen = set()
        deduped = []
        for c in result:
            if c["time"] not in seen:
                seen.add(c["time"])
                deduped.append(c)

        # Also fetch daily reference levels (last 5 trading days)
        daily_refs = None
        try:
            df_daily = await asyncio.to_thread(yf.Ticker(ticker).history, period="10d", interval="1d")
            if not df_daily.empty:
                df_daily = df_daily.reset_index()
                dailies = []
                for _, row in df_daily.iterrows():
                    date_val = row["Date"] if "Date" in df_daily.columns else row["Datetime"]
                    dailies.append({
                        "date": date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)[:10],
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                    })
                if len(dailies) >= 2:
                    prev = dailies[-2]  # previous trading day
                    weekly_high = max(d["high"] for d in dailies[-5:])
                    weekly_low = min(d["low"] for d in dailies[-5:])
                    daily_refs = {
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
            pass

        return {
            "symbol": symbol,
            "candles": deduped,
            "dailyRefs": daily_refs,
            "cached": not need_fetch,
            "cache_size": len(deduped),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "candles": [], "error": str(e)}


@app.get("/api/cache/status")
async def cache_status(
    symbol: str = Query("NIFTY 50", description="Index display name"),
):
    """Return cache metadata for a given symbol."""
    ticker = get_ticker_from_display(symbol)
    records, last_date, total = load_cached_csv(ticker)
    return {
        "symbol": symbol,
        "last_updated": last_date or "never",
        "total_days": total,
    }


@app.on_event("startup")
async def startup():
    """Initialize the SQLite database on startup + deduplicate any stale rows."""
    init_db()
    deduped = deduplicate_predictions()
    print(f"[startup] Deduplicated {deduped} prediction rows")


# ── Prediction endpoints ──


@app.post("/api/predictions")
async def create_prediction(pred: PredictionCreate):
    """Save a prediction from the frontend."""
    try:
        pred_id = save_prediction(pred.model_dump())
        return {"id": pred_id, "status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/predictions")
async def list_predictions(
    symbol: str = Query(None, description="Filter by symbol"),
    limit: int = Query(50, description="Max results"),
    status: str = Query(None, description="Filter by status"),
):
    """List predictions with optional filters."""
    return get_predictions(symbol=symbol, limit=limit, status=status)


@app.get("/api/predictions/stats")
async def prediction_stats(
    symbol: str = Query(None, description="Filter by symbol"),
):
    """Get backtesting accuracy statistics."""
    return get_prediction_stats(symbol=symbol)


@app.post("/api/predictions/check-results")
async def check_pending_results():
    """Check all PENDING predictions against actual market data."""
    pending = get_pending_predictions()
    if not pending:
        return {"checked": 0, "message": "No pending predictions to check"}

    results = []
    for pred in pending:
        status, details = await check_prediction_result(pred)
        update_prediction_result(
            pred["id"],
            status,
            {
                "high": details.get("actual_high"),
                "low": details.get("actual_low"),
                "close": details.get("actual_close"),
                "open": details.get("actual_open"),
                "date": pred["predicted_date"],
            },
            details,
        )
        results.append({
            "id": pred["id"],
            "symbol": pred["symbol"],
            "predicted_date": pred["predicted_date"],
            "bias": pred["suggested_bias"],
            "status": status,
            "outcome": details.get("outcome", details.get("reason", details.get("error", "Checked"))),
        })

    return {"checked": len(results), "results": results}


@app.post("/api/predictions/cleanup")
async def cleanup_duplicates():
    """Force-deduplicate prediction rows by (symbol, interval, predicted_date)."""
    removed = deduplicate_predictions()
    return {"removed": removed, "message": f"Removed {removed} duplicate entries"}


@app.get("/api/predictions/{prediction_id}")
async def get_prediction(prediction_id: int):
    """Get a single prediction by id."""
    pred = get_prediction_by_id(prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return pred


@app.delete("/api/predictions/{prediction_id}")
async def remove_prediction(prediction_id: int):
    """Delete a prediction by id."""
    deleted = delete_prediction(prediction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"deleted": True, "id": prediction_id}


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "MarketMind AI Backend is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

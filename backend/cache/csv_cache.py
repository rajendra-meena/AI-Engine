"""
MarketMind AI — CSV Cache Layer

Handles reading and writing market data CSV files on disk.
Used by both daily and intraday endpoints.
"""

import csv
import os
from core.config import DATA_CACHE_DIR


def _sanitise_ticker(ticker: str) -> str:
    """Strip special characters from a ticker for safe file naming."""
    return ticker.replace("^", "").replace(".", "_")


def csv_path(ticker: str, suffix: str = "") -> str:
    """
    Build a cache file path for a ticker.

    Args:
        ticker: Yahoo Finance ticker (e.g. ^NSEI)
        suffix: Optional interval suffix (e.g. _15m)

    Returns:
        Absolute path to the CSV file.
    """
    safe = _sanitise_ticker(ticker)
    return os.path.join(DATA_CACHE_DIR, f"{safe}{suffix}.csv")


def load_daily_csv(ticker: str):
    """
    Load cached daily OHLC data.

    Returns:
        (records, last_date_str, total_count)
        records is a list of dicts with Date/Open/High/Low/Close/Volume keys.
    """
    path = csv_path(ticker)
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


def write_full_daily_csv(ticker: str, records: list):
    """Write the full daily dataset to CSV (overwrites existing)."""
    path = csv_path(ticker)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        for r in records:
            writer.writerow([r["Date"], r["Open"], r["High"], r["Low"], r["Close"], r["Volume"]])


def append_daily_csv(ticker: str, records: list):
    """Append new daily records to CSV, writing header if file is empty."""
    path = csv_path(ticker)
    file_exists = os.path.exists(path) and os.path.getsize(path) > 0
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        for r in records:
            writer.writerow([r["Date"], r["Open"], r["High"], r["Low"], r["Close"], r["Volume"]])


def load_intraday_csv(ticker: str, interval: str):
    """
    Load cached intraday candle data.

    Returns:
        (candles, latest_time_str)
        candles is a list of dicts with time/open/high/low/close/volume keys.
    """
    cache_key = f"{_sanitise_ticker(ticker)}_{interval}"
    path = csv_path(ticker, f"_{interval}")
    candles = []
    latest_time = None

    if not os.path.exists(path):
        return candles, latest_time

    try:
        with open(path, "r", newline="") as f:
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
                candles.append(c)
                latest_time = row["time"]
    except Exception:
        return [], None
    return candles, latest_time


def write_full_intraday_csv(ticker: str, interval: str, candles: list):
    """Write the full intraday dataset to CSV (overwrites existing)."""
    path = csv_path(ticker, f"_{interval}")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "open", "high", "low", "close", "volume"])
        for c in candles:
            writer.writerow([c["time"], c["open"], c["high"], c["low"], c["close"], c["volume"]])

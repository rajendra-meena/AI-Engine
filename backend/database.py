"""
MarketMind AI - Database Layer
SQLite-backed prediction storage and result checking for backtesting.
"""

import sqlite3
import json
import os
import asyncio
from datetime import datetime, timedelta, timezone

from core.symbols import get_ticker, list_display_names
from core.settings import DB_PATH
from core.enums import Outcome
from core.constants import (
    BACKTEST_BUFFER_DAYS_INTRADAY,
    BACKTEST_BUFFER_DAYS_DAILY,
    BACKTEST_INTRADAY_INTERVAL,
    BACKTEST_DAILY_INTERVAL,
    DEFAULT_API_LIMIT,
)
from data.provider_factory import ProviderFactory
from data.base_provider import BaseProvider

# Build a ticker → display-name map for backtesting lookups
SYMBOL_MAP = {name: get_ticker(name) for name in list_display_names()}

# Lazily initialised provider reference
_provider: BaseProvider | None = None


def _get_provider() -> BaseProvider:
    global _provider
    if _provider is None:
        factory = ProviderFactory()
        _provider = factory.get_default_provider()
    return _provider


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the predictions table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            interval        TEXT NOT NULL DEFAULT '15m',
            predicted_date  TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            direction       TEXT NOT NULL,
            trend_label     TEXT,
            confidence      INTEGER,
            suggested_bias  TEXT,
            entry_zone      REAL,
            stop_loss       REAL,
            target          REAL,
            predicted_high  REAL,
            predicted_low   REAL,
            predicted_close REAL,
            rsi             REAL,
            atr             REAL,
            adx             REAL,
            support_levels  TEXT,
            resistance_levels TEXT,
            fibonacci_levels  TEXT,
            buy_scenario    TEXT,
            sell_scenario   TEXT,
            notes           TEXT,

            -- Result fields
            status              TEXT DEFAULT 'PENDING',
            result_checked_at   TEXT,
            actual_high         REAL,
            actual_low          REAL,
            actual_close        REAL,
            actual_open         REAL,
            result_details      TEXT,
            checked_date        TEXT
        )
    """)
    conn.commit()

    # Add unique index if it doesn't exist
    try:
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_unique
            ON predictions(symbol, interval, predicted_date)
        """)
    except Exception:
        pass
    conn.commit()

    # Clean up any duplicate rows that existed before the index was added
    conn.execute("""
        DELETE FROM predictions WHERE id NOT IN (
            SELECT MIN(id) FROM predictions GROUP BY symbol, interval, predicted_date
        )
    """)
    conn.commit()
    conn.close()


def deduplicate_predictions():
    """Remove duplicate rows keeping only the earliest entry per (symbol, interval, predicted_date).
    Returns the number of duplicates removed.
    """
    conn = get_connection()
    result = conn.execute("""
        DELETE FROM predictions WHERE id NOT IN (
            SELECT MIN(id) FROM predictions GROUP BY symbol, interval, predicted_date
        )
    """)
    removed = result.rowcount
    conn.commit()
    conn.close()
    return removed


def save_prediction(data):
    """Insert or replace a prediction. Returns the inserted id.

    Deduplicates by (symbol, interval, predicted_date) — if a prediction
    for the same symbol+interval+date already exists, it's updated with
    the latest values.
    """
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO predictions (
            id, symbol, interval, predicted_date, created_at,
            direction, trend_label, confidence, suggested_bias,
            entry_zone, stop_loss, target,
            predicted_high, predicted_low, predicted_close,
            rsi, atr, adx,
            support_levels, resistance_levels, fibonacci_levels,
            buy_scenario, sell_scenario, notes
        ) VALUES (
            COALESCE((SELECT id FROM predictions WHERE symbol=? AND interval=? AND predicted_date=?), NULL),
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?
        )
    """, (
        # 3 lookup params (for the subquery)
        data.get("symbol"),
        data.get("interval", "15m"),
        data.get("predicted_date"),
        # 23 column values
        data.get("symbol"),
        data.get("interval", "15m"),
        data.get("predicted_date"),
        now,
        data.get("direction"),
        data.get("trend_label"),
        data.get("confidence"),
        data.get("suggested_bias"),
        data.get("entry_zone"),
        data.get("stop_loss"),
        data.get("target"),
        data.get("predicted_high"),
        data.get("predicted_low"),
        data.get("predicted_close"),
        data.get("rsi"),
        data.get("atr"),
        data.get("adx"),
        json.dumps(data.get("support_levels", [])),
        json.dumps(data.get("resistance_levels", [])),
        json.dumps(data.get("fibonacci_levels", {})),
        json.dumps(data.get("buy_scenario")),
        json.dumps(data.get("sell_scenario")),
        data.get("notes"),
    ))
    conn.commit()
    prediction_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return prediction_id


def get_predictions(symbol=None, limit=50, status=None):
    """List predictions, most recent first, with optional filters."""
    conn = get_connection()
    conditions = []
    params = []
    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if status:
        conditions.append("status = ?")
        params.append(status)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    rows = conn.execute(f"""
        SELECT * FROM predictions {where}
        GROUP BY symbol, interval, predicted_date
        ORDER BY created_at DESC LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_prediction_by_id(prediction_id):
    """Get a single prediction by id."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def delete_prediction(prediction_id):
    """Delete a prediction by id. Returns True if deleted, False if not found."""
    conn = get_connection()
    result = conn.execute("DELETE FROM predictions WHERE id = ?", (prediction_id,))
    deleted = result.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_pending_predictions():
    """Get all predictions with status PENDING."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM predictions WHERE status = 'PENDING'").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def update_prediction_result(prediction_id, status, actual_data, details):
    """Update a prediction with its backtesting result."""
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        UPDATE predictions SET
            status = ?,
            result_checked_at = ?,
            actual_high = ?,
            actual_low = ?,
            actual_close = ?,
            actual_open = ?,
            result_details = ?,
            checked_date = ?
        WHERE id = ?
    """, (
        status,
        now,
        actual_data.get("high"),
        actual_data.get("low"),
        actual_data.get("close"),
        actual_data.get("open"),
        json.dumps(details),
        actual_data.get("date"),
        prediction_id,
    ))
    conn.commit()
    conn.close()


def get_prediction_stats(symbol=None):
    """Get aggregate backtesting statistics."""
    conn = get_connection()
    # Clean duplicates first so stats are accurate
    conn.execute("""
        DELETE FROM predictions WHERE id NOT IN (
            SELECT MIN(id) FROM predictions GROUP BY symbol, interval, predicted_date
        )
    """)
    conn.commit()
    conditions = []
    params = []
    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    # Total counts
    total = conn.execute(f"SELECT COUNT(*) FROM predictions {where}", params).fetchone()[0]

    has_result_where = where + " AND status != 'PENDING'" if where else "WHERE status != 'PENDING'"
    total_checked = conn.execute(f"SELECT COUNT(*) FROM predictions {has_result_where}", params).fetchone()[0]

    # Status breakdown
    status_breakdown = {}
    for s in (Outcome.HIT_TARGET.value, Outcome.HIT_STOPLOSS.value, Outcome.NO_TRADE.value, Outcome.UNCHECKED.value, Outcome.PENDING.value):
        sw = f"status = '{s}'"
        full_where = f"{where} AND {sw}" if where else f"WHERE {sw}"
        count = conn.execute(f"SELECT COUNT(*) FROM predictions {full_where}", params).fetchone()[0]
        if count > 0:
            status_breakdown[s] = count

    # Direction breakdown within HIT_TARGET
    hits_with_dir = {}
    if where:
        hits_rows = conn.execute(f"""
            SELECT direction, COUNT(*) as cnt FROM predictions {where}
            AND status = 'HIT_TARGET' GROUP BY direction
        """, params).fetchall()
    else:
        hits_rows = conn.execute("""
            SELECT direction, COUNT(*) as cnt FROM predictions
            WHERE status = 'HIT_TARGET' GROUP BY direction
        """).fetchall()
    for r in hits_rows:
        hits_with_dir[r["direction"]] = r["cnt"]

    # Average confidence
    avg_conf_row = conn.execute(f"SELECT AVG(confidence) as avg_c FROM predictions {where}", params).fetchone()
    avg_confidence = round(avg_conf_row["avg_c"], 1) if avg_conf_row and avg_conf_row["avg_c"] else None

    conn.close()

    return {
        "total_predictions": total,
        "total_checked": total_checked,
        "hit_rate": round(status_breakdown.get("HIT_TARGET", 0) / total_checked * 100, 1) if total_checked > 0 else 0,
        "stoploss_rate": round(status_breakdown.get("HIT_STOPLOSS", 0) / total_checked * 100, 1) if total_checked > 0 else 0,
        "no_trade_rate": round(status_breakdown.get("NO_TRADE", 0) / total_checked * 100, 1) if total_checked > 0 else 0,
        "status_breakdown": status_breakdown,
        "hits_by_direction": hits_with_dir,
        "average_confidence": avg_confidence,
    }


def _is_intraday_interval(interval):
    """Check if the interval is intraday (minute/hour based) vs daily+."""
    if not interval:
        return False
    interval = interval.strip().lower()
    return interval.endswith("m") or interval.endswith("h")


async def check_prediction_result(prediction):
    """
    For a single PENDING prediction, fetch actual market data for the predicted_date
    and determine if target or stop loss was hit.

    - For intraday predictions (1m/3m/5m/15m/etc.): uses intraday OHLC data so the
      backtest checks against the actual intraday price action on that trading day.
    - For daily+ predictions (4D/1W/1M/etc.): uses daily OHLC data.
    """
    ticker = SYMBOL_MAP.get(prediction["symbol"])
    if not ticker:
        return Outcome.UNCHECKED.value, {"error": f"Unknown symbol: {prediction['symbol']}"}

    predicted_date = prediction["predicted_date"]
    pred_interval = prediction.get("interval", "15m")
    bias = prediction["suggested_bias"]
    entry = prediction["entry_zone"]
    stop_loss = prediction["stop_loss"]
    target = prediction["target"]

    if not target and not stop_loss:
        return Outcome.NO_TRADE.value, {"reason": "No target or stop loss defined"}

    if bias == "Wait":
        return Outcome.NO_TRADE.value, {"reason": "Prediction bias was 'Wait'"}

    try:
        start_dt = datetime.strptime(predicted_date, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=BACKTEST_BUFFER_DAYS_INTRADAY)

        provider = _get_provider()

        if _is_intraday_interval(pred_interval):
            # ── Intraday backtest: fetch intraday candles for the predicted day ──
            rows = await provider.fetch_intraday_range(
                prediction["symbol"], start_dt, end_dt, interval=BACKTEST_INTRADAY_INTERVAL
            )

            if not rows:
                return Outcome.UNCHECKED.value, {"error": f"No intraday data available for {predicted_date}"}

            # Filter candles that fall on the predicted_date (IST day)
            actual_high = -float("inf")
            actual_low = float("inf")
            actual_close = None
            actual_open = None
            last_close = None
            first_open = None

            for row in rows:
                date_val = row["Datetime"] if "Datetime" in row else row.get("Date")
                if hasattr(date_val, "strftime"):
                    candle_date = date_val.strftime("%Y-%m-%d")
                else:
                    candle_date = str(date_val)[:10]

                if candle_date == predicted_date:
                    h = float(row["High"])
                    l = float(row["Low"])
                    o = float(row["Open"])
                    c = float(row["Close"])
                    if h > actual_high:
                        actual_high = h
                    if l < actual_low:
                        actual_low = l
                    last_close = c
                    if first_open is None:
                        actual_open = o
                        first_open = o

            if actual_high == -float("inf"):
                return Outcome.UNCHECKED.value, {"error": f"No intraday candles found for {predicted_date}"}

            actual_close = last_close or actual_close

        else:
            # ── Daily backtest: fetch daily OHLC data ──
            rows = await provider.fetch_daily_range(
                prediction["symbol"], start_dt, end_dt
            )

            if not rows:
                return Outcome.UNCHECKED.value, {"error": f"No data available for {predicted_date}"}

            # Find the candle that matches our predicted_date (or the next trading day)
            target_candle = None
            for row in rows:
                date_val = row["Date"]
                if hasattr(date_val, "strftime"):
                    candle_date = date_val.strftime("%Y-%m-%d")
                else:
                    candle_date = str(date_val)[:10]
                if candle_date >= predicted_date:
                    target_candle = row
                    break

            if target_candle is None:
                target_candle = rows[0]

            actual_high = float(target_candle["High"])
            actual_low = float(target_candle["Low"])
            actual_close = float(target_candle["Close"])
            actual_open = float(target_candle["Open"])

        details = {
            "entry_zone": entry,
            "stop_loss": stop_loss,
            "target": target,
            "actual_high": actual_high,
            "actual_low": actual_low,
            "actual_close": actual_close,
            "actual_open": actual_open,
        }

        # Determine outcome based on bias
        target_hit = False
        stoploss_hit = False

        if bias == "Buy":
            # For Buy: price needs to go UP
            if target and actual_high >= target:
                target_hit = True
            if stop_loss and actual_low <= stop_loss:
                stoploss_hit = True

            # If both hit, check intraday data to see which happened first
            if target_hit and stoploss_hit:
                first_event = await _which_happened_first(prediction["symbol"], predicted_date, stop_loss, target, bias)
                if first_event == "target":
                    stoploss_hit = False  # target hit first
                elif first_event == "stoploss":
                    target_hit = False  # stoploss hit first

        elif bias == "Sell":
            # For Sell: price needs to go DOWN
            if target and actual_low <= target:
                target_hit = True
            if stop_loss and actual_high >= stop_loss:
                stoploss_hit = True

            if target_hit and stoploss_hit:
                first_event = await _which_happened_first(prediction["symbol"], predicted_date, stop_loss, target, bias)
                if first_event == "target":
                    stoploss_hit = False
                elif first_event == "stoploss":
                    target_hit = False

        if target_hit:
            status = Outcome.HIT_TARGET.value
            details["outcome"] = "Target was hit"
        elif stoploss_hit:
            status = Outcome.HIT_STOPLOSS.value
            details["outcome"] = "Stop loss was hit"
        else:
            status = Outcome.NO_TRADE.value
            details["outcome"] = f"Neither target ({target}) nor stop loss ({stop_loss}) was reached. Day range: {actual_low}-{actual_high}"

        return status, details

    except Exception as e:
        return Outcome.UNCHECKED.value, {"error": str(e)}


async def _which_happened_first(symbol, date_str, stop_loss, target, bias):
    """
    Check intraday data to determine whether the target or stoploss was hit first.
    Returns 'target', 'stoploss', or 'unknown'.
    """
    try:
        start_dt = datetime.strptime(date_str, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=BACKTEST_BUFFER_DAYS_INTRADAY)

        provider = _get_provider()
        rows = await provider.fetch_intraday_range(
            symbol, start_dt, end_dt, interval=BACKTEST_INTRADAY_INTERVAL
        )
        if not rows:
            return "unknown"

        for row in rows:
            candle_high = float(row["High"])
            candle_low = float(row["Low"])

            if bias == "Buy":
                if target and candle_high >= target:
                    return "target"
                if stop_loss and candle_low <= stop_loss:
                    return "stoploss"
            elif bias == "Sell":
                if stop_loss and candle_high >= stop_loss:
                    return "stoploss"
                if target and candle_low <= target:
                    return "target"

        return "unknown"
    except Exception:
        return "unknown"


def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    d = dict(row)
    # Parse JSON fields back to Python objects
    for json_field in ("support_levels", "resistance_levels", "fibonacci_levels",
                       "buy_scenario", "sell_scenario", "result_details"):
        if d.get(json_field) and isinstance(d[json_field], str):
            try:
                d[json_field] = json.loads(d[json_field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d

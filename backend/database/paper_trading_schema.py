"""
Paper Trading Persistence Schema — SQLite tables for paper positions, trades,
execution attempts, and position events.

Extends the existing learning database pattern at backend/learning/database.py.
Uses the same DB_PATH from core.settings.
"""

import sqlite3
import json
from datetime import datetime, timezone
from core.settings import DB_PATH


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_paper_trading_tables():
    """Create all paper-trading persistence tables."""
    conn = _get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_positions (
            trade_id                TEXT PRIMARY KEY,
            status                  TEXT NOT NULL DEFAULT 'OPEN',
            execution_type          TEXT NOT NULL DEFAULT 'option_buying',
            symbol                  TEXT NOT NULL DEFAULT '',
            execution_symbol        TEXT NOT NULL DEFAULT '',
            underlying_symbol       TEXT DEFAULT '',
            direction               TEXT NOT NULL DEFAULT 'LONG',
            quantity                INTEGER NOT NULL DEFAULT 0,
            entry_price             REAL NOT NULL DEFAULT 0.0,
            current_premium         REAL DEFAULT 0.0,
            stop_loss               REAL,
            target                  REAL,
            premium_entry           REAL,
            premium_current         REAL,
            premium_stop_loss       REAL,
            premium_target          REAL,
            lot_size                INTEGER,
            lots                    INTEGER,
            option_type             TEXT,
            strike                  REAL,
            expiry                  TEXT,
            exchange                TEXT DEFAULT 'NSE',
            instrument_token        INTEGER DEFAULT 0,
            premium_source          TEXT DEFAULT '',
            premium_data_status     TEXT DEFAULT 'WAITING_FOR_FIRST_TICK',
            last_premium_tick_at    TEXT,
            underlying_entry        REAL,
            underlying_current      REAL,
            risk_reward             REAL,
            ai_confidence           REAL DEFAULT 0.0,
            opportunity_score       REAL DEFAULT 0.0,
            trade_grade             TEXT DEFAULT '',
            decision_id             TEXT DEFAULT '',
            analysis_cycle_id       TEXT DEFAULT '',
            strategy_version        TEXT DEFAULT '1.0',
            premium_instrument_token INTEGER DEFAULT 0,
            created_at              TEXT NOT NULL,
            updated_at              TEXT,
            source_provenance       TEXT DEFAULT '',
            settings_snapshot       TEXT,
            risk_snapshot           TEXT,
            test_origin             TEXT DEFAULT '',
            recovery_info           TEXT,
            CONSTRAINT valid_status CHECK (status IN ('OPEN','CLOSED','RECOVERY_ERROR'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_trades (
            trade_id                TEXT PRIMARY KEY,
            status                  TEXT NOT NULL DEFAULT 'CLOSED',
            execution_type          TEXT NOT NULL DEFAULT 'option_buying',
            symbol                  TEXT NOT NULL DEFAULT '',
            execution_symbol        TEXT NOT NULL DEFAULT '',
            underlying_symbol       TEXT DEFAULT '',
            direction               TEXT NOT NULL DEFAULT 'LONG',
            quantity                INTEGER NOT NULL DEFAULT 0,
            entry_price             REAL NOT NULL DEFAULT 0.0,
            exit_premium            REAL,
            premium_entry           REAL,
            premium_exit            REAL,
            premium_stop_loss       REAL,
            premium_target          REAL,
            lot_size                INTEGER,
            lots                    INTEGER,
            option_type             TEXT,
            strike                  REAL,
            expiry                  TEXT,
            exit_price              REAL,
            realized_pnl            REAL DEFAULT 0.0,
            pnl_percent             REAL DEFAULT 0.0,
            entry_time              TEXT NOT NULL,
            exit_time               TEXT,
            exit_reason             TEXT DEFAULT '',
            exit_price_source       TEXT DEFAULT '',
            emergency_exit_reason   TEXT DEFAULT '',
            duration_seconds        INTEGER DEFAULT 0,
            max_favorable           REAL,
            max_adverse             REAL,
            ai_confidence           REAL DEFAULT 0.0,
            opportunity_score       REAL DEFAULT 0.0,
            trade_grade             TEXT DEFAULT '',
            risk_reward             REAL,
            premium_source          TEXT DEFAULT '',
            exchange                TEXT DEFAULT 'NSE',
            instrument_token        INTEGER DEFAULT 0,
            decision_id             TEXT DEFAULT '',
            analysis_cycle_id       TEXT DEFAULT '',
            source_provenance       TEXT DEFAULT '',
            closing_timestamp       TEXT,
            test_origin             TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_execution_attempts (
            attempt_id              TEXT PRIMARY KEY,
            timestamp               TEXT NOT NULL,
            underlying_symbol       TEXT NOT NULL DEFAULT '',
            direction               TEXT NOT NULL DEFAULT '',
            analysis_cycle_id       TEXT DEFAULT '',
            stage                   TEXT NOT NULL DEFAULT '',
            block_code              TEXT NOT NULL DEFAULT '',
            block_reason            TEXT DEFAULT '',
            actual_value            TEXT DEFAULT '',
            required_value          TEXT DEFAULT '',
            settings_snapshot       TEXT,
            risk_snapshot           TEXT,
            created_at              TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_position_events (
            event_id                TEXT PRIMARY KEY,
            trade_id                TEXT NOT NULL,
            event_type              TEXT NOT NULL,
            timestamp               TEXT NOT NULL,
            premium                 REAL,
            underlying_price        REAL,
            reason                  TEXT DEFAULT '',
            details                 TEXT,
            created_at              TEXT NOT NULL,
            FOREIGN KEY (trade_id) REFERENCES paper_positions(trade_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS runtime_mode_audit (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp               TEXT NOT NULL,
            previous_mode           TEXT,
            new_mode                TEXT NOT NULL,
            source                  TEXT DEFAULT 'api',
            user_action             INTEGER DEFAULT 1,
            details                 TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS paper_account_snapshots (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp               TEXT NOT NULL,
            initial_capital         REAL NOT NULL DEFAULT 100000.0,
            available_cash          REAL NOT NULL DEFAULT 100000.0,
            used_margin             REAL NOT NULL DEFAULT 0.0,
            equity                  REAL NOT NULL DEFAULT 100000.0,
            total_unrealized_pnl    REAL NOT NULL DEFAULT 0.0,
            total_realized_pnl      REAL NOT NULL DEFAULT 0.0,
            total_pnl               REAL NOT NULL DEFAULT 0.0,
            open_positions_count    INTEGER NOT NULL DEFAULT 0,
            closed_trades_count     INTEGER NOT NULL DEFAULT 0,
            win_count               INTEGER NOT NULL DEFAULT 0,
            loss_count              INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]

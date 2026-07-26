"""
Regime Database — stores regime snapshots, transitions, and strategy snapshots.
"""

from __future__ import annotations

import sqlite3

from core.settings import DB_PATH


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_regime_tables():
    """Create regime history, transition, and strategy snapshot tables."""
    conn = _get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_history (
            id              TEXT PRIMARY KEY,
            symbol          TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            regime          TEXT NOT NULL,
            regime_category TEXT,
            confidence      INTEGER NOT NULL DEFAULT 0,
            supporting_factors TEXT,
            duration_bars   INTEGER DEFAULT 0,
            duration_minutes INTEGER DEFAULT 0,
            stability_score REAL DEFAULT 0,
            transition_probability REAL DEFAULT 0,
            previous_regime TEXT,
            strategy_primary TEXT,
            strategy_secondary TEXT,
            confidence_adjustment INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_transition_history (
            id              TEXT PRIMARY KEY,
            symbol          TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            from_regime     TEXT NOT NULL,
            to_regime       TEXT NOT NULL,
            transition_type TEXT NOT NULL,
            confidence      REAL DEFAULT 0,
            duration_bars   INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_strategy_snapshot (
            id              TEXT PRIMARY KEY,
            regime          TEXT NOT NULL,
            strategy_id     TEXT NOT NULL,
            strategy_name   TEXT NOT NULL,
            total_trades    INTEGER DEFAULT 0,
            win_rate        REAL,
            profit_factor   REAL,
            expectancy      REAL,
            sharpe_ratio    REAL,
            max_drawdown    REAL,
            avg_holding_hours REAL,
            snapshot_date   TEXT NOT NULL,
            UNIQUE(regime, strategy_id, snapshot_date)
        )
    """)

    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_rh_symbol ON regime_history(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_rh_timestamp ON regime_history(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_rh_regime ON regime_history(regime)",
        "CREATE INDEX IF NOT EXISTS idx_rth_symbol ON regime_transition_history(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_rth_type ON regime_transition_history(transition_type)",
        "CREATE INDEX IF NOT EXISTS idx_rss_regime ON regime_strategy_snapshot(regime)",
        "CREATE INDEX IF NOT EXISTS idx_rss_strategy ON regime_strategy_snapshot(strategy_id)",
    ]:
        conn.execute(idx)

    conn.commit()
    conn.close()

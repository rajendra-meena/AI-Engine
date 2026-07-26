"""
AI Performance Database — SQLite tables for trade evaluation, strategy & pattern analysis.
Extends the learning/database.py pattern with Phase 57 specific tables.
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


def init_ai_performance_tables():
    """Create all AI performance analytics tables."""
    conn = _get_db()

    # Table 1: Trade Evaluation (per-trade post-hoc scoring)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_perf_trade_evaluation (
            id              TEXT PRIMARY KEY,
            prediction_id   TEXT UNIQUE NOT NULL,
            entry_accuracy  REAL,
            exit_quality    REAL,
            sl_quality      REAL,
            target_quality  REAL,
            mfe_mae_ratio   REAL,
            slippage_impact REAL,
            overall_score   REAL,
            outcome_class   TEXT,
            evaluated_at    TEXT NOT NULL,
            FOREIGN KEY (prediction_id) REFERENCES prediction_journal(id)
        )
    """)

    # Table 2: Strategy Performance Snapshot
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_perf_strategy_snapshot (
            id              TEXT PRIMARY KEY,
            strategy_id     TEXT NOT NULL,
            strategy_name   TEXT NOT NULL,
            total_trades    INTEGER DEFAULT 0,
            win_rate        REAL,
            profit_factor   REAL,
            expectancy      REAL,
            sharpe_ratio    REAL,
            recovery_factor REAL,
            max_drawdown    REAL,
            avg_holding_hours REAL,
            snapshot_date   TEXT NOT NULL,
            UNIQUE(strategy_id, snapshot_date)
        )
    """)

    # Table 3: Pattern Performance
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_perf_pattern_performance (
            id              TEXT PRIMARY KEY,
            pattern_name    TEXT NOT NULL,
            pattern_type    TEXT,
            total_occurrences INTEGER DEFAULT 0,
            win_count       INTEGER DEFAULT 0,
            loss_count      INTEGER DEFAULT 0,
            win_rate        REAL,
            avg_return      REAL,
            avg_duration_hours REAL,
            failure_rate    REAL,
            observation_date TEXT NOT NULL,
            UNIQUE(pattern_name, observation_date)
        )
    """)

    # Table 4: Market Condition Performance
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_perf_market_condition (
            id              TEXT PRIMARY KEY,
            condition_type  TEXT NOT NULL,
            condition_value TEXT NOT NULL,
            total_trades    INTEGER DEFAULT 0,
            win_count       INTEGER DEFAULT 0,
            win_rate        REAL,
            avg_return      REAL,
            profit_factor   REAL,
            observation_date TEXT NOT NULL,
            UNIQUE(condition_type, condition_value, observation_date)
        )
    """)

    # Table 5: Mistake Log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_perf_mistake_log (
            id              TEXT PRIMARY KEY,
            prediction_id   TEXT NOT NULL,
            mistake_type    TEXT NOT NULL,
            severity        TEXT,
            description     TEXT,
            impact          REAL,
            lesson          TEXT,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (prediction_id) REFERENCES prediction_journal(id)
        )
    """)

    # Indexes
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_apte_prediction ON ai_perf_trade_evaluation(prediction_id)",
        "CREATE INDEX IF NOT EXISTS idx_apte_outcome ON ai_perf_trade_evaluation(outcome_class)",
        "CREATE INDEX IF NOT EXISTS idx_apss_strategy ON ai_perf_strategy_snapshot(strategy_id)",
        "CREATE INDEX IF NOT EXISTS idx_appp_pattern ON ai_perf_pattern_performance(pattern_name)",
        "CREATE INDEX IF NOT EXISTS idx_apmc_condition ON ai_perf_market_condition(condition_type)",
        "CREATE INDEX IF NOT EXISTS idx_apml_mistake ON ai_perf_mistake_log(mistake_type)",
        "CREATE INDEX IF NOT EXISTS idx_apml_prediction ON ai_perf_mistake_log(prediction_id)",
    ]:
        conn.execute(idx)

    conn.commit()
    conn.close()

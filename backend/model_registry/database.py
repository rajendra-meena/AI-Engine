"""Model Registry Database — persistent tables for models, versions, lineage, evaluations."""

from __future__ import annotations

import sqlite3
from core.settings import DB_PATH


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_model_registry_tables():
    """Create all model governance tables."""
    conn = _get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_registry (
            id                  TEXT PRIMARY KEY,
            name                TEXT NOT NULL,
            description         TEXT,
            version             TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'draft',
            model_type          TEXT,
            algorithm           TEXT,
            feature_set_version TEXT,
            indicator_version   TEXT,
            regime_compatibility TEXT,
            strategy_compatibility TEXT,
            parent_model_id     TEXT,
            dataset_reference   TEXT,
            hyperparameters     TEXT,
            training_timestamp  TEXT,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL,
            UNIQUE(name, version)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_evaluation_record (
            id              TEXT PRIMARY KEY,
            model_id        TEXT NOT NULL,
            evaluation_type TEXT NOT NULL,
            win_rate        REAL,
            profit_factor   REAL,
            max_drawdown    REAL,
            sharpe_ratio    REAL,
            sortino_ratio   REAL,
            calmar_ratio    REAL,
            expectancy      REAL,
            total_trades    INTEGER,
            stability_score REAL,
            calibration_score REAL,
            regime_performance TEXT,
            strategy_performance TEXT,
            walk_forward_score REAL,
            oos_win_rate    REAL,
            oos_sharpe      REAL,
            generalization_score REAL,
            evaluated_at    TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (model_id) REFERENCES model_registry(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_comparison (
            id                  TEXT PRIMARY KEY,
            champion_model_id   TEXT NOT NULL,
            challenger_model_id TEXT NOT NULL,
            same_signal_pct     REAL,
            different_signal_pct REAL,
            champion_win_rate   REAL,
            challenger_win_rate REAL,
            champion_sharpe     REAL,
            challenger_sharpe   REAL,
            confidence_diff     REAL,
            strategy_diff       TEXT,
            regime_diff         TEXT,
            better_entry_pct    REAL,
            better_exit_pct     REAL,
            comparison_date     TEXT NOT NULL,
            created_at          TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_promotion_log (
            id              TEXT PRIMARY KEY,
            model_id        TEXT NOT NULL,
            action          TEXT NOT NULL,
            previous_status TEXT NOT NULL,
            new_status      TEXT NOT NULL,
            reason          TEXT,
            recommendation  TEXT,
            human_reviewed  INTEGER DEFAULT 0,
            reviewer_id     TEXT,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (model_id) REFERENCES model_registry(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_lineage (
            id              TEXT PRIMARY KEY,
            model_id        TEXT NOT NULL,
            parent_model_id TEXT,
            event_type      TEXT NOT NULL,
            event_detail    TEXT,
            version_before  TEXT,
            version_after   TEXT,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (model_id) REFERENCES model_registry(id),
            FOREIGN KEY (parent_model_id) REFERENCES model_registry(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS walk_forward_result (
            id              TEXT PRIMARY KEY,
            model_id        TEXT NOT NULL,
            window_index    INTEGER NOT NULL,
            train_start     TEXT NOT NULL,
            train_end       TEXT NOT NULL,
            val_start       TEXT NOT NULL,
            val_end         TEXT NOT NULL,
            train_win_rate  REAL,
            train_profit_factor REAL,
            train_sharpe    REAL,
            train_max_dd    REAL,
            val_win_rate    REAL,
            val_profit_factor REAL,
            val_sharpe      REAL,
            val_max_dd      REAL,
            generalization_score REAL,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (model_id) REFERENCES model_registry(id)
        )
    """)

    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_mr_status ON model_registry(status)",
        "CREATE INDEX IF NOT EXISTS idx_mr_name ON model_registry(name)",
        "CREATE INDEX IF NOT EXISTS idx_mer_model ON model_evaluation_record(model_id)",
        "CREATE INDEX IF NOT EXISTS idx_mc_champion ON model_comparison(champion_model_id)",
        "CREATE INDEX IF NOT EXISTS idx_mpl_model ON model_promotion_log(model_id)",
        "CREATE INDEX IF NOT EXISTS idx_ml_model ON model_lineage(model_id)",
        "CREATE INDEX IF NOT EXISTS idx_wfr_model ON walk_forward_result(model_id)",
    ]:
        conn.execute(idx)

    conn.commit()
    conn.close()

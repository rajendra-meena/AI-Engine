"""
AI Learning Database — SQLite tables for the learning feedback loop.
Extends the existing database.py pattern.
"""

import sqlite3

from core.settings import DB_PATH


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_learning_tables():
    """Create all learning-related database tables."""
    conn = _get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_journal (
            id              TEXT PRIMARY KEY,
            symbol          TEXT NOT NULL,
            exchange        TEXT DEFAULT 'NSE',
            interval        TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            decision        TEXT NOT NULL,
            direction       TEXT,
            score           INTEGER NOT NULL,
            confidence      INTEGER NOT NULL,
            risk_score      INTEGER,
            risk_level      TEXT,
            entry_price     REAL,
            stop_loss       REAL,
            target          REAL,
            risk_reward     REAL,
            strategy_id     TEXT,
            model_id        TEXT,
            model_version   TEXT,
            market_regime   TEXT,
            trend           TEXT,
            market_phase    TEXT,
            institutional_bias TEXT,
            mtf_alignment   TEXT,
            volatility      REAL,
            momentum        REAL,
            feature_snapshot    TEXT,
            indicator_snapshot  TEXT,
            pattern_snapshot    TEXT,
            structure_snapshot  TEXT,
            sr_snapshot         TEXT,
            news_context        TEXT,
            market_context      TEXT,
            regime          TEXT,
            user_id         TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_outcome (
            id                      TEXT PRIMARY KEY,
            prediction_id           TEXT UNIQUE NOT NULL,
            outcome_5m              TEXT,
            outcome_15m             TEXT,
            outcome_30m             TEXT,
            outcome_60m             TEXT,
            outcome_session         TEXT,
            outcome_eod             TEXT,
            max_favorable_excursion REAL,
            max_adverse_excursion   REAL,
            target_hit              INTEGER,
            stop_loss_hit           INTEGER,
            time_exit               INTEGER,
            manual_exit             INTEGER,
            expired                 INTEGER,
            actual_direction        TEXT,
            actual_return           REAL,
            maximum_return          REAL,
            maximum_drawdown        REAL,
            error_category          TEXT,
            error_reason            TEXT,
            created_at              TEXT NOT NULL,
            updated_at              TEXT NOT NULL,
            FOREIGN KEY (prediction_id) REFERENCES prediction_journal(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_feedback (
            id              TEXT PRIMARY KEY,
            prediction_id   TEXT UNIQUE NOT NULL,
            entry_slippage  REAL,
            exit_slippage   REAL,
            commission      REAL,
            taxes           REAL,
            brokerage       REAL,
            gross_pnl       REAL,
            net_pnl         REAL,
            planned_risk    REAL,
            actual_risk     REAL,
            planned_rr      REAL,
            actual_rr       REAL,
            holding_duration INTEGER,
            exit_reason     TEXT,
            risk_firewall_result TEXT,
            strategy_result     TEXT,
            model_result        TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            FOREIGN KEY (prediction_id) REFERENCES prediction_journal(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS blocked_trade (
            id                      TEXT PRIMARY KEY,
            prediction_id           TEXT UNIQUE NOT NULL,
            blocked_by              TEXT NOT NULL,
            reason                  TEXT NOT NULL,
            risk_score              INTEGER,
            would_have_been_profitable INTEGER,
            hypothetical_return     REAL,
            hypothetical_rr         REAL,
            actual_market_move      REAL,
            created_at              TEXT NOT NULL,
            updated_at              TEXT NOT NULL,
            FOREIGN KEY (prediction_id) REFERENCES prediction_journal(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_recommendation (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            finding         TEXT NOT NULL,
            evidence        TEXT,
            sample_count    INTEGER DEFAULT 0,
            confidence      REAL,
            expected_impact TEXT,
            risk            TEXT,
            recommendation  TEXT NOT NULL,
            action          TEXT,
            category        TEXT,
            status          TEXT DEFAULT 'NEW',
            approved_at     TEXT,
            rejected_at     TEXT,
            rejection_reason TEXT,
            implemented_at  TEXT,
            rolled_back_at  TEXT,
            user_id         TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS calibration_bucket (
            id                  TEXT PRIMARY KEY,
            bucket              TEXT UNIQUE NOT NULL,
            bucket_min          REAL NOT NULL,
            bucket_max          REAL NOT NULL,
            total_predictions   INTEGER DEFAULT 0,
            correct_count       INTEGER DEFAULT 0,
            actual_accuracy     REAL,
            average_confidence  REAL,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feature_observation (
            id                      TEXT PRIMARY KEY,
            feature_name            TEXT NOT NULL,
            importance              REAL,
            correlation_with_outcome REAL,
            positive_rate           REAL,
            negative_rate           REAL,
            win_rate_when_aligned   REAL,
            win_rate_when_conflicting REAL,
            sample_count            INTEGER DEFAULT 0,
            drift_score             REAL,
            observation_date        TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shadow_prediction (
            id                      TEXT PRIMARY KEY,
            symbol                  TEXT NOT NULL,
            interval                TEXT NOT NULL,
            timestamp               TEXT NOT NULL,
            champion_decision       TEXT,
            champion_score          INTEGER,
            champion_confidence     INTEGER,
            challenger_decision     TEXT,
            challenger_score        INTEGER,
            challenger_confidence   INTEGER,
            actual_outcome          TEXT,
            actual_return           REAL,
            winner                  TEXT,
            performance_diff        REAL,
            model_id                TEXT,
            created_at              TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_evaluation (
            id              TEXT PRIMARY KEY,
            model_id        TEXT NOT NULL,
            model_name      TEXT NOT NULL,
            model_version   INTEGER DEFAULT 1,
            model_type      TEXT DEFAULT 'challenger',
            accuracy        REAL,
            precision       REAL,
            recall          REAL,
            f1_score        REAL,
            sharpe_ratio    REAL,
            win_rate        REAL,
            profit_factor   REAL,
            max_drawdown    REAL,
            calibration     REAL,
            oos_accuracy    REAL,
            oos_sharpe      REAL,
            oos_win_rate    REAL,
            regime_performance TEXT,
            trained_at      TEXT,
            evaluated_at    TEXT,
            created_at      TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_performance (
            id              TEXT PRIMARY KEY,
            regime          TEXT NOT NULL,
            total_predictions INTEGER DEFAULT 0,
            total_trades    INTEGER DEFAULT 0,
            win_rate        REAL,
            average_return  REAL,
            profit_factor   REAL,
            sharpe_ratio    REAL,
            max_drawdown    REAL,
            confidence_accuracy REAL,
            observation_date TEXT NOT NULL,
            UNIQUE(regime, observation_date)
        )
    """)

    # Indexes
    for idx in [
        "CREATE INDEX IF NOT EXISTS idx_pj_symbol ON prediction_journal(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_pj_timestamp ON prediction_journal(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_pj_score ON prediction_journal(score)",
        "CREATE INDEX IF NOT EXISTS idx_pj_regime ON prediction_journal(regime)",
        "CREATE INDEX IF NOT EXISTS idx_po_error ON prediction_outcome(error_category)",
        "CREATE INDEX IF NOT EXISTS idx_tf_pnl ON trade_feedback(gross_pnl)",
        "CREATE INDEX IF NOT EXISTS idx_bt_blocked ON blocked_trade(blocked_by)",
        "CREATE INDEX IF NOT EXISTS idx_lr_status ON learning_recommendation(status)",
        "CREATE INDEX IF NOT EXISTS idx_fo_feature ON feature_observation(feature_name)",
        "CREATE INDEX IF NOT EXISTS idx_me_model ON model_evaluation(model_id)",
        "CREATE INDEX IF NOT EXISTS idx_me_type ON model_evaluation(model_type)",
        "CREATE INDEX IF NOT EXISTS idx_sp_symbol ON shadow_prediction(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_sp_winner ON shadow_prediction(winner)",
        "CREATE INDEX IF NOT EXISTS idx_rp_regime ON regime_performance(regime)",
    ]:
        conn.execute(idx)

    conn.commit()
    conn.close()

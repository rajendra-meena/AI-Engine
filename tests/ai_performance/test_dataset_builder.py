"""Tests for AIPerformanceDatasetBuilder — 8 tests."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from ai_performance.dataset_builder import AIPerformanceDatasetBuilder


class TestDatasetBuilder:
    def _make_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prediction_journal (
                id TEXT PRIMARY KEY, symbol TEXT, timestamp TEXT, interval TEXT,
                decision TEXT, direction TEXT, score INTEGER, confidence INTEGER,
                risk_score INTEGER, risk_level TEXT,
                entry_price REAL, stop_loss REAL, target REAL, risk_reward REAL,
                strategy_id TEXT, model_id TEXT,
                market_regime TEXT, trend TEXT, market_phase TEXT,
                institutional_bias TEXT, mtf_alignment TEXT,
                volatility REAL, momentum REAL,
                feature_snapshot TEXT, indicator_snapshot TEXT,
                pattern_snapshot TEXT, structure_snapshot TEXT,
                sr_snapshot TEXT, news_context TEXT, market_context TEXT,
                regime TEXT, created_at TEXT
            );
            INSERT INTO prediction_journal VALUES
                ('p1', 'NIFTY', '2026-07-26T09:30:00Z', '15m', 'HIGH_CONVICTION',
                 'BUY', 85, 80, 20, 'LOW', 25100, 24800, 25700, 2.0,
                 'trend_following', NULL,
                 'TRENDING', 'BULLISH', 'markup',
                 NULL, 'STRONG_ALIGNMENT',
                 120, 0.8,
                 NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                 NULL, '2026-07-26T09:30:00Z');
            CREATE TABLE IF NOT EXISTS prediction_outcome (
                id TEXT PRIMARY KEY, prediction_id TEXT UNIQUE,
                outcome_eod TEXT, actual_return REAL,
                max_favorable_excursion REAL, max_adverse_excursion REAL,
                target_hit INTEGER, stop_loss_hit INTEGER,
                error_category TEXT, error_reason TEXT,
                maximum_return REAL, maximum_drawdown REAL
            );
            INSERT INTO prediction_outcome VALUES
                ('o1', 'p1', 'WIN', 250, 300, -50, 0, 0, '', '', 300, -50);
            CREATE TABLE IF NOT EXISTS trade_feedback (
                id TEXT PRIMARY KEY, prediction_id TEXT UNIQUE,
                entry_slippage REAL, exit_slippage REAL,
                gross_pnl REAL, net_pnl REAL, actual_risk REAL,
                actual_rr REAL, holding_duration INTEGER, exit_reason TEXT
            );
            INSERT INTO trade_feedback VALUES
                ('f1', 'p1', 2.5, 1.5, 250, 246, 300, 2.0, 180, 'target');
            CREATE TABLE IF NOT EXISTS ai_perf_trade_evaluation (
                id TEXT PRIMARY KEY, prediction_id TEXT UNIQUE,
                overall_score REAL, outcome_class TEXT,
                entry_accuracy REAL, exit_quality REAL,
                sl_quality REAL, target_quality REAL,
                mfe_mae_ratio REAL, slippage_impact REAL,
                evaluated_at TEXT
            );
            INSERT INTO ai_perf_trade_evaluation VALUES
                ('e1', 'p1', 82, 'Good', 85, 75, 90, 100, 85, 1.3, '2026-07-26T10:00:00Z');
        """)
        return conn

    def test_build_dataset(self):
        db = self._make_db()
        records = AIPerformanceDatasetBuilder.build_evaluation_dataset(db)
        assert len(records) >= 1
        assert records[0]["prediction_id"] == "p1"
        assert records[0]["overall_score"] == 82

    def test_dataset_contains_all_columns(self):
        db = self._make_db()
        records = AIPerformanceDatasetBuilder.build_evaluation_dataset(db)
        r = records[0]
        assert "prediction_id" in r
        assert "actual_return" in r
        assert "overall_score" in r
        assert "outcome_class" in r
        assert "entry_slippage" in r

    def test_json_export(self):
        db = self._make_db()
        data = AIPerformanceDatasetBuilder.export_dataset(db, "json")
        parsed = json.loads(data)
        assert len(parsed) >= 1
        assert parsed[0]["symbol"] == "NIFTY"

    def test_json_export_empty(self):
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE prediction_journal (id TEXT PRIMARY KEY, symbol TEXT)")
        data = AIPerformanceDatasetBuilder.export_dataset(db, "json")
        parsed = json.loads(data)
        assert len(parsed) == 0

    def test_csv_export(self):
        db = self._make_db()
        data = AIPerformanceDatasetBuilder.export_dataset(db, "csv")
        assert isinstance(data, bytes)
        decoded = data.decode("utf-8")
        assert "prediction_id" in decoded
        assert "p1" in decoded

    def test_get_dataset_stats(self):
        db = self._make_db()
        stats = AIPerformanceDatasetBuilder.get_dataset_stats(db)
        assert stats["total_records"] >= 1
        assert stats["with_outcome"] >= 1
        assert stats["with_evaluation"] >= 1

    def test_stats_by_outcome_class(self):
        db = self._make_db()
        stats = AIPerformanceDatasetBuilder.get_dataset_stats(db)
        assert "Good" in stats["by_outcome_class"]

    def test_dataset_limit(self):
        db = self._make_db()
        records = AIPerformanceDatasetBuilder.build_evaluation_dataset(db, limit=1)
        assert len(records) >= 1

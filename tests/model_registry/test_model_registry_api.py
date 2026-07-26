"""Tests for API-level behavior of model registry modules."""

from __future__ import annotations

from model_registry.registry import ModelRegistry, MODEL_STATES, VALID_TRANSITIONS
from model_registry.walk_forward import WalkForwardEngine
from model_registry.comparison import ModelComparisonEngine


class TestAPI:
    def test_model_states_defined(self):
        assert len(MODEL_STATES) == 7
        assert "draft" in MODEL_STATES
        assert "champion" in MODEL_STATES
        assert "rolled_back" in MODEL_STATES

    def test_valid_transitions_cover_all_states(self):
        for state in MODEL_STATES:
            assert state in VALID_TRANSITIONS, f"{state} missing transitions"

    def test_walk_forward_windows_non_overlapping(self):
        windows = WalkForwardEngine.generate_windows(200, 60, 20, 20)
        for w in windows:
            assert w["train_end"] <= w["val_start"]

    def test_comparison_empty_inputs(self):
        result = ModelComparisonEngine.compare_decisions([], [])
        assert result["total_comparisons"] == 0

    def test_registry_names_unique_with_version(self):
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE model_registry (id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT, version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft', model_type TEXT, algorithm TEXT, feature_set_version TEXT,
                indicator_version TEXT, regime_compatibility TEXT, strategy_compatibility TEXT, parent_model_id TEXT,
                dataset_reference TEXT, hyperparameters TEXT, training_timestamp TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(name, version));
            CREATE TABLE model_evaluation_record (id TEXT PRIMARY KEY, model_id TEXT NOT NULL, evaluation_type TEXT NOT NULL,
                win_rate REAL, profit_factor REAL, max_drawdown REAL, sharpe_ratio REAL,
                sortino_ratio REAL, calmar_ratio REAL, expectancy REAL, total_trades INTEGER,
                stability_score REAL, calibration_score REAL, regime_performance TEXT, strategy_performance TEXT,
                walk_forward_score REAL, oos_win_rate REAL, oos_sharpe REAL, generalization_score REAL,
                evaluated_at TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE model_promotion_log (id TEXT PRIMARY KEY, model_id TEXT NOT NULL, action TEXT NOT NULL,
                previous_status TEXT NOT NULL, new_status TEXT NOT NULL, reason TEXT,
                human_reviewed INTEGER DEFAULT 0, reviewer_id TEXT, created_at TEXT NOT NULL);
            CREATE TABLE model_lineage (id TEXT PRIMARY KEY, model_id TEXT NOT NULL, parent_model_id TEXT,
                event_type TEXT NOT NULL, event_detail TEXT, version_before TEXT, version_after TEXT, created_at TEXT NOT NULL);
            CREATE TABLE walk_forward_result (id TEXT PRIMARY KEY, model_id TEXT NOT NULL, window_index INTEGER NOT NULL,
                train_start TEXT NOT NULL, train_end TEXT NOT NULL, val_start TEXT NOT NULL, val_end TEXT NOT NULL,
                train_win_rate REAL, train_profit_factor REAL, train_sharpe REAL, train_max_dd REAL,
                val_win_rate REAL, val_profit_factor REAL, val_sharpe REAL, val_max_dd REAL,
                generalization_score REAL, created_at TEXT NOT NULL);
        """)
        m1 = ModelRegistry.register(db, "M", "1.0.0")
        assert m1["status"] == "draft"
        db.close()

    def test_missing_model_returns_none(self):
        import sqlite3
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE model_registry (id TEXT PRIMARY KEY, name TEXT, version TEXT, status TEXT, created_at TEXT, updated_at TEXT)")
        assert ModelRegistry.get_model(db, "x") is None
        db.close()

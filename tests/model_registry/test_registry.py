"""Tests for ModelRegistry — registration, status transitions, champion/challenger."""

from __future__ import annotations

import sqlite3
import pytest
from model_registry.registry import ModelRegistry, MODEL_STATES, VALID_TRANSITIONS


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS model_registry (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT, version TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft', model_type TEXT, algorithm TEXT,
            feature_set_version TEXT, indicator_version TEXT, regime_compatibility TEXT,
            strategy_compatibility TEXT, parent_model_id TEXT, dataset_reference TEXT,
            hyperparameters TEXT, training_timestamp TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_evaluation_record (
            id TEXT PRIMARY KEY, model_id TEXT NOT NULL, evaluation_type TEXT NOT NULL,
            win_rate REAL, profit_factor REAL, max_drawdown REAL, sharpe_ratio REAL,
            sortino_ratio REAL, calmar_ratio REAL, expectancy REAL, total_trades INTEGER,
            stability_score REAL, calibration_score REAL, regime_performance TEXT,
            strategy_performance TEXT, walk_forward_score REAL, oos_win_rate REAL,
            oos_sharpe REAL, generalization_score REAL, evaluated_at TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_comparison (
            id TEXT PRIMARY KEY, champion_model_id TEXT NOT NULL, challenger_model_id TEXT NOT NULL,
            same_signal_pct REAL, different_signal_pct REAL, champion_win_rate REAL,
            challenger_win_rate REAL, champion_sharpe REAL, challenger_sharpe REAL,
            confidence_diff REAL, strategy_diff TEXT, regime_diff TEXT, better_entry_pct REAL,
            better_exit_pct REAL, comparison_date TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_promotion_log (
            id TEXT PRIMARY KEY, model_id TEXT NOT NULL, action TEXT NOT NULL,
            previous_status TEXT NOT NULL, new_status TEXT NOT NULL, reason TEXT,
            human_reviewed INTEGER DEFAULT 0, reviewer_id TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_lineage (
            id TEXT PRIMARY KEY, model_id TEXT NOT NULL, parent_model_id TEXT,
            event_type TEXT NOT NULL, event_detail TEXT, version_before TEXT, version_after TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS walk_forward_result (
            id TEXT PRIMARY KEY, model_id TEXT NOT NULL, window_index INTEGER NOT NULL,
            train_start TEXT NOT NULL, train_end TEXT NOT NULL, val_start TEXT NOT NULL, val_end TEXT NOT NULL,
            train_win_rate REAL, train_profit_factor REAL, train_sharpe REAL, train_max_dd REAL,
            val_win_rate REAL, val_profit_factor REAL, val_sharpe REAL, val_max_dd REAL,
            generalization_score REAL, created_at TEXT NOT NULL
        );
    """)
    return conn


class TestModelRegistry:
    def test_register_model(self, db):
        m = ModelRegistry.register(db, "TestModel", "1.0.0", "ml", "random_forest")
        assert m["status"] == "draft"
        assert m["name"] == "TestModel"
        assert m["version"] == "1.0.0"

    def test_register_with_parent(self, db):
        parent = ModelRegistry.register(db, "Parent", "1.0.0")
        child = ModelRegistry.register(db, "Child", "1.1.0", parent_model_id=parent["id"])
        assert child["parent_model_id"] == parent["id"]

    def test_set_status_valid(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        result = ModelRegistry.set_status(db, m["id"], "validation")
        assert result["status"] == "validation"

    def test_set_status_invalid_transition(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        with pytest.raises(ValueError):
            ModelRegistry.set_status(db, m["id"], "champion")  # draft can't go to champion

    def test_promote_to_champion_demotes_old(self, db):
        def _to_champion(conn, mid):
            ModelRegistry.set_status(conn, mid, "validation")
            ModelRegistry.set_status(conn, mid, "candidate")
            ModelRegistry.set_status(conn, mid, "champion")

        c1 = ModelRegistry.register(db, "C1", "1.0.0")
        _to_champion(db, c1["id"])

        c2 = ModelRegistry.register(db, "C2", "2.0.0")
        ModelRegistry.set_status(db, c2["id"], "validation")
        ModelRegistry.set_status(db, c2["id"], "candidate")

        # Promote c2 - c1 should be archived
        ModelRegistry.set_status(db, c2["id"], "champion")
        old_champ = ModelRegistry.get_model(db, c1["id"])
        assert old_champ["status"] == "archived"

    def test_get_champion(self, db):
        assert ModelRegistry.get_champion(db) is None
        m = ModelRegistry.register(db, "M", "1.0.0")
        ModelRegistry.set_status(db, m["id"], "validation")
        ModelRegistry.set_status(db, m["id"], "candidate")
        ModelRegistry.set_status(db, m["id"], "champion")
        champ = ModelRegistry.get_champion(db)
        assert champ is not None
        assert champ["id"] == m["id"]

    def test_get_challenger(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        ModelRegistry.set_status(db, m["id"], "validation")
        ModelRegistry.set_status(db, m["id"], "candidate")
        ModelRegistry.set_status(db, m["id"], "challenger")
        assert ModelRegistry.get_challenger(db) is not None

    def test_list_models_filtered(self, db):
        ModelRegistry.register(db, "M1", "1.0.0")
        ModelRegistry.register(db, "M2", "1.0.0")
        all_m = ModelRegistry.list_models(db)
        assert len(all_m) >= 2

    def test_list_status_filtered(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        draft_list = ModelRegistry.list_models(db, "draft")
        assert all(x["status"] == "draft" for x in draft_list)

    def test_get_model_by_id(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        fetched = ModelRegistry.get_model(db, m["id"])
        assert fetched["id"] == m["id"]

    def test_get_model_not_found(self, db):
        assert ModelRegistry.get_model(db, "nonexistent") is None

    def test_valid_transitions_defined(self):
        assert "draft" in VALID_TRANSITIONS
        assert VALID_TRANSITIONS["champion"] == ["rolled_back", "archived"]
        assert VALID_TRANSITIONS["archived"] == []

    def test_lineage_recorded_on_create(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        lineage = ModelRegistry.get_lineage(db, m["id"])
        assert len(lineage) >= 1
        assert lineage[0]["event_type"] == "created"

    def test_lineage_on_status_change(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        ModelRegistry.set_status(db, m["id"], "validation")
        lineage = ModelRegistry.get_lineage(db, m["id"])
        assert len(lineage) >= 2

    def test_promotion_log_created(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        ModelRegistry.set_status(db, m["id"], "validation")
        history = ModelRegistry.get_history(db, m["id"])
        # Each status transition creates a promotion log entry
        assert len(history) >= 1  # at least status change logged
        assert history[0]["action"] == "draft->validation"

    def test_lineage_has_events(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        ModelRegistry.set_status(db, m["id"], "validation")
        lineage = ModelRegistry.get_lineage(db, m["id"])
        assert len(lineage) >= 2  # creation + status change

    def test_save_evaluation(self, db):
        m = ModelRegistry.register(db, "M", "1.0.0")
        eid = ModelRegistry.save_evaluation(db, m["id"], "walk_forward", {
            "win_rate": 65.0, "profit_factor": 1.5, "sharpe_ratio": 0.8, "max_drawdown": 12.0,
        })
        assert eid is not None

"""Tests for ModelComparisonEngine and RollbackGovernor."""

from __future__ import annotations

import sqlite3
import pytest
from model_registry.comparison import ModelComparisonEngine
from model_registry.rollback import RollbackGovernor


class TestModelComparison:
    def test_compare_decisions_same(self):
        champ = [{"decision": "BUY", "confidence": 80}] * 10
        chall = [{"decision": "BUY", "confidence": 75}] * 10
        result = ModelComparisonEngine.compare_decisions(champ, chall)
        assert result["same_signal_pct"] == 100.0

    def test_compare_decisions_different(self):
        champ = [{"decision": "BUY", "confidence": 80}] * 10
        chall = [{"decision": "SELL", "confidence": 75}] * 10
        result = ModelComparisonEngine.compare_decisions(champ, chall)
        assert result["different_signal_pct"] == 100.0

    def test_compare_decisions_mixed(self):
        champ = [{"decision": "BUY", "confidence": 80}] * 10
        chall = ([{"decision": "BUY", "confidence": 75}] * 5) + ([{"decision": "SELL", "confidence": 70}] * 5)
        result = ModelComparisonEngine.compare_decisions(champ, chall)
        assert 40 <= result["same_signal_pct"] <= 60

    def test_compare_entry_quality(self):
        champ = [{"decision": "BUY", "entry_accuracy": 80}] * 10
        chall = [{"decision": "BUY", "entry_accuracy": 60}] * 10
        result = ModelComparisonEngine.compare_decisions(champ, chall)
        assert result["champion_better_entry_pct"] >= 80

    def test_empty_predictions(self):
        result = ModelComparisonEngine.compare_decisions([], [])
        assert result["total_comparisons"] == 0

    def test_promote_recommendation_all_gates_pass(self):
        champ_m = {"total_trades": 150, "win_rate": 60, "profit_factor": 1.4, "sharpe_ratio": 0.7, "max_drawdown": 18.0, "calibration_score": 65}
        chall_m = {"total_trades": 50, "win_rate": 68, "profit_factor": 1.8, "sharpe_ratio": 0.9, "max_drawdown": 10.0, "calibration_score": 78}
        rec = ModelComparisonEngine.compute_promotion_recommendation(champ_m, chall_m, walk_forward_score=75)
        assert rec["decision"] in ("promote", "more_data_required")

    def test_promote_recommendation_keep_champion(self):
        champ_m = {"total_trades": 200, "win_rate": 65, "profit_factor": 1.7, "sharpe_ratio": 0.85, "max_drawdown": 12.0, "calibration_score": 80}
        chall_m = {"total_trades": 15, "win_rate": 55, "profit_factor": 1.1, "sharpe_ratio": 0.3, "max_drawdown": 30.0, "calibration_score": 50}
        rec = ModelComparisonEngine.compute_promotion_recommendation(champ_m, chall_m, walk_forward_score=30)
        assert rec["decision"] in ("keep_champion", "reject_challenger", "more_data_required")

    def test_promotion_reasons_listed(self):
        champ_m = {"total_trades": 100, "win_rate": 60, "profit_factor": 1.4, "sharpe_ratio": 0.7, "max_drawdown": 15.0, "calibration_score": 70}
        chall_m = {"total_trades": 45, "win_rate": 66, "profit_factor": 1.6, "sharpe_ratio": 0.85, "max_drawdown": 12.0, "calibration_score": 75}
        rec = ModelComparisonEngine.compute_promotion_recommendation(champ_m, chall_m, walk_forward_score=72)
        if rec["decision"] == "promote":
            assert len(rec["reasons"]) >= 1

    def test_store_comparison(self, db):
        champ = {"id": "m1", "name": "Champ", "version": "1.0", "status": "champion"}
        chall = {"id": "m2", "name": "Chall", "version": "2.0", "status": "challenger"}
        cid = ModelComparisonEngine.store_comparison(db, champ["id"], chall["id"],
            {"same_signal_pct": 80, "different_signal_pct": 20, "avg_confidence_difference": 5},
            {"champion_win_rate": 62, "challenger_win_rate": 65, "champion_sharpe": 0.7, "challenger_sharpe": 0.85})
        assert cid is not None


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
    """)
    return conn


class TestRollbackGovernor:
    def test_request_rollback_not_champion(self, db):
        db.execute("INSERT INTO model_registry (id, name, version, status, created_at, updated_at) VALUES ('m1', 'M', '1.0', 'draft', 'now', 'now')")
        db.commit()
        with pytest.raises(ValueError, match="not champion"):
            RollbackGovernor.request_rollback(db, "m1", "performance_degradation")

    def test_rollback_request_creates_log(self, db):
        db.execute("INSERT INTO model_registry (id, name, version, status, created_at, updated_at) VALUES ('m1', 'M', '1.0', 'champion', 'now', 'now')")
        db.commit()
        result = RollbackGovernor.request_rollback(db, "m1", "performance_degradation", "admin")
        assert result["status"] == "pending_review"

    def test_approve_rollback(self, db):
        db.execute("INSERT INTO model_registry (id, name, version, status, created_at, updated_at) VALUES ('m1', 'M', '1.0', 'champion', 'now', 'now')")
        db.commit()
        req = RollbackGovernor.request_rollback(db, "m1", "test")
        result = RollbackGovernor.approve_rollback(db, req["rollback_id"], "admin_user")
        assert result["success"] is True
        updated = db.execute("SELECT status FROM model_registry WHERE id = 'm1'").fetchone()
        assert updated["status"] == "rolled_back"

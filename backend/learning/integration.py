"""
Learning Integration Layer — Hooks into existing engines to auto-journal
predictions, record blocked trades, and capture outcomes.

This is the BRIDGE between live trading systems and the Learning Engine.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from learning import engine as lrn
from learning.database import _get_db, init_learning_tables


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Correlation ID generation ──

def generate_correlation_id() -> str:
    """Generate a unique correlation ID for end-to-end traceability."""
    import uuid
    return f"corr_{uuid.uuid4().hex[:16]}"


# ── Journal a prediction from AI Decision Engine output ──

def journal_ai_prediction(
    symbol: str,
    interval: str,
    decision: str,
    score: int,
    confidence: int,
    direction: str | None = None,
    exchange: str = "NSE",
    risk_score: int | None = None,
    risk_level: str | None = None,
    entry_price: float | None = None,
    stop_loss: float | None = None,
    target: float | None = None,
    risk_reward: float | None = None,
    strategy_id: str | None = None,
    model_id: str | None = None,
    model_version: str | None = None,
    market_regime: str | None = None,
    trend: str | None = None,
    market_phase: str | None = None,
    institutional_bias: str | None = None,
    mtf_alignment: str | None = None,
    volatility: float | None = None,
    momentum: float | None = None,
    feature_snapshot: dict | None = None,
    indicator_snapshot: dict | None = None,
    pattern_snapshot: dict | None = None,
    structure_snapshot: dict | None = None,
    sr_snapshot: dict | None = None,
    ml_prediction: str | None = None,
    ml_confidence: float | None = None,
    prediction_source: str = "ai_engine",
    correlation_id: str | None = None,
    user_id: str = "",
) -> str:
    """Journal an AI prediction with the correlation ID for traceability."""
    init_learning_tables()
    corr_id = correlation_id or generate_correlation_id()

    pid = lrn.record_prediction(
        symbol=symbol,
        interval=interval,
        decision=decision,
        score=score,
        confidence=confidence,
        direction=direction,
        exchange=exchange,
        risk_score=risk_score,
        risk_level=risk_level,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target=target,
        risk_reward=risk_reward,
        strategy_id=strategy_id,
        model_id=model_id,
        market_regime=market_regime,
        trend=trend,
        institutional_bias=institutional_bias,
        mtf_alignment=mtf_alignment,
        volatility=volatility,
        momentum=momentum,
        feature_snapshot=feature_snapshot,
        indicator_snapshot=indicator_snapshot,
        pattern_snapshot=pattern_snapshot,
        structure_snapshot=structure_snapshot,
        sr_snapshot=sr_snapshot,
        regime=market_regime,
        user_id=user_id,
    )

    # Store correlation_id + extra fields in a metadata table
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_metadata (
            id TEXT PRIMARY KEY,
            prediction_id TEXT UNIQUE NOT NULL,
            correlation_id TEXT UNIQUE,
            prediction_source TEXT DEFAULT 'ai_engine',
            ml_prediction TEXT,
            ml_confidence REAL,
            ai_decision TEXT,
            model_version TEXT,
            prediction_expiry TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(
        """INSERT OR IGNORE INTO learning_metadata
        (id, prediction_id, correlation_id, prediction_source,
         ml_prediction, ml_confidence, ai_decision, model_version, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (lrn._new_id(), pid, corr_id, prediction_source,
         ml_prediction, ml_confidence, decision, model_version, _now()),
    )
    conn.commit()
    conn.close()

    return pid


# ── Record blocked trade from Risk Firewall ──

def record_blocked_trade(
    prediction_id: str | None,
    symbol: str,
    direction: str | None,
    intended_entry: float | None,
    intended_sl: float | None,
    intended_tp: float | None,
    intended_quantity: int,
    ai_score: int | None,
    ai_confidence: int | None,
    strategy: str | None,
    blocked_by: str,
    block_reason: str,
    risk_score: int | None = None,
    market_regime: str | None = None,
    correlation_id: str | None = None,
) -> str:
    """Record a trade that was blocked by the Risk Firewall."""
    init_learning_tables()
    conn = _get_db()
    bid = lrn._new_id()
    now = _now()
    conn.execute(
        """INSERT OR IGNORE INTO blocked_trade
        (id, prediction_id, blocked_by, reason, risk_score,
         created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (bid, prediction_id, blocked_by, block_reason, risk_score, now, now),
    )
    conn.commit()
    conn.close()
    return bid


# ── Record trade feedback from execution ──

def record_trade_feedback(
    prediction_id: str,
    entry_price: float,
    exit_price: float | None = None,
    quantity: int = 0,
    direction: str = "BUY",
    entry_slippage: float | None = None,
    exit_slippage: float | None = None,
    commission: float = 0.0,
    taxes: float = 0.0,
    brokerage: float = 0.0,
    gross_pnl: float | None = None,
    net_pnl: float | None = None,
    planned_risk: float | None = None,
    actual_risk: float | None = None,
    planned_rr: float | None = None,
    actual_rr: float | None = None,
    holding_duration: int | None = None,
    exit_reason: str | None = None,
    risk_firewall_result: dict | None = None,
) -> str:
    """Record trade feedback for an executed prediction."""
    init_learning_tables()
    conn = _get_db()
    tfid = lrn._new_id()
    now = _now()
    conn.execute(
        """INSERT OR IGNORE INTO trade_feedback
        (id, prediction_id, entry_slippage, exit_slippage,
         commission, taxes, brokerage, gross_pnl, net_pnl,
         planned_risk, actual_risk, planned_rr, actual_rr,
         holding_duration, exit_reason,
         risk_firewall_result, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (tfid, prediction_id, entry_slippage, exit_slippage,
         commission, taxes, brokerage, gross_pnl, net_pnl,
         planned_risk, actual_risk, planned_rr, actual_rr,
         holding_duration, exit_reason,
         json.dumps(risk_firewall_result) if risk_firewall_result else None,
         now, now),
    )
    conn.commit()
    conn.close()
    return tfid


# ── Update outcome from execution result ──

def update_outcome_from_execution(
    prediction_id: str,
    actual_return: float,
    target_hit: bool = False,
    stop_loss_hit: bool = False,
    actual_direction: str | None = None,
    max_favorable: float | None = None,
    max_adverse: float | None = None,
    error_category: str | None = None,
    error_reason: str | None = None,
) -> str:
    """Update prediction outcome based on execution result."""
    lrn.record_outcome(
        prediction_id=prediction_id,
        outcome_eod="WIN" if actual_return > 0 else "LOSS",
        target_hit=target_hit,
        stop_loss_hit=stop_loss_hit,
        actual_direction=actual_direction,
        actual_return=actual_return,
        max_favorable=max_favorable,
        max_adverse=max_adverse,
        error_category=error_category,
        error_reason=error_reason,
    )
    lrn.update_calibration()
    return prediction_id


# ── Record a recommendation ──

def create_learning_recommendation(
    title: str,
    finding: str,
    evidence: str,
    sample_count: int,
    confidence: float,
    expected_impact: str,
    risk: str,
    recommendation: str,
    category: str,
    action: str | None = None,
) -> str:
    """Create a new learning recommendation."""
    return lrn.create_recommendation(
        title=title,
        finding=finding,
        evidence=evidence,
        sample_count=sample_count,
        confidence=confidence,
        expected_impact=expected_impact,
        risk=risk,
        recommendation=recommendation,
        category=category,
        action=action,
    )


# ── AI vs ML comparison ──

def get_ai_vs_ml_comparison() -> dict[str, Any]:
    """Compare AI predictions vs ML predictions vs actual outcomes."""
    conn = _get_db()
    rows = conn.execute("""
        SELECT pj.id, pj.direction, pj.score, pj.confidence,
               lm.ml_prediction, lm.ml_confidence,
               po.actual_direction, po.actual_return,
               po.error_category
        FROM prediction_journal pj
        LEFT JOIN learning_metadata lm ON lm.prediction_id = pj.id
        LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id
        WHERE lm.ml_prediction IS NOT NULL
        AND po.actual_return IS NOT NULL
    """).fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    total = len(results)
    if total == 0:
        return {"total": 0, "ai_accuracy": 0, "ml_accuracy": 0, "agreement_rate": 0, "samples": []}

    ai_correct = 0
    ml_correct = 0
    both_correct = 0
    both_wrong = 0
    ai_only = 0
    ml_only = 0

    for r in results:
        actual_up = (r["actual_return"] or 0) > 0
        ai_up = r["direction"] == "BUY"
        ml_up = r["ml_prediction"] == "BUY"

        ai_ok = ai_up == actual_up
        ml_ok = ml_up == actual_up

        if ai_ok:
            ai_correct += 1
        if ml_ok:
            ml_correct += 1
        if ai_ok and ml_ok:
            both_correct += 1
        elif not ai_ok and not ml_ok:
            both_wrong += 1
        elif ai_ok and not ml_ok:
            ai_only += 1
        elif ml_ok and not ai_ok:
            ml_only += 1

    return {
        "total": total,
        "ai_accuracy": round(ai_correct / total * 100, 1) if total > 0 else 0,
        "ml_accuracy": round(ml_correct / total * 100, 1) if total > 0 else 0,
        "agreement_rate": round((total - (ai_only + ml_only)) / total * 100, 1) if total > 0 else 0,
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "ai_correct_ml_wrong": ai_only,
        "ai_wrong_ml_correct": ml_only,
        "sample_size": total,
    }


# ── Data quality check ──

def check_data_quality() -> dict[str, Any]:
    """Check data integrity across learning tables."""
    conn = _get_db()
    pj_count = conn.execute("SELECT COUNT(*) as c FROM prediction_journal").fetchone()
    po_count = conn.execute("SELECT COUNT(*) as c FROM prediction_outcome").fetchone()
    tf_count = conn.execute("SELECT COUNT(*) as c FROM trade_feedback").fetchone()
    bt_count = conn.execute("SELECT COUNT(*) as c FROM blocked_trade").fetchone()
    orphan_po = conn.execute("""
        SELECT COUNT(*) as c FROM prediction_outcome po
        LEFT JOIN prediction_journal pj ON po.prediction_id = pj.id WHERE pj.id IS NULL
    """).fetchone()
    orphan_tf = conn.execute("""
        SELECT COUNT(*) as c FROM trade_feedback tf
        LEFT JOIN prediction_journal pj ON tf.prediction_id = pj.id WHERE pj.id IS NULL
    """).fetchone()
    dup_outcomes = conn.execute(
        "SELECT prediction_id, COUNT(*) as c FROM prediction_outcome GROUP BY prediction_id HAVING c > 1"
    ).fetchall()
    conn.close()

    return {
        "prediction_journal_count": dict(pj_count)["c"],
        "outcome_count": dict(po_count)["c"],
        "trade_feedback_count": dict(tf_count)["c"],
        "blocked_trade_count": dict(bt_count)["c"],
        "orphan_outcomes": dict(orphan_po)["c"],
        "orphan_feedback": dict(orphan_tf)["c"],
        "duplicate_outcomes": len(dup_outcomes),
        "data_completeness_pct": _calc_completeness(po_count, pj_count),
        "has_issues": dict(orphan_po)["c"] > 0 or dict(orphan_tf)["c"] > 0 or len(dup_outcomes) > 0,
    }


def _calc_completeness(po: Any, pj: Any) -> float:
    pj_c = dict(pj)["c"] if pj else 0
    po_c = dict(po)["c"] if po else 0
    if pj_c == 0:
        return 100.0
    return round(po_c / pj_c * 100, 1)

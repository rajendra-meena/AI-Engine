"""
AI Learning Engine — Prediction Journal, Outcome Tracking,
Trade Feedback, Blocked Trade Analysis, and Learning Metric Computation.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from learning.database import _get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"lrn_{uuid.uuid4().hex[:12]}"


# ── Prediction Journal ──


def record_prediction(
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
    news_context: dict | None = None,
    market_context: dict | None = None,
    regime: str | None = None,
    user_id: str = "",
) -> str:
    """Record an AI prediction in the journal. Returns the prediction ID."""
    pid = _new_id()
    now = _now()
    conn = _get_db()
    conn.execute(
        """INSERT INTO prediction_journal
        (id, symbol, exchange, interval, timestamp, decision, direction, score, confidence,
         risk_score, risk_level, entry_price, stop_loss, target, risk_reward,
         strategy_id, model_id, market_regime, trend, market_phase,
         institutional_bias, mtf_alignment, volatility, momentum,
         feature_snapshot, indicator_snapshot, pattern_snapshot,
         structure_snapshot, sr_snapshot, news_context, market_context,
         regime, user_id, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid, symbol, exchange, interval, now, decision, direction, score, confidence,
            risk_score, risk_level, entry_price, stop_loss, target, risk_reward,
            strategy_id, model_id, market_regime, trend, market_phase,
            institutional_bias, mtf_alignment, volatility, momentum,
            json.dumps(feature_snapshot) if feature_snapshot else None,
            json.dumps(indicator_snapshot) if indicator_snapshot else None,
            json.dumps(pattern_snapshot) if pattern_snapshot else None,
            json.dumps(structure_snapshot) if structure_snapshot else None,
            json.dumps(sr_snapshot) if sr_snapshot else None,
            json.dumps(news_context) if news_context else None,
            json.dumps(market_context) if market_context else None,
            regime, user_id, now, now,
        ),
    )
    conn.commit()
    conn.close()
    return pid


def record_outcome(
    prediction_id: str,
    outcome_5m: str | None = None,
    outcome_15m: str | None = None,
    outcome_30m: str | None = None,
    outcome_60m: str | None = None,
    outcome_session: str | None = None,
    outcome_eod: str | None = None,
    max_favorable: float | None = None,
    max_adverse: float | None = None,
    target_hit: bool | None = None,
    stop_loss_hit: bool | None = None,
    time_exit: bool | None = None,
    manual_exit: bool | None = None,
    expired: bool | None = None,
    actual_direction: str | None = None,
    actual_return: float | None = None,
    maximum_return: float | None = None,
    maximum_drawdown: float | None = None,
    error_category: str | None = None,
    error_reason: str | None = None,
) -> str:
    """Record outcome for a prediction."""
    oid = _new_id()
    now = _now()
    conn = _get_db()
    conn.execute(
        """INSERT INTO prediction_outcome
        (id, prediction_id, outcome_5m, outcome_15m, outcome_30m, outcome_60m,
         outcome_session, outcome_eod,
         max_favorable_excursion, max_adverse_excursion,
         target_hit, stop_loss_hit, time_exit, manual_exit, expired,
         actual_direction, actual_return, maximum_return, maximum_drawdown,
         error_category, error_reason, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            oid, prediction_id, outcome_5m, outcome_15m, outcome_30m, outcome_60m,
            outcome_session, outcome_eod,
            max_favorable, max_adverse,
            1 if target_hit else 0 if target_hit is not None else None,
            1 if stop_loss_hit else 0 if stop_loss_hit is not None else None,
            1 if time_exit else 0, 1 if manual_exit else 0, 1 if expired else 0,
            actual_direction, actual_return, maximum_return, maximum_drawdown,
            error_category, error_reason, now, now,
        ),
    )
    conn.commit()
    conn.close()
    return oid


def get_predictions(
    limit: int = 100,
    offset: int = 0,
    symbol: str | None = None,
    regime: str | None = None,
) -> list[dict[str, Any]]:
    """Get prediction journal entries with outcomes."""
    conn = _get_db()
    where = []
    params: list[Any] = []
    if symbol:
        where.append("pj.symbol = ?")
        params.append(symbol)
    if regime:
        where.append("pj.regime = ?")
        params.append(regime)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"""SELECT pj.*, po.outcome_15m, po.outcome_eod, po.actual_return,
                   po.error_category, po.target_hit, po.stop_loss_hit,
                   po.max_favorable_excursion, po.max_adverse_excursion,
                   tf.gross_pnl, tf.net_pnl, tf.actual_rr,
                   bt.blocked_by, bt.would_have_been_profitable
            FROM prediction_journal pj
            LEFT JOIN prediction_outcome po ON po.prediction_id = pj.id
            LEFT JOIN trade_feedback tf ON tf.prediction_id = pj.id
            LEFT JOIN blocked_trade bt ON bt.prediction_id = pj.id
            {w}
            ORDER BY pj.timestamp DESC LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_performance_metrics() -> dict[str, Any]:
    """Compute aggregate prediction performance metrics."""
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM prediction_journal").fetchone()
    evaluated = conn.execute(
        "SELECT COUNT(*) as c FROM prediction_journal pj INNER JOIN prediction_outcome po ON po.prediction_id = pj.id"
    ).fetchone()
    correct = conn.execute(
        """SELECT COUNT(*) as c FROM prediction_journal pj
           INNER JOIN prediction_outcome po ON po.prediction_id = pj.id
           WHERE po.actual_return IS NOT NULL AND (
               (pj.direction = 'BUY' AND po.actual_return > 0) OR
               (pj.direction = 'SELL' AND po.actual_return < 0)
           )"""
    ).fetchone()
    wrong = conn.execute(
        """SELECT COUNT(*) as c FROM prediction_journal pj
           INNER JOIN prediction_outcome po ON po.prediction_id = pj.id
           WHERE po.actual_return IS NOT NULL AND (
               (pj.direction = 'BUY' AND po.actual_return <= 0) OR
               (pj.direction = 'SELL' AND po.actual_return >= 0)
           )"""
    ).fetchone()

    evaluated_c = dict(evaluated)["c"]
    correct_c = dict(correct)["c"]

    # Average confidence
    avg_conf = conn.execute(
        "SELECT AVG(confidence) as c FROM prediction_journal"
    ).fetchone()
    # Average return
    avg_return = conn.execute(
        "SELECT AVG(actual_return) as c FROM prediction_outcome WHERE actual_return IS NOT NULL"
    ).fetchone()
    # Win rate from trade feedback
    win_rate = conn.execute(
        "SELECT COUNT(*) as c FROM trade_feedback WHERE gross_pnl > 0"
    ).fetchone()
    total_trades = conn.execute(
        "SELECT COUNT(*) as c FROM trade_feedback"
    ).fetchone()
    # Blocked trades
    blocked = conn.execute("SELECT COUNT(*) as c FROM blocked_trade").fetchone()

    conn.close()
    return {
        "total_predictions": dict(total)["c"],
        "evaluated_predictions": dict(evaluated)["c"],
        "correct_predictions": dict(correct)["c"],
        "incorrect_predictions": dict(wrong)["c"],
        "accuracy": round(correct_c / evaluated_c * 100, 1) if evaluated_c > 0 else 0,
        "average_confidence": round(dict(avg_conf)["c"] or 0, 1),
        "average_return": round(dict(avg_return)["c"] or 0, 2),
        "win_rate": round(dict(win_rate)["c"] / max(1, dict(total_trades)["c"]) * 100, 1),
        "total_trades": dict(total_trades)["c"],
        "blocked_trades": dict(blocked)["c"],
    }


def get_calibration_data() -> list[dict[str, Any]]:
    """Get confidence calibration buckets."""
    conn = _get_db()
    rows = conn.execute("SELECT * FROM calibration_bucket ORDER BY bucket_min").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_calibration():
    """Recalculate calibration buckets from prediction data."""
    conn = _get_db()
    buckets = [
        (0, 10), (10, 20), (20, 30), (30, 40), (40, 50),
        (50, 60), (60, 70), (70, 80), (80, 90), (90, 100),
    ]
    now = _now()
    for bmin, bmax in buckets:
        bucket_key = f"{bmin}-{bmax}"
        rows = conn.execute(
            """SELECT pj.confidence, po.actual_return FROM prediction_journal pj
               INNER JOIN prediction_outcome po ON po.prediction_id = pj.id
               WHERE pj.confidence >= ? AND pj.confidence < ? AND po.actual_return IS NOT NULL""",
            (bmin, bmax),
        ).fetchall()
        total = len(rows)
        if total == 0:
            continue
        correct = sum(
            1 for r in rows
            if (r["actual_return"] or 0) > 0
        )
        avg_conf = sum(r["confidence"] for r in rows if r["confidence"]) / total if total > 0 else 0
        accuracy = (correct / total * 100) if total > 0 else 0

        conn.execute(
            """INSERT INTO calibration_bucket
               (id, bucket, bucket_min, bucket_max, total_predictions, correct_count,
                actual_accuracy, average_confidence, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(bucket) DO UPDATE SET
               total_predictions = excluded.total_predictions,
               correct_count = excluded.correct_count,
               actual_accuracy = excluded.actual_accuracy,
               average_confidence = excluded.average_confidence,
               updated_at = excluded.updated_at""",
            (_new_id(), bucket_key, bmin, bmax, total, correct, accuracy, avg_conf, now, now),
        )
    conn.commit()
    conn.close()


def get_regime_performance() -> list[dict[str, Any]]:
    """Get performance broken down by market regime."""
    conn = _get_db()
    rows = conn.execute(
        """SELECT pj.regime,
                  COUNT(*) as total_predictions,
                  AVG(po.actual_return) as avg_return,
                  SUM(CASE WHEN po.actual_return > 0 THEN 1 ELSE 0 END) as wins,
                  SUM(CASE WHEN po.actual_return < 0 THEN 1 ELSE 0 END) as losses
           FROM prediction_journal pj
           INNER JOIN prediction_outcome po ON po.prediction_id = pj.id
           WHERE pj.regime IS NOT NULL AND po.actual_return IS NOT NULL
           GROUP BY pj.regime"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_error_analysis() -> list[dict[str, Any]]:
    """Get error category distribution."""
    conn = _get_db()
    rows = conn.execute(
        """SELECT po.error_category, COUNT(*) as count,
                  AVG(ABS(po.actual_return)) as avg_loss,
                  (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM prediction_outcome WHERE error_category IS NOT NULL)) as pct
           FROM prediction_outcome po
           WHERE po.error_category IS NOT NULL
           GROUP BY po.error_category ORDER BY count DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_blocked_trade_analysis() -> dict[str, Any]:
    """Analyze blocked trades to evaluate risk firewall strictness."""
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM blocked_trade").fetchone()
    would_be_profitable = conn.execute(
        "SELECT COUNT(*) as c FROM blocked_trade WHERE would_have_been_profitable = 1"
    ).fetchone()
    would_be_loss = conn.execute(
        "SELECT COUNT(*) as c FROM blocked_trade WHERE would_have_been_profitable = 0"
    ).fetchone()
    by_rule = conn.execute(
        "SELECT blocked_by, COUNT(*) as c FROM blocked_trade GROUP BY blocked_by ORDER BY c DESC"
    ).fetchall()
    conn.close()
    t = dict(total)["c"]
    return {
        "total_blocked": t,
        "would_have_been_profitable": dict(would_be_profitable)["c"],
        "would_have_been_loss": dict(would_be_loss)["c"],
        "correctly_blocked_pct": round(dict(would_be_loss)["c"] / t * 100, 1) if t > 0 else 0,
        "missed_opportunities_pct": round(dict(would_be_profitable)["c"] / t * 100, 1) if t > 0 else 0,
        "by_rule": [dict(r) for r in by_rule],
    }


def get_recommendations(status: str | None = None) -> list[dict[str, Any]]:
    """Get learning recommendations, optionally filtered by status."""
    conn = _get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM learning_recommendation WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM learning_recommendation ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_recommendation(
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
    rid = _new_id()
    now = _now()
    conn = _get_db()
    conn.execute(
        """INSERT INTO learning_recommendation
        (id, title, finding, evidence, sample_count, confidence,
         expected_impact, risk, recommendation, action, category,
         status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,'NEW',?,?)""",
        (rid, title, finding, evidence, sample_count, confidence,
         expected_impact, risk, recommendation, action, category, now, now),
    )
    conn.commit()
    conn.close()
    return rid


def update_recommendation_status(
    rec_id: str,
    status: str,
    rejection_reason: str | None = None,
) -> bool:
    """Approve, reject, or update a recommendation status."""
    conn = _get_db()
    now = _now()
    fields: dict[str, Any] = {"status": status, "updated_at": now}
    if status == "APPROVED":
        fields["approved_at"] = now
    elif status == "REJECTED":
        fields["rejected_at"] = now
        fields["rejection_reason"] = rejection_reason
    elif status == "IMPLEMENTED":
        fields["implemented_at"] = now

    conn.execute(
        f"UPDATE learning_recommendation SET {', '.join(f'{k}=?' for k in fields)} WHERE id=?",
        tuple(fields.values()) + (rec_id,),
    )
    conn.commit()
    conn.close()
    return True

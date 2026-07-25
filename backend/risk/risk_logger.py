"""
Institutional Risk Firewall — Risk Logger

Logs every trade validation, rejection, and risk event to the database.
Provides query methods for audit trails and analytics.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.settings import DB_PATH


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_risk_tables():
    """Create risk-related database tables."""
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS risk_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            symbol          TEXT,
            side            TEXT,
            quantity        INTEGER,
            price           REAL,
            ai_score        REAL,
            ai_confidence   REAL,
            risk_score      REAL,
            risk_grade      TEXT,
            status          TEXT NOT NULL,
            reason          TEXT,
            recommendation  TEXT,
            strategy        TEXT,
            user_id         TEXT,
            broker          TEXT,
            details         TEXT,
            created_at      TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS risk_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            event_type      TEXT NOT NULL,
            severity        TEXT NOT NULL,
            title           TEXT NOT NULL,
            message         TEXT,
            metric_name     TEXT,
            metric_value    REAL,
            threshold       REAL,
            resolved        INTEGER DEFAULT 0,
            resolved_at     TEXT,
            created_at      TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emergency_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            action          TEXT NOT NULL,
            initiated_by    TEXT,
            reason          TEXT,
            status          TEXT NOT NULL DEFAULT 'executed',
            details         TEXT,
            created_at      TEXT NOT NULL
        )
    """)
    # Index for fast lookups
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_risk_logs_timestamp ON risk_logs(timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_risk_logs_event_type ON risk_logs(event_type)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_risk_events_timestamp ON risk_events(timestamp)
    """)
    conn.commit()
    conn.close()


class RiskLogger:
    """Logs all risk-related events to the database."""

    @staticmethod
    def log_validation(
        symbol: str,
        side: str | None,
        quantity: int | None,
        status: str,
        reason: str | None,
        risk_score: float | None = None,
        risk_grade: str | None = None,
        ai_score: float | None = None,
        ai_confidence: float | None = None,
        recommendation: str | None = None,
        strategy: str = "manual",
        user_id: str = "",
        broker: str = "zerodha",
        details: dict[str, Any] | None = None,
        price: float | None = None,
    ):
        """Log a trade validation event."""
        now = datetime.now(timezone.utc).isoformat()
        conn = _get_db()
        conn.execute(
            """
            INSERT INTO risk_logs
                (timestamp, event_type, symbol, side, quantity, price,
                 ai_score, ai_confidence, risk_score, risk_grade,
                 status, reason, recommendation, strategy, user_id, broker,
                 details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                "trade_validation",
                symbol,
                side,
                quantity,
                price,
                ai_score,
                ai_confidence,
                risk_score,
                risk_grade,
                status,
                reason,
                recommendation,
                strategy,
                user_id,
                broker,
                json.dumps(details) if details else None,
                now,
            ),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def log_risk_event(
        event_type: str,
        severity: str,
        title: str,
        message: str | None = None,
        metric_name: str | None = None,
        metric_value: float | None = None,
        threshold: float | None = None,
    ):
        """Log a risk event (limit breach, warning, etc.)."""
        now = datetime.now(timezone.utc).isoformat()
        conn = _get_db()
        conn.execute(
            """
            INSERT INTO risk_events
                (timestamp, event_type, severity, title, message,
                 metric_name, metric_value, threshold, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, event_type, severity, title, message, metric_name, metric_value, threshold, now),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def log_emergency(
        action: str,
        initiated_by: str = "system",
        reason: str = "",
        details: dict[str, Any] | None = None,
    ):
        """Log an emergency action."""
        now = datetime.now(timezone.utc).isoformat()
        conn = _get_db()
        conn.execute(
            """
            INSERT INTO emergency_events
                (timestamp, action, initiated_by, reason, status, details, created_at)
            VALUES (?, ?, ?, ?, 'executed', ?, ?)
            """,
            (now, action, initiated_by, reason, json.dumps(details) if details else None, now),
        )
        conn.commit()
        conn.close()

    # ── Queries ──

    @staticmethod
    def get_recent_logs(limit: int = 100) -> list[dict[str, Any]]:
        """Get recent risk logs."""
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM risk_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
        """Get recent risk events."""
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM risk_events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_emergency_log(limit: int = 50) -> list[dict[str, Any]]:
        """Get emergency action log."""
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM emergency_events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_validation_stats() -> dict[str, Any]:
        """Get aggregate validation statistics."""
        conn = _get_db()
        total = conn.execute("SELECT COUNT(*) as c FROM risk_logs").fetchone()
        passed = conn.execute(
            "SELECT COUNT(*) as c FROM risk_logs WHERE status IN ('pass','warn')"
        ).fetchone()
        rejected = conn.execute(
            "SELECT COUNT(*) as c FROM risk_logs WHERE status IN ('fail','block')"
        ).fetchone()
        by_reason = conn.execute(
            "SELECT reason, COUNT(*) as c FROM risk_logs "
            "WHERE status IN ('fail','block') AND reason IS NOT NULL "
            "GROUP BY reason ORDER BY c DESC LIMIT 10"
        ).fetchall()
        conn.close()
        return {
            "total": dict(total)["c"],
            "passed": dict(passed)["c"],
            "rejected": dict(rejected)["c"],
            "top_rejection_reasons": [dict(r) for r in by_reason],
        }

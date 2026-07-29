"""
Paper Trading DB — CRUD operations for paper-trading persistence.

All paper positions, trades, events, and attempts are persisted to SQLite
using the schema defined in paper_trading_schema.py.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from core.settings import DB_PATH
from utils.logger import log_info, log_warn, log_error


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Helpers ──


def _serialize(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return str(val)


def _deserialize(val: str | None) -> Any:
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


# ── Paper Position CRUD ──


def insert_position(pos: dict) -> bool:
    """Persist an open paper position."""
    try:
        conn = _get_db()
        conn.execute("""
            INSERT OR REPLACE INTO paper_positions (
                trade_id, status, execution_type, symbol, execution_symbol,
                underlying_symbol, direction, quantity, entry_price,
                current_premium, stop_loss, target, premium_entry,
                premium_current, premium_stop_loss, premium_target,
                lot_size, lots, option_type, strike, expiry, exchange,
                instrument_token, premium_source, premium_data_status,
                last_premium_tick_at, underlying_entry, underlying_current,
                risk_reward, ai_confidence, opportunity_score, trade_grade,
                decision_id, analysis_cycle_id, strategy_version,
                premium_instrument_token, created_at, updated_at,
                source_provenance, settings_snapshot, risk_snapshot,
                test_origin, recovery_info
            ) VALUES (
                :trade_id, :status, :execution_type, :symbol, :execution_symbol,
                :underlying_symbol, :direction, :quantity, :entry_price,
                :current_premium, :stop_loss, :target, :premium_entry,
                :premium_current, :premium_stop_loss, :premium_target,
                :lot_size, :lots, :option_type, :strike, :expiry, :exchange,
                :instrument_token, :premium_source, :premium_data_status,
                :last_premium_tick_at, :underlying_entry, :underlying_current,
                :risk_reward, :ai_confidence, :opportunity_score, :trade_grade,
                :decision_id, :analysis_cycle_id, :strategy_version,
                :premium_instrument_token, :created_at, :updated_at,
                :source_provenance, :settings_snapshot, :risk_snapshot,
                :test_origin, :recovery_info
            )
        """, {
            "trade_id": pos.get("trade_id", ""),
            "status": pos.get("status", "OPEN"),
            "execution_type": pos.get("execution_type", "option_buying"),
            "symbol": pos.get("symbol", ""),
            "execution_symbol": pos.get("execution_symbol", ""),
            "underlying_symbol": pos.get("underlying_symbol", ""),
            "direction": pos.get("direction", "LONG"),
            "quantity": pos.get("quantity", 0),
            "entry_price": pos.get("entry_price", 0.0),
            "current_premium": pos.get("current_premium", 0.0),
            "stop_loss": pos.get("stop_loss"),
            "target": pos.get("target"),
            "premium_entry": pos.get("premium_entry"),
            "premium_current": pos.get("premium_current"),
            "premium_stop_loss": pos.get("premium_stop_loss"),
            "premium_target": pos.get("premium_target"),
            "lot_size": pos.get("lot_size"),
            "lots": pos.get("lots"),
            "option_type": pos.get("option_type"),
            "strike": pos.get("strike"),
            "expiry": pos.get("expiry"),
            "exchange": pos.get("exchange", "NSE"),
            "instrument_token": pos.get("instrument_token", 0),
            "premium_source": pos.get("premium_source", ""),
            "premium_data_status": pos.get("premium_data_status", "WAITING_FOR_FIRST_TICK"),
            "last_premium_tick_at": pos.get("last_premium_tick_at"),
            "underlying_entry": pos.get("underlying_entry"),
            "underlying_current": pos.get("underlying_current"),
            "risk_reward": pos.get("risk_reward"),
            "ai_confidence": pos.get("ai_confidence", 0.0),
            "opportunity_score": pos.get("opportunity_score", 0.0),
            "trade_grade": pos.get("trade_grade", ""),
            "decision_id": pos.get("decision_id", ""),
            "analysis_cycle_id": pos.get("analysis_cycle_id", ""),
            "strategy_version": pos.get("strategy_version", "1.0"),
            "premium_instrument_token": pos.get("premium_instrument_token", 0),
            "created_at": pos.get("created_at", _now()),
            "updated_at": pos.get("updated_at", _now()),
            "source_provenance": pos.get("source_provenance", ""),
            "settings_snapshot": _serialize(pos.get("settings_snapshot")),
            "risk_snapshot": _serialize(pos.get("risk_snapshot")),
            "test_origin": pos.get("test_origin", ""),
            "recovery_info": pos.get("recovery_info"),
        })
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_error("PaperTradingDB: insert_position failed", error=str(e))
        return False


def update_position(trade_id: str, updates: dict) -> bool:
    """Update fields on an existing position."""
    try:
        if not updates:
            return True
        updates["updated_at"] = _now()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [trade_id]
        conn = _get_db()
        conn.execute(f"UPDATE paper_positions SET {set_clause} WHERE trade_id=?", values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_error("PaperTradingDB: update_position failed", trade_id=trade_id, error=str(e))
        return False


def get_open_positions() -> list[dict]:
    """Load all OPEN positions from DB."""
    try:
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM paper_positions WHERE status='OPEN' ORDER BY created_at ASC"
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["settings_snapshot"] = _deserialize(d.get("settings_snapshot"))
            d["risk_snapshot"] = _deserialize(d.get("risk_snapshot"))
            result.append(d)
        return result
    except Exception as e:
        log_error("PaperTradingDB: get_open_positions failed", error=str(e))
        return []


def get_position_by_trade_id(trade_id: str) -> dict | None:
    """Get a position by trade_id."""
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM paper_positions WHERE trade_id=?", (trade_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        d = dict(row)
        d["settings_snapshot"] = _deserialize(d.get("settings_snapshot"))
        d["risk_snapshot"] = _deserialize(d.get("risk_snapshot"))
        return d
    except Exception as e:
        log_error("PaperTradingDB: get_position_by_trade_id failed", trade_id=trade_id, error=str(e))
        return None


def delete_position(trade_id: str) -> bool:
    """Remove an open position record (used when closing)."""
    try:
        conn = _get_db()
        conn.execute("DELETE FROM paper_positions WHERE trade_id=?", (trade_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_error("PaperTradingDB: delete_position failed", trade_id=trade_id, error=str(e))
        return False


# ── Paper Trades (closed positions) CRUD ──


def insert_trade(trade: dict) -> bool:
    """Persist a completed/closed trade."""
    try:
        conn = _get_db()
        conn.execute("""
            INSERT OR REPLACE INTO paper_trades (
                trade_id, status, execution_type, symbol, execution_symbol,
                underlying_symbol, direction, quantity, entry_price,
                exit_premium, premium_entry, premium_exit, premium_stop_loss,
                premium_target, lot_size, lots, option_type, strike, expiry,
                exit_price, realized_pnl, pnl_percent, entry_time, exit_time,
                exit_reason, exit_price_source, emergency_exit_reason,
                duration_seconds, max_favorable, max_adverse, ai_confidence,
                opportunity_score, trade_grade, risk_reward, premium_source,
                exchange, instrument_token, decision_id, analysis_cycle_id,
                source_provenance, closing_timestamp, test_origin
            ) VALUES (
                :trade_id, :status, :execution_type, :symbol, :execution_symbol,
                :underlying_symbol, :direction, :quantity, :entry_price,
                :exit_premium, :premium_entry, :premium_exit, :premium_stop_loss,
                :premium_target, :lot_size, :lots, :option_type, :strike, :expiry,
                :exit_price, :realized_pnl, :pnl_percent, :entry_time, :exit_time,
                :exit_reason, :exit_price_source, :emergency_exit_reason,
                :duration_seconds, :max_favorable, :max_adverse, :ai_confidence,
                :opportunity_score, :trade_grade, :risk_reward, :premium_source,
                :exchange, :instrument_token, :decision_id, :analysis_cycle_id,
                :source_provenance, :closing_timestamp, :test_origin
            )
        """, {
            "trade_id": trade.get("trade_id", ""),
            "status": trade.get("status", "CLOSED"),
            "execution_type": trade.get("execution_type", "option_buying"),
            "symbol": trade.get("symbol", ""),
            "execution_symbol": trade.get("execution_symbol", ""),
            "underlying_symbol": trade.get("underlying_symbol", ""),
            "direction": trade.get("direction", "LONG"),
            "quantity": trade.get("quantity", 0),
            "entry_price": trade.get("entry_price", 0.0),
            "exit_premium": trade.get("exit_premium"),
            "premium_entry": trade.get("premium_entry"),
            "premium_exit": trade.get("premium_exit"),
            "premium_stop_loss": trade.get("premium_stop_loss"),
            "premium_target": trade.get("premium_target"),
            "lot_size": trade.get("lot_size"),
            "lots": trade.get("lots"),
            "option_type": trade.get("option_type"),
            "strike": trade.get("strike"),
            "expiry": trade.get("expiry"),
            "exit_price": trade.get("exit_price"),
            "realized_pnl": trade.get("realized_pnl", 0.0),
            "pnl_percent": trade.get("pnl_percent", 0.0),
            "entry_time": trade.get("entry_time", ""),
            "exit_time": trade.get("exit_time", _now()),
            "exit_reason": trade.get("exit_reason", ""),
            "exit_price_source": trade.get("exit_price_source", ""),
            "emergency_exit_reason": trade.get("emergency_exit_reason", ""),
            "duration_seconds": trade.get("duration_seconds", 0),
            "max_favorable": trade.get("max_favorable"),
            "max_adverse": trade.get("max_adverse"),
            "ai_confidence": trade.get("ai_confidence", 0.0),
            "opportunity_score": trade.get("opportunity_score", 0.0),
            "trade_grade": trade.get("trade_grade", ""),
            "risk_reward": trade.get("risk_reward"),
            "premium_source": trade.get("premium_source", ""),
            "exchange": trade.get("exchange", "NSE"),
            "instrument_token": trade.get("instrument_token", 0),
            "decision_id": trade.get("decision_id", ""),
            "analysis_cycle_id": trade.get("analysis_cycle_id", ""),
            "source_provenance": trade.get("source_provenance", ""),
            "closing_timestamp": trade.get("closing_timestamp", _now()),
            "test_origin": trade.get("test_origin", ""),
        })
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_error("PaperTradingDB: insert_trade failed", error=str(e))
        return False


def get_trades(limit: int = 100, offset: int = 0) -> list[dict]:
    """Get completed trades, newest first."""
    try:
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM paper_trades ORDER BY exit_time DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        log_error("PaperTradingDB: get_trades failed", error=str(e))
        return []


def get_trade_count() -> int:
    """Get total number of completed trades."""
    try:
        conn = _get_db()
        row = conn.execute("SELECT COUNT(*) as cnt FROM paper_trades").fetchone()
        conn.close()
        return row["cnt"] if row else 0
    except Exception as e:
        return 0


# ── Execution Attempts ──


def insert_execution_attempt(attempt: dict) -> bool:
    """Persist a blocked execution attempt."""
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO paper_execution_attempts (
                attempt_id, timestamp, underlying_symbol, direction,
                analysis_cycle_id, stage, block_code, block_reason,
                actual_value, required_value, settings_snapshot,
                risk_snapshot, created_at
            ) VALUES (
                :attempt_id, :timestamp, :underlying_symbol, :direction,
                :analysis_cycle_id, :stage, :block_code, :block_reason,
                :actual_value, :required_value, :settings_snapshot,
                :risk_snapshot, :created_at
            )
        """, {
            "attempt_id": attempt.get("attempt_id", f"ba_{uuid.uuid4().hex[:8]}"),
            "timestamp": attempt.get("timestamp", _now()),
            "underlying_symbol": attempt.get("underlying_symbol", ""),
            "direction": attempt.get("direction", ""),
            "analysis_cycle_id": attempt.get("analysis_cycle_id", ""),
            "stage": attempt.get("stage", ""),
            "block_code": attempt.get("block_code", ""),
            "block_reason": attempt.get("block_reason", ""),
            "actual_value": attempt.get("actual_value", ""),
            "required_value": attempt.get("required_value", ""),
            "settings_snapshot": _serialize(attempt.get("settings_snapshot")),
            "risk_snapshot": _serialize(attempt.get("risk_snapshot")),
            "created_at": _now(),
        })
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_error("PaperTradingDB: insert_execution_attempt failed", error=str(e))
        return False


# ── Position Events ──


def insert_position_event(trade_id: str, event_type: str, details: dict | None = None) -> bool:
    """Record a lifecycle event for a position."""
    try:
        now = _now()
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        conn = _get_db()
        conn.execute("""
            INSERT INTO paper_position_events (
                event_id, trade_id, event_type, timestamp,
                premium, underlying_price, reason, details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, trade_id, event_type, now,
            details.get("premium") if details else None,
            details.get("underlying_price") if details else None,
            details.get("reason", "") if details else "",
            _serialize(details) if details else None,
            now,
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_error("PaperTradingDB: insert_position_event failed", trade_id=trade_id, error=str(e))
        return False


def get_position_events(trade_id: str) -> list[dict]:
    """Get all events for a position."""
    try:
        conn = _get_db()
        rows = conn.execute(
            "SELECT * FROM paper_position_events WHERE trade_id=? ORDER BY timestamp ASC",
            (trade_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        log_error("PaperTradingDB: get_position_events failed", trade_id=trade_id, error=str(e))
        return []


# ── Account Snapshots ──


def record_account_snapshot(account: dict) -> bool:
    """Record a periodic account snapshot."""
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO paper_account_snapshots (
                timestamp, initial_capital, available_cash, used_margin,
                equity, total_unrealized_pnl, total_realized_pnl, total_pnl,
                open_positions_count, closed_trades_count, win_count, loss_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            _now(),
            account.get("initial_capital", 100000.0),
            account.get("available_cash", 100000.0),
            account.get("used_margin", 0.0),
            account.get("equity", 100000.0),
            account.get("total_unrealized_pnl", 0.0),
            account.get("total_realized_pnl", 0.0),
            account.get("total_pnl", 0.0),
            account.get("open_positions", 0),
            account.get("closed_trades", 0),
            account.get("win_count", 0),
            account.get("loss_count", 0),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False


# ── Runtime Mode Audit ──


def record_runtime_audit(previous: str, new_mode: str, source: str = "api") -> bool:
    """Record a runtime mode change."""
    try:
        conn = _get_db()
        conn.execute("""
            INSERT INTO runtime_mode_audit (timestamp, previous_mode, new_mode, source)
            VALUES (?, ?, ?, ?)
        """, (_now(), previous, new_mode, source))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

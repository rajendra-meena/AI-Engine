"""
Shadow Performance Engine — aggregates shadow trade data, computes metrics,
detects degradation, and generates validation reports.
Never executes orders or modifies runtime mode.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from trading.shadow_tracker import ShadowTradeTracker


def _new_id() -> str:
    return f"spv_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SAMPLE_THRESHOLDS = {"insufficient": 30, "low": 50, "moderate": 100, "good": 200}


def _sample_level(count: int) -> str:
    if count < SAMPLE_THRESHOLDS["insufficient"]:
        return "insufficient"
    if count < SAMPLE_THRESHOLDS["low"]:
        return "low"
    if count < SAMPLE_THRESHOLDS["moderate"]:
        return "moderate"
    if count < SAMPLE_THRESHOLDS["good"]:
        return "good"
    return "strong"


@dataclass
class ShadowMetrics:
    """Aggregate shadow performance metrics."""
    total_signals: int = 0
    qualified_signals: int = 0
    risk_approved: int = 0
    risk_blocked: int = 0
    shadow_trades: int = 0
    closed_trades: int = 0
    open_trades: int = 0
    long_trades: int = 0
    short_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    avg_pnl: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_r: float = 0.0
    max_drawdown_pct: float = 0.0
    max_consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    avg_mae: float = 0.0
    avg_mfe: float = 0.0
    avg_holding_minutes: float = 0.0
    target_hit_rate: float = 0.0
    stoploss_hit_rate: float = 0.0
    qualification_rate: float = 0.0
    risk_approval_rate: float = 0.0
    sample_level: str = "insufficient"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_signals": self.total_signals,
            "qualified_signals": self.qualified_signals,
            "risk_approved": self.risk_approved,
            "risk_blocked": self.risk_blocked,
            "shadow_trades": self.shadow_trades,
            "closed_trades": self.closed_trades,
            "open_trades": self.open_trades,
            "long_trades": self.long_trades,
            "short_trades": self.short_trades,
            "wins": self.wins,
            "losses": self.losses,
            "breakeven": self.breakeven,
            "win_rate": round(self.win_rate, 1),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "net_pnl": round(self.net_pnl, 2),
            "avg_pnl": round(self.avg_pnl, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 2),
            "avg_r": round(self.avg_r, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_consecutive_wins": self.max_consecutive_wins,
            "avg_mae": round(self.avg_mae, 2),
            "avg_mfe": round(self.avg_mfe, 2),
            "avg_holding_minutes": round(self.avg_holding_minutes, 1),
            "target_hit_rate": round(self.target_hit_rate, 1),
            "stoploss_hit_rate": round(self.stoploss_hit_rate, 1),
            "qualification_rate": round(self.qualification_rate, 1),
            "risk_approval_rate": round(self.risk_approval_rate, 1),
            "sample_level": self.sample_level,
        }


class ShadowPerformanceEngine:
    """
    Aggregates shadow trade data and computes comprehensive performance metrics.
    Read-only: never executes orders or modifies configuration.
    """

    def __init__(self):
        self._trades: list[dict] = []
        self._signals: list[dict] = []

    def compute_metrics(self, tracker: ShadowTradeTracker) -> ShadowMetrics:
        """Compute full metrics from shadow tracker data."""
        all_trades = tracker.get_all_trades()
        closed = tracker.get_closed_trades()
        open_trades = tracker.get_open_trades()

        m = ShadowMetrics()
        m.shadow_trades = len(all_trades)
        m.closed_trades = len(closed)
        m.open_trades = len(open_trades)
        m.sample_level = _sample_level(m.closed_trades)

        m.long_trades = sum(1 for t in all_trades if t.direction == "LONG")
        m.short_trades = sum(1 for t in all_trades if t.direction == "SHORT")

        if not closed:
            return m

        # Win/loss analysis
        for t in closed:
            pnl = t.realized_pnl
            if pnl > 0:
                m.wins += 1
                m.gross_profit += pnl
                m.largest_win = max(m.largest_win, pnl)
            elif pnl < 0:
                m.losses += 1
                m.gross_loss += abs(pnl)
                m.largest_loss = min(m.largest_loss, pnl)
            else:
                m.breakeven += 1

        total = len(closed)
        m.win_rate = (m.wins / total) * 100 if total > 0 else 0
        m.net_pnl = m.gross_profit - m.gross_loss
        m.avg_pnl = m.net_pnl / total if total > 0 else 0
        m.profit_factor = m.gross_profit / max(m.gross_loss, 0.01)
        m.expectancy = m.net_pnl / total if total > 0 else 0

        # R-multiple
        r_vals = [t.r_multiple for t in closed if t.r_multiple != 0]
        m.avg_r = sum(r_vals) / max(len(r_vals), 1) if r_vals else 0

        # Drawdown
        equity = 0.0
        peak = 0.0
        for t in closed:
            equity += t.realized_pnl
            if equity > peak:
                peak = equity
            dd = (peak - equity) / max(peak, 1) * 100 if peak > 0 else 0
            m.max_drawdown_pct = max(m.max_drawdown_pct, dd)

        # Consecutive wins/losses
        cur_w, cur_l, max_w, max_l = 0, 0, 0, 0
        for t in closed:
            if t.realized_pnl > 0:
                cur_w += 1
                cur_l = 0
                max_w = max(max_w, cur_w)
            else:
                cur_l += 1
                cur_w = 0
                max_l = max(max_l, cur_l)
        m.max_consecutive_wins = max_w
        m.max_consecutive_losses = max_l

        # MAE/MFE
        mae_vals = [t.mae for t in closed if t.mae != 0]
        mfe_vals = [t.mfe for t in closed if t.mfe != 0]
        m.avg_mae = sum(mae_vals) / max(len(mae_vals), 1) if mae_vals else 0
        m.avg_mfe = sum(mfe_vals) / max(len(mfe_vals), 1) if mfe_vals else 0

        # Exit reason rates
        target_hits = sum(1 for t in closed if t.exit_reason == "target")
        sl_hits = sum(1 for t in closed if t.exit_reason == "stop_loss")
        m.target_hit_rate = target_hits / total * 100 if total > 0 else 0
        m.stoploss_hit_rate = sl_hits / total * 100 if total > 0 else 0

        # Funnel rates
        total_sigs = max(m.total_signals, 1)
        m.qualification_rate = m.qualified_signals / total_sigs * 100
        m.risk_approval_rate = m.risk_approved / max(m.qualified_signals, 1) * 100

        return m

    def compute_funnel(self, metrics: ShadowMetrics) -> dict[str, Any]:
        return {
            "total_signals": metrics.total_signals,
            "qualified": metrics.qualified_signals,
            "risk_approved": metrics.risk_approved,
            "risk_blocked": metrics.risk_blocked,
            "shadow_executed": metrics.shadow_trades,
            "closed": metrics.closed_trades,
            "wins": metrics.wins,
            "losses": metrics.losses,
            "qualification_rate": round(metrics.qualification_rate, 1),
            "approval_rate": round(metrics.risk_approval_rate, 1),
        }

    def breakdown_by(self, trades: list, key: str) -> list[dict]:
        groups: dict[str, list] = {}
        for t in trades:
            val = getattr(t, key, "unknown") if hasattr(t, key) else "unknown"
            if val not in groups:
                groups[val] = []
            groups[val].append(t)
        results = []
        for val, ts in sorted(groups.items()):
            wins = sum(1 for t in ts if t.realized_pnl > 0)
            total = len(ts)
            pnl = sum(t.realized_pnl for t in ts)
            results.append({
                key: val,
                "trades": total,
                "wins": wins,
                "win_rate": round(wins / max(total, 1) * 100, 1),
                "net_pnl": round(pnl, 2),
            })
        return results

    def compute_sessions(self, trades: list) -> list[dict]:
        sessions: dict[str, list] = {}
        for t in trades:
            day = (t.entry_timestamp or "")[:10]
            if day not in sessions:
                sessions[day] = []
            sessions[day].append(t)
        results = []
        for day, ts in sorted(sessions.items()):
            pnl = sum(t.realized_pnl for t in ts)
            wins = sum(1 for t in ts if t.realized_pnl > 0)
            results.append({
                "date": day,
                "trades": len(ts),
                "wins": wins,
                "pnl": round(pnl, 2),
                "win_rate": round(wins / max(len(ts), 1) * 100, 1),
            })
        return results

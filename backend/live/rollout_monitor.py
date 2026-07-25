"""Rollout Performance Monitor — monitors during active rollout.

Phase 49: Tracks P&L, win rate, slippage, latency, and safety events.
Detects deterioration against baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time."""
    cumulative_pnl: float = 0.0
    daily_pnl: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_r: float = 0.0
    max_drawdown_pct: float = 0.0
    consecutive_losses: int = 0
    avg_slippage_pct: float = 0.0
    avg_latency_ms: float = 0.0
    rejection_rate: float = 0.0
    order_mismatches: int = 0
    position_mismatches: int = 0
    stale_data_events: int = 0
    emergency_stops: int = 0
    risk_violations: int = 0
    total_trades: int = 0
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cumulative_pnl": round(self.cumulative_pnl, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 2),
            "avg_r": round(self.avg_r, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "consecutive_losses": self.consecutive_losses,
            "avg_slippage_pct": round(self.avg_slippage_pct, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "rejection_rate": round(self.rejection_rate, 2),
            "order_mismatches": self.order_mismatches,
            "position_mismatches": self.position_mismatches,
            "stale_data_events": self.stale_data_events,
            "emergency_stops": self.emergency_stops,
            "risk_violations": self.risk_violations,
            "total_trades": self.total_trades,
            "timestamp": self.timestamp,
        }


class RolloutPerformanceMonitor:
    """
    Monitors performance during an active rollout stage.

    Tracks financial metrics and safety events.
    Detects deterioration by comparing against baseline.
    """

    def __init__(self):
        self._baseline: PerformanceSnapshot | None = None
        self._current: PerformanceSnapshot = PerformanceSnapshot()
        self._snapshots: list[PerformanceSnapshot] = []

    def set_baseline(self, snapshot: PerformanceSnapshot) -> None:
        """Set the baseline performance for comparison."""
        self._baseline = snapshot

    def get_baseline(self) -> PerformanceSnapshot | None:
        return self._baseline

    def snapshot(self) -> PerformanceSnapshot:
        """Take a performance snapshot at the current moment."""
        snap = PerformanceSnapshot(
            cumulative_pnl=self._current.cumulative_pnl,
            daily_pnl=self._current.daily_pnl,
            win_rate=self._current.win_rate,
            profit_factor=self._current.profit_factor,
            expectancy=self._current.expectancy,
            avg_r=self._current.avg_r,
            max_drawdown_pct=self._current.max_drawdown_pct,
            consecutive_losses=self._current.consecutive_losses,
            avg_slippage_pct=self._current.avg_slippage_pct,
            avg_latency_ms=self._current.avg_latency_ms,
            rejection_rate=self._current.rejection_rate,
            order_mismatches=self._current.order_mismatches,
            position_mismatches=self._current.position_mismatches,
            stale_data_events=self._current.stale_data_events,
            emergency_stops=self._current.emergency_stops,
            risk_violations=self._current.risk_violations,
            total_trades=self._current.total_trades,
        )
        self._snapshots.append(snap)
        return snap

    def update_trade(self, pnl: float, won: bool, r_multiple: float = 0.0,
                     slippage_pct: float = 0.0, latency_ms: float = 0.0) -> None:
        """Update metrics after a trade exit."""
        self._current.total_trades += 1
        self._current.cumulative_pnl += pnl
        self._current.daily_pnl += pnl

        if won:
            self._current.win_rate = (
                (self._current.win_rate * (self._current.total_trades - 1)) + 100
            ) / self._current.total_trades
        else:
            self._current.win_rate = (
                (self._current.win_rate * (self._current.total_trades - 1))
            ) / self._current.total_trades
            self._current.consecutive_losses += 1

        if pnl < 0:
            self._current.consecutive_losses += 1
        else:
            self._current.consecutive_losses = 0

        if slippage_pct:
            prev = self._current.avg_slippage_pct * (self._current.total_trades - 1)
            self._current.avg_slippage_pct = (prev + abs(slippage_pct)) / self._current.total_trades

        if latency_ms:
            prev = self._current.avg_latency_ms * (self._current.total_trades - 1)
            self._current.avg_latency_ms = (prev + latency_ms) / self._current.total_trades

        self._current.avg_r = (
            (self._current.avg_r * (self._current.total_trades - 1)) + r_multiple
        ) / self._current.total_trades

    def record_safety_event(self, event_type: str) -> None:
        """Record a safety event."""
        if "order_mismatch" in event_type:
            self._current.order_mismatches += 1
        elif "position_mismatch" in event_type:
            self._current.position_mismatches += 1
        elif "stale_data" in event_type:
            self._current.stale_data_events += 1
        elif "emergency" in event_type or "kill_switch" in event_type:
            self._current.emergency_stops += 1
        elif "risk" in event_type or "risk_violation" in event_type:
            self._current.risk_violations += 1

    def get_current(self) -> PerformanceSnapshot:
        return self._current

    def get_snapshots(self, limit: int = 50) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._snapshots[-limit:]]

    def get_summary(self) -> dict[str, Any]:
        current = self._current
        deterioration = []
        if self._baseline:
            if current.max_drawdown_pct > self._baseline.max_drawdown_pct * 1.5:
                deterioration.append("drawdown_increased")
            if current.avg_slippage_pct > self._baseline.avg_slippage_pct * 2:
                deterioration.append("slippage_increased")
            if current.avg_latency_ms > self._baseline.avg_latency_ms * 2:
                deterioration.append("latency_increased")
            if current.win_rate < self._baseline.win_rate * 0.5 and self._baseline.win_rate > 0:
                deterioration.append("win_rate_decreased")

        return {
            "current": current.to_dict(),
            "baseline": self._baseline.to_dict() if self._baseline else None,
            "deterioration": deterioration,
            "snapshots_taken": len(self._snapshots),
        }

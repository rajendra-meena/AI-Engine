"""
Institutional Risk Firewall — Drawdown Manager

Tracks peak-to-trough drawdown across multiple time windows:
- Session (daily)
- Weekly
- Monthly
- All-time

Provides real-time drawdown checks against configured limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Any


@dataclass
class DrawdownMetrics:
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    session_high: float = 0.0
    session_low: float = 0.0
    session_dd_percent: float = 0.0
    week_high: float = 0.0
    week_low: float = 0.0
    week_dd_percent: float = 0.0
    month_high: float = 0.0
    month_low: float = 0.0
    month_dd_percent: float = 0.0
    all_time_high: float = 0.0
    all_time_dd_percent: float = 0.0
    session_pnl: float = 0.0
    week_pnl: float = 0.0
    month_pnl: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "session_high": round(self.session_high, 2),
            "session_low": round(self.session_low, 2),
            "session_dd_percent": round(self.session_dd_percent, 2),
            "week_high": round(self.week_high, 2),
            "week_low": round(self.week_low, 2),
            "week_dd_percent": round(self.week_dd_percent, 2),
            "month_high": round(self.month_high, 2),
            "month_low": round(self.month_low, 2),
            "month_dd_percent": round(self.month_dd_percent, 2),
            "all_time_high": round(self.all_time_high, 2),
            "all_time_dd_percent": round(self.all_time_dd_percent, 2),
            "session_pnl": round(self.session_pnl, 2),
            "week_pnl": round(self.week_pnl, 2),
            "month_pnl": round(self.month_pnl, 2),
        }


class DrawdownManager:
    """Tracks drawdown across multiple time windows."""

    def __init__(self, initial_capital: float = 100000.0):
        self._initial_capital = initial_capital
        self._all_time_high = initial_capital
        self._session_high = initial_capital
        self._week_high = initial_capital
        self._month_high = initial_capital
        self._session_start_value = initial_capital
        self._week_start_value = initial_capital
        self._month_start_value = initial_capital
        self._last_session_day = date.today()
        self._last_week_number = date.today().isocalendar()[1]
        self._last_month = date.today().month

    def update(self, current_equity: float):
        """Update drawdown metrics with latest equity value."""
        today = date.today()
        week_num = today.isocalendar()[1]
        month = today.month

        # Reset session tracking on new day
        if today != self._last_session_day:
            self._session_high = current_equity
            self._session_start_value = current_equity
            self._last_session_day = today

        # Reset week tracking on new week
        if week_num != self._last_week_number:
            self._week_high = current_equity
            self._week_start_value = current_equity
            self._last_week_number = week_num

        # Reset month tracking on new month
        if month != self._last_month:
            self._month_high = current_equity
            self._month_start_value = current_equity
            self._last_month = month

        # Update highs
        if current_equity > self._session_high:
            self._session_high = current_equity
        if current_equity > self._week_high:
            self._week_high = current_equity
        if current_equity > self._month_high:
            self._month_high = current_equity
        if current_equity > self._all_time_high:
            self._all_time_high = current_equity

    def get_metrics(self) -> DrawdownMetrics:
        """Compute and return current drawdown metrics."""
        current = self._session_high  # Use most recent equity

        # Approximate current equity from session low
        current = self._session_high - (self._session_high - self._session_low)

        return DrawdownMetrics(
            session_high=self._session_high,
            session_low=min(self._session_low, current),
            session_dd_percent=self._calc_dd(self._session_high, current),
            week_high=self._week_high,
            week_low=self._week_high
            - (self._week_high - self._week_start_value),
            week_dd_percent=self._calc_dd(self._week_high, current),
            month_high=self._month_high,
            month_low=self._month_high
            - (self._month_high - self._month_start_value),
            month_dd_percent=self._calc_dd(self._month_high, current),
            all_time_high=self._all_time_high,
            all_time_dd_percent=self._calc_dd(self._all_time_high, current),
            session_pnl=current - self._session_start_value,
            week_pnl=current - self._week_start_value,
            month_pnl=current - self._month_start_value,
        )

    def check_limits(
        self, max_daily_dd: float, max_weekly_dd: float, max_monthly_dd: float
    ) -> dict[str, Any]:
        """Check if any drawdown limit is breached."""
        metrics = self.get_metrics()
        breaches = []

        if metrics.session_dd_percent >= max_daily_dd:
            breaches.append(
                f"Daily drawdown {metrics.session_dd_percent:.1f}% >= {max_daily_dd:.1f}%"
            )
        if metrics.week_dd_percent >= max_weekly_dd:
            breaches.append(
                f"Weekly drawdown {metrics.week_dd_percent:.1f}% >= {max_weekly_dd:.1f}%"
            )
        if metrics.month_dd_percent >= max_monthly_dd:
            breaches.append(
                f"Monthly drawdown {metrics.month_dd_percent:.1f}% >= {max_monthly_dd:.1f}%"
            )

        return {
            "breached": len(breaches) > 0,
            "breaches": breaches,
            "metrics": metrics.to_dict(),
        }

    @staticmethod
    def _calc_dd(high: float, current: float) -> float:
        if high <= 0:
            return 0.0
        return max(0.0, ((high - current) / high) * 100)

    def reset(self):
        """Reset all drawdown tracking."""
        self.__init__(self._initial_capital)

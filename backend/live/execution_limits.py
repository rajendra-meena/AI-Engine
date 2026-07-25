"""Execution Risk Limiter — hard limits enforced server-side for live execution.

Phase 46: The execution layer can only enforce STRICTER limits than RiskEngine.
Never weaker. Must come from configuration with safe defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Hard Default Limits (server-side, cannot be weakened at runtime) ──

DEFAULT_MAX_ORDER_QUANTITY = 100
DEFAULT_MAX_ORDER_NOTIONAL = 500000
DEFAULT_MAX_RISK_PER_TRADE_PCT = 0.5
DEFAULT_MAX_OPEN_POSITIONS = 1
DEFAULT_MAX_DAILY_LOSS_PCT = 1.5
DEFAULT_MAX_DAILY_TRADES = 5
DEFAULT_MAX_CONSECUTIVE_LOSSES = 3
DEFAULT_MAX_ORDERS_PER_MINUTE = 2
DEFAULT_MAX_SLIPPAGE_PCT = 0.5


@dataclass
class LimitsConfig:
    """Execution limit configuration."""
    max_order_quantity: int = DEFAULT_MAX_ORDER_QUANTITY
    max_order_notional: float = DEFAULT_MAX_ORDER_NOTIONAL
    max_risk_per_trade_pct: float = DEFAULT_MAX_RISK_PER_TRADE_PCT
    max_open_positions: int = DEFAULT_MAX_OPEN_POSITIONS
    max_daily_loss_pct: float = DEFAULT_MAX_DAILY_LOSS_PCT
    max_daily_trades: int = DEFAULT_MAX_DAILY_TRADES
    max_consecutive_losses: int = DEFAULT_MAX_CONSECUTIVE_LOSSES
    max_orders_per_minute: int = DEFAULT_MAX_ORDERS_PER_MINUTE
    max_slippage_pct: float = DEFAULT_MAX_SLIPPAGE_PCT

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_order_quantity": self.max_order_quantity,
            "max_order_notional": self.max_order_notional,
            "max_risk_per_trade_pct": self.max_risk_per_trade_pct,
            "max_open_positions": self.max_open_positions,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_daily_trades": self.max_daily_trades,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_orders_per_minute": self.max_orders_per_minute,
            "max_slippage_pct": self.max_slippage_pct,
        }


@dataclass
class LimitCheckResult:
    """Result of a limit check."""
    passed: bool = False
    blockers: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "blockers": self.blockers,
            "checks": self.checks,
            "timestamp": self.timestamp,
        }


class ExecutionRiskLimiter:
    """
    Enforces hard execution limits server-side.

    These limits are SEPARATE from RiskEngine configuration.
    The execution layer can only be STRICTER.
    """

    def __init__(self, config: LimitsConfig | None = None):
        self._config = config or LimitsConfig()
        self._daily_trade_count = 0
        self._daily_loss = 0.0
        self._consecutive_losses = 0
        self._orders_this_minute = 0
        self._minute_start = datetime.now(timezone.utc).timestamp()
        self._open_positions: list[dict[str, Any]] = []
        self._account_balance = 100000.0
        self._audit_log = None

    def set_audit_log(self, audit): self._audit_log = audit

    def update_state(self, daily_trade_count: int = 0, daily_loss: float = 0.0,
                     consecutive_losses: int = 0, open_positions: list | None = None,
                     account_balance: float = 100000.0) -> None:
        """Update current execution state for limit checking."""
        self._daily_trade_count = daily_trade_count
        self._daily_loss = daily_loss
        self._consecutive_losses = consecutive_losses
        self._open_positions = open_positions or []
        self._account_balance = account_balance

    def check(
        self,
        symbol: str = "",
        side: str = "BUY",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
    ) -> LimitCheckResult:
        """Run all limit checks against the current order.

        Returns:
            LimitCheckResult with per-check pass/fail and overall passed.
        """
        result = LimitCheckResult()
        blockers: list[str] = []
        checks: dict[str, bool] = {}

        # 1. Max order quantity
        qty_ok = quantity <= self._config.max_order_quantity
        checks["max_order_quantity"] = qty_ok
        if not qty_ok:
            blockers.append(
                f"max_order_quantity: {quantity} > {self._config.max_order_quantity}"
            )

        # 2. Max order notional
        notional = (price or 0) * quantity
        notional_ok = notional <= self._config.max_order_notional
        checks["max_order_notional"] = notional_ok
        if not notional_ok:
            blockers.append(
                f"max_order_notional: {notional:.0f} > {self._config.max_order_notional:.0f}"
            )

        # 3. Max risk per trade
        risk_per_trade = 0.0
        if price and price > 0 and stop_loss and stop_loss > 0:
            risk_per_unit = abs(price - stop_loss)
            risk_per_trade = risk_per_unit * quantity
            max_risk = self._account_balance * (self._config.max_risk_per_trade_pct / 100)
            risk_ok = risk_per_trade <= max_risk
            checks["max_risk_per_trade"] = risk_ok
            if not risk_ok:
                blockers.append(
                    f"max_risk_per_trade: {risk_per_trade:.0f} > {max_risk:.0f}"
                )
        else:
            checks["max_risk_per_trade"] = False
            blockers.append("cannot_calculate_risk")

        # 4. Max open positions
        positions_ok = len(self._open_positions) < self._config.max_open_positions
        checks["max_open_positions"] = positions_ok
        if not positions_ok:
            blockers.append(
                f"max_open_positions: {len(self._open_positions)} >= {self._config.max_open_positions}"
            )

        # 5. Max daily loss
        max_loss = self._account_balance * (self._config.max_daily_loss_pct / 100)
        loss_ok = self._daily_loss > -max_loss
        checks["max_daily_loss"] = loss_ok
        if not loss_ok:
            blockers.append(
                f"max_daily_loss: {self._daily_loss:.0f} <= {-max_loss:.0f}"
            )

        # 6. Max daily trades
        trades_ok = self._daily_trade_count < self._config.max_daily_trades
        checks["max_daily_trades"] = trades_ok
        if not trades_ok:
            blockers.append(
                f"max_daily_trades: {self._daily_trade_count} >= {self._config.max_daily_trades}"
            )

        # 7. Max consecutive losses
        cons_ok = self._consecutive_losses < self._config.max_consecutive_losses
        checks["max_consecutive_losses"] = cons_ok
        if not cons_ok:
            blockers.append(
                f"max_consecutive_losses: {self._consecutive_losses} >= {self._config.max_consecutive_losses}"
            )

        # 8. Orders per minute rate limit
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts - self._minute_start > 60:
            self._orders_this_minute = 0
            self._minute_start = now_ts
        rate_ok = self._orders_this_minute < self._config.max_orders_per_minute
        checks["max_orders_per_minute"] = rate_ok
        if not rate_ok:
            blockers.append(
                f"max_orders_per_minute: {self._orders_this_minute} >= {self._config.max_orders_per_minute}"
            )

        # 9. Max slippage (informational check)
        checks["max_slippage"] = True

        result.passed = len(blockers) == 0
        result.blockers = blockers
        result.checks = checks
        result.timestamp = _now()
        return result

    def record_trade_executed(self, pnl: float = 0.0) -> None:
        """Update counters after a trade execution."""
        self._daily_trade_count += 1
        self._orders_this_minute += 1
        if pnl < 0:
            self._consecutive_losses += 1
            self._daily_loss += pnl
        else:
            self._consecutive_losses = 0
            self._daily_loss += pnl

    def get_config(self) -> LimitsConfig:
        return self._config

    def get_status(self) -> dict[str, Any]:
        return {
            "limits": self._config.to_dict(),
            "current_state": {
                "daily_trade_count": self._daily_trade_count,
                "daily_loss": round(self._daily_loss, 2),
                "consecutive_losses": self._consecutive_losses,
                "orders_this_minute": self._orders_this_minute,
                "open_positions": len(self._open_positions),
                "account_balance": self._account_balance,
            },
        }

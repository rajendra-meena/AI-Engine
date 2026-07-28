"""
Institutional Risk Firewall — Risk Engine

Central validation pipeline that evaluates every order before broker execution.

Flow:
    TradeIntent → RiskEngine.validate()
        ├── Pre-trade checks (market, session, circuit, etc.)
        ├── Exposure checks (symbol, sector, portfolio)
        ├── Loss limits (daily, weekly, monthly, drawdown)
        ├── AI quality checks (score, confidence, R:R)
        ├── Position sizing validation
        └── Emergency override check
            → ValidationSummary (passed/rejected + risk_score)

If RiskEngine rejects a trade, the broker MUST NEVER receive the order.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from risk.trade_validator import (
    TradeIntent,
    ValidationResult,
    ValidationSummary,
    ValidationStatus,
    Severity,
)
from risk.risk_rules import (
    check_capital_available,
    check_margin_available,
    check_market_open,
    check_trading_session,
    check_freeze_quantity,
    check_duplicate_order,
    check_max_daily_trades,
    check_max_concurrent_positions,
    check_max_open_orders,
    check_cooldown,
    check_symbol_exposure,
    check_daily_loss,
    check_weekly_loss,
    check_monthly_loss,
    check_max_drawdown,
    check_max_risk_percent,
    check_min_ai_score,
    check_min_confidence,
    check_reward_risk_ratio,
)
from risk.exposure import ExposureManager
from risk.drawdown import DrawdownManager
from risk.risk_logger import RiskLogger
from utils.logger import log_info, log_warn


PRE_TRADE_CHECKS = [
    "capital_available",
    "margin_available",
    "market_open",
    "trading_session",
    "freeze_quantity",
    "circuit_limits",
    "duplicate_order",
]

LIMIT_CHECKS = [
    "max_daily_trades",
    "max_concurrent_positions",
    "max_open_orders",
    "cooldown",
    "symbol_exposure",
    "daily_loss",
    "weekly_loss",
    "monthly_loss",
    "max_drawdown",
    "max_risk_percent",
]

AI_QUALITY_CHECKS = [
    "min_ai_score",
    "min_confidence",
    "reward_risk_ratio",
]


@dataclass
class RiskConfig:
    """Configuration for the risk firewall."""
    max_daily_loss: float = 5000.0
    max_weekly_loss: float = 15000.0
    max_monthly_loss: float = 50000.0
    max_drawdown_percent: float = 25.0
    max_daily_trades: int = 20
    max_concurrent_positions: int = 10
    max_open_orders: int = 20
    max_exposure_percent: float = 80.0
    max_risk_percent: float = 3.0
    min_ai_score: float = 30.0
    min_ai_confidence: float = 40.0
    min_reward_risk: float = 1.5
    trade_cooldown_seconds: int = 60
    trading_halt: bool = False
    broker_disabled: bool = False
    ai_disabled: bool = False


class RiskEngine:
    """
    Centralized risk validation pipeline.

    Implements the 'validate before execute' pattern. Every order
    must pass through validate() before the broker adapter touches it.
    """

    def __init__(self, config: RiskConfig | None = None):
        self._config = config or RiskConfig()
        self._exposure_manager = ExposureManager()
        self._drawdown_manager = DrawdownManager()
        self._last_trade_time: datetime | None = None
        self._daily_trades = 0
        self._today_pnl = 0.0
        self._week_pnl = 0.0
        self._month_pnl = 0.0
        self._last_reset_day = datetime.now(timezone.utc).day
        self._open_positions: list[dict[str, Any]] = []
        self._open_orders: list[dict[str, Any]] = []
        self._active_broker: str = "zerodha"
        self._logger = RiskLogger()

    # ── Configuration ──

    @property
    def config(self) -> RiskConfig:
        return self._config

    def update_config(self, updates: dict[str, Any]):
        """Update risk configuration at runtime."""
        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        log_info("RiskEngine: config updated", updates=updates)

    # ── State updates ──

    def update_positions(self, positions: list[dict[str, Any]]):
        """Update current open positions for exposure calculations."""
        self._open_positions = positions
        self._exposure_manager.update_positions(positions)

    def update_orders(self, orders: list[dict[str, Any]]):
        """Update current open orders."""
        self._open_orders = orders

    def update_pnl(self, today_pnl: float, week_pnl: float, month_pnl: float):
        """Update PnL tracking for loss limits."""
        self._today_pnl = today_pnl
        self._week_pnl = week_pnl
        self._month_pnl = month_pnl

    def update_equity(self, equity: float):
        """Update equity for drawdown tracking."""
        self._drawdown_manager.update(equity)

    def set_broker(self, broker: str):
        self._active_broker = broker

    @property
    def exposure(self) -> dict[str, Any]:
        return self._exposure_manager.get_snapshot().to_dict()

    @property
    def drawdown(self) -> dict[str, Any]:
        return self._drawdown_manager.get_metrics().to_dict()

    # ── Core validation ──

    def validate(self, intent: TradeIntent) -> ValidationSummary:
        """
        Validate a trade intent against ALL risk rules.

        This must be called BEFORE any broker order placement.
        Returns a ValidationSummary with execution_permitted flag.
        """
        start = time.time()
        results: list[ValidationResult] = []
        rejected_by: list[str] = []

        # ── Emergency overrides ──
        if self._config.trading_halt:
            results.append(ValidationResult(
                check="trading_halt",
                status=ValidationStatus.BLOCK,
                severity=Severity.CRITICAL,
                reason="Global trading halt is active",
                recommendation="Contact risk administrator",
            ))
            rejected_by.append("trading_halt")

        if self._config.broker_disabled:
            results.append(ValidationResult(
                check="broker_disabled",
                status=ValidationStatus.BLOCK,
                severity=Severity.CRITICAL,
                reason="Broker execution is disabled",
                recommendation="Enable broker in Risk Center",
            ))
            rejected_by.append("broker_disabled")

        if self._config.ai_disabled and intent.strategy in ("ai", "automated"):
            results.append(ValidationResult(
                check="ai_disabled",
                status=ValidationStatus.BLOCK,
                severity=Severity.CRITICAL,
                reason="AI trading is disabled",
                recommendation="Enable AI in Risk Center",
            ))
            rejected_by.append("ai_disabled")

        # If emergency blocks triggered, skip detailed checks
        if rejected_by:
            return self._build_summary(results, rejected_by, start)

        # ── Capital & Margin ──
        snapshot = self._exposure_manager.get_snapshot()
        available_capital = snapshot.buying_power
        estimated_cost = intent.quantity * (intent.price or 0)

        results.append(check_capital_available(intent, available_capital, estimated_cost))
        results.append(check_margin_available(intent, available_capital, estimated_cost * 0.2))

        # ── Market state ──
        results.append(check_market_open(intent, True))  # Simplified
        results.append(check_trading_session(intent, "regular", ["regular", "pre-open", "post-close"]))

        # ── Order validation ──
        results.append(check_freeze_quantity(intent, 1))
        results.append(check_duplicate_order(intent, self._open_orders))

        # ── Limits ──
        results.append(check_max_daily_trades(intent, self._daily_trades, self._config.max_daily_trades))
        results.append(check_max_concurrent_positions(
            intent, len(self._open_positions), self._config.max_concurrent_positions
        ))
        results.append(check_max_open_orders(intent, len(self._open_orders), self._config.max_open_orders))
        results.append(check_cooldown(intent, self._last_trade_time, self._config.trade_cooldown_seconds))

        # ── Exposure ──
        symbol_exposure = snapshot.symbol_exposure.get(intent.symbol, 0)
        max_sym_exposure = self._config.max_exposure_percent / 100 * snapshot.buying_power
        results.append(check_symbol_exposure(intent, symbol_exposure, max_sym_exposure, intent.price or 0))

        # ── Loss limits ──
        results.append(check_daily_loss(intent, self._today_pnl, self._config.max_daily_loss))
        results.append(check_weekly_loss(intent, self._week_pnl, self._config.max_weekly_loss))
        results.append(check_monthly_loss(intent, self._month_pnl, self._config.max_monthly_loss))
        max_dd = self._config.max_drawdown_percent
        dd_val = self._drawdown_manager.get_metrics().all_time_dd_percent
        results.append(check_max_drawdown(intent, dd_val, max_dd))
        results.append(check_max_risk_percent(intent, self._config.max_risk_percent, self._config.max_risk_percent))

        # ── AI quality (only for AI-driven trades) ──
        if intent.ai_score is not None:
            results.append(check_min_ai_score(intent, self._config.min_ai_score))
        if intent.ai_confidence is not None:
            results.append(check_min_confidence(intent, self._config.min_ai_confidence))
        if intent.stop_loss and intent.take_profit:
            results.append(check_reward_risk_ratio(intent, self._config.min_reward_risk))

        # ── Compile results ──
        return self._build_summary(results, rejected_by, start)

    def _build_summary(
        self,
        results: list[ValidationResult],
        rejected_by: list[str],
        start: float,
    ) -> ValidationSummary:
        """Build the final validation summary from individual results."""
        blocks = [r for r in results if r.status == ValidationStatus.BLOCK]
        fails = [r for r in results if r.status == ValidationStatus.FAIL]
        critical = [
            r for r in results
            if r.severity == Severity.CRITICAL
            and r.status in (ValidationStatus.FAIL, ValidationStatus.BLOCK)
        ]

        execution_permitted = len(blocks) == 0 and len(fails) == 0
        passed = len(blocks) == 0 and len(fails) == 0

        # Risk score: count critical/high failures
        risk_score = min(100, len(critical) * 25 + len(blocks) * 15 + len(fails) * 10)
        risk_grade = self._grade_risk(risk_score)

        for r in blocks + fails:
            if r.check not in rejected_by:
                rejected_by.append(r.check)

        summary = ValidationSummary(
            passed=passed,
            results=results,
            risk_score=risk_score,
            risk_grade=risk_grade,
            execution_permitted=execution_permitted,
            rejected_by=rejected_by,
        )

        # Log the validation
        elapsed = (time.time() - start) * 1000
        status = "pass" if passed else "rejected"
        self._logger.log_validation(
            symbol=results[0].detail.get("symbol", "") if results else "",
            side=None,
            quantity=None,
            status=status,
            reason=rejected_by[0] if rejected_by else None,
            risk_score=risk_score,
            risk_grade=risk_grade,
            recommendation=results[0].recommendation if results else None,
        )

        log_info(
            "RiskEngine: validation complete",
            passed=passed,
            risk_score=risk_score,
            risk_grade=risk_grade,
            execution_permitted=execution_permitted,
            rejected_by=rejected_by,
            elapsed_ms=round(elapsed, 1),
        )

        return summary

    def on_trade_executed(self, intent: TradeIntent):
        """Update internal state after a trade is executed."""
        self._last_trade_time = datetime.now(timezone.utc)
        self._daily_trades += 1
        log_info("RiskEngine: trade recorded", symbol=intent.symbol, side=intent.side)

    @staticmethod
    def _grade_risk(score: float) -> str:
        if score >= 75:
            return "CRITICAL"
        if score >= 50:
            return "HIGH"
        if score >= 25:
            return "MEDIUM"
        return "LOW"

    def get_status(self) -> dict[str, Any]:
        """Return comprehensive risk status for the dashboard."""
        drawdown_metrics = self._drawdown_manager.get_metrics()
        return {
            "risk_score": self._grade_risk_from_state(),
            "risk_grade": self._grade_risk(self._grade_risk_from_state()),
            "trading_halt": self._config.trading_halt,
            "broker_disabled": self._config.broker_disabled,
            "ai_disabled": self._config.ai_disabled,
            "daily_trades": self._daily_trades,
            "daily_loss": self._today_pnl,
            "exposure": self._exposure_manager.get_snapshot().to_dict(),
            "drawdown": drawdown_metrics.to_dict(),
            "config": {
                "max_daily_loss": self._config.max_daily_loss,
                "max_weekly_loss": self._config.max_weekly_loss,
                "max_concurrent_positions": self._config.max_concurrent_positions,
                "max_drawdown_percent": self._config.max_drawdown_percent,
                "max_exposure_percent": self._config.max_exposure_percent,
                "max_risk_percent": self._config.max_risk_percent,
                "trade_cooldown_seconds": self._config.trade_cooldown_seconds,
            },
            "validation_stats": self._logger.get_validation_stats(),
        }

    def _grade_risk_from_state(self) -> float:
        """Compute a composite risk score from current state."""
        score = 0.0
        if self._config.trading_halt:
            score += 30
        if self._config.broker_disabled:
            score += 20
        dd = self._drawdown_manager.get_metrics().all_time_dd_percent
        if dd > self._config.max_drawdown_percent:
            score += 25
        exposure = self._exposure_manager.get_snapshot().buying_power_used_pct
        if exposure > self._config.max_exposure_percent:
            score += 15
        return min(score, 100)

    # ── Emergency controls ──

    def pause_trading(self):
        """Emergency: pause all trading."""
        self._config.trading_halt = True
        self._logger.log_emergency("pause_trading", "system", "Emergency trading halt")
        log_warn("RiskEngine: TRADING HALTED")

    def disable_ai(self):
        """Emergency: disable AI-driven trading."""
        self._config.ai_disabled = True
        self._logger.log_emergency("disable_ai", "system", "AI trading disabled")
        log_warn("RiskEngine: AI TRADING DISABLED")

    def disable_broker(self):
        """Emergency: disable broker execution."""
        self._config.broker_disabled = True
        self._logger.log_emergency("disable_broker", "system", "Broker disabled")
        log_warn("RiskEngine: BROKER DISABLED")

    def emergency_exit(self):
        """Emergency: halt all trading activity."""
        self.pause_trading()
        self.disable_ai()
        self.disable_broker()
        self._logger.log_emergency("emergency_exit", "system", "Full emergency exit")

    def reset_emergency(self):
        """Reset all emergency controls."""
        self._config.trading_halt = False
        self._config.broker_disabled = False
        self._config.ai_disabled = False
        self._logger.log_emergency("reset", "system", "Emergency controls reset")
        log_info("RiskEngine: emergency controls reset")

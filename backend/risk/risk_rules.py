"""
Institutional Risk Firewall — Risk Rules

All pre-trade validation rules as independent, testable functions.
Each rule takes a TradeIntent + context and returns a ValidationResult.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from risk.trade_validator import (
    TradeIntent,
    ValidationResult,
    ValidationStatus,
    Severity,
)

# ── Capital & Margin ──


def check_capital_available(
    intent: TradeIntent,
    available_capital: float,
    estimated_cost: float,
) -> ValidationResult:
    """Ensure sufficient capital is available for the trade."""
    if estimated_cost <= 0:
        return ValidationResult(
            check="capital_available",
            status=ValidationStatus.PASS,
            detail={"available": available_capital, "required": estimated_cost},
        )
    if estimated_cost > available_capital:
        return ValidationResult(
            check="capital_available",
            status=ValidationStatus.FAIL,
            severity=Severity.CRITICAL,
            reason=f"Estimated cost {estimated_cost:.2f} exceeds available capital {available_capital:.2f}",
            recommendation="Reduce quantity or increase capital allocation",
            detail={
                "available": available_capital,
                "required": estimated_cost,
                "shortfall": estimated_cost - available_capital,
            },
        )
    return ValidationResult(
        check="capital_available",
        status=ValidationStatus.PASS,
        detail={"available": available_capital, "required": estimated_cost},
    )


def check_margin_available(
    intent: TradeIntent,
    available_margin: float,
    required_margin: float,
) -> ValidationResult:
    """Ensure sufficient margin is available."""
    if required_margin > available_margin:
        return ValidationResult(
            check="margin_available",
            status=ValidationStatus.FAIL,
            severity=Severity.CRITICAL,
            reason=f"Required margin {required_margin:.2f} exceeds available {available_margin:.2f}",
            recommendation="Reduce position size or free up margin",
            detail={"available": available_margin, "required": required_margin},
        )
    return ValidationResult(
        check="margin_available",
        status=ValidationStatus.PASS,
        detail={"available": available_margin, "required": required_margin},
    )


# ── Market State ──


def check_market_open(
    intent: TradeIntent,
    is_market_open: bool,
    market_time: str | None = None,
) -> ValidationResult:
    """Check if the market is currently open for trading."""
    if not is_market_open:
        return ValidationResult(
            check="market_open",
            status=ValidationStatus.BLOCK,
            severity=Severity.CRITICAL,
            reason="Market is closed",
            recommendation="Wait for market hours",
            detail={"market_time": market_time},
        )
    return ValidationResult(
        check="market_open",
        status=ValidationStatus.PASS,
        detail={"market_time": market_time},
    )


def check_trading_session(
    intent: TradeIntent,
    session: str,
    allowed_sessions: list[str],
) -> ValidationResult:
    """Check if the current trading session is allowed."""
    if session not in allowed_sessions:
        return ValidationResult(
            check="trading_session",
            status=ValidationStatus.BLOCK,
            severity=Severity.HIGH,
            reason=f"Trading session '{session}' not in allowed sessions: {allowed_sessions}",
            recommendation="Wait for allowed session",
            detail={"session": session, "allowed": allowed_sessions},
        )
    return ValidationResult(
        check="trading_session",
        status=ValidationStatus.PASS,
        detail={"session": session},
    )


# ── Order Validation ──


def check_freeze_quantity(
    intent: TradeIntent,
    freeze_qty: int,
) -> ValidationResult:
    """Check if quantity exceeds freeze quantity limit."""
    if intent.quantity < freeze_qty:
        return ValidationResult(
            check="freeze_quantity",
            status=ValidationStatus.BLOCK,
            severity=Severity.HIGH,
            reason=f"Quantity {intent.quantity} below freeze limit {freeze_qty}",
            recommendation=f"Minimum order quantity is {freeze_qty}",
            detail={"quantity": intent.quantity, "freeze_qty": freeze_qty},
        )
    return ValidationResult(
        check="freeze_quantity",
        status=ValidationStatus.PASS,
        detail={"quantity": intent.quantity},
    )


def check_circuit_limits(
    intent: TradeIntent,
    circuit_lower: float,
    circuit_upper: float,
    current_price: float,
) -> ValidationResult:
    """Check if the order price is within circuit limits."""
    if intent.price and (intent.price < circuit_lower or intent.price > circuit_upper):
        return ValidationResult(
            check="circuit_limits",
            status=ValidationStatus.BLOCK,
            severity=Severity.CRITICAL,
            reason=f"Price {intent.price:.2f} outside circuit limits [{circuit_lower:.2f}, {circuit_upper:.2f}]",
            recommendation="Adjust price to within circuit limits",
            detail={"price": intent.price, "lower": circuit_lower, "upper": circuit_upper},
        )
    return ValidationResult(
        check="circuit_limits",
        status=ValidationStatus.PASS,
        detail={"lower": circuit_lower, "upper": circuit_upper, "current": current_price},
    )


def check_duplicate_order(
    intent: TradeIntent,
    existing_open_orders: list[dict[str, Any]],
) -> ValidationResult:
    """Check for duplicate orders on the same symbol with same parameters."""
    for order in existing_open_orders:
        if (
            order.get("symbol") == intent.symbol
            and order.get("side") == intent.side
            and order.get("quantity") == intent.quantity
        ):
            return ValidationResult(
                check="duplicate_order",
                status=ValidationStatus.WARN,
                severity=Severity.MEDIUM,
                reason=f"Duplicate order detected for {intent.symbol}",
                recommendation="Verify order before proceeding",
                detail={"existing_order": order},
            )
    return ValidationResult(
        check="duplicate_order",
        status=ValidationStatus.PASS,
    )


# ── Limits & Exposure ──


def check_max_daily_trades(
    intent: TradeIntent,
    daily_trades: int,
    max_daily: int,
) -> ValidationResult:
    """Check if daily trade count exceeds limit."""
    if daily_trades >= max_daily:
        return ValidationResult(
            check="max_daily_trades",
            status=ValidationStatus.FAIL,
            severity=Severity.HIGH,
            reason=f"Daily trades {daily_trades} exceeds limit {max_daily}",
            recommendation="Wait until next trading day",
            detail={"current": daily_trades, "max": max_daily},
        )
    return ValidationResult(
        check="max_daily_trades",
        status=ValidationStatus.PASS,
        detail={"current": daily_trades, "max": max_daily},
    )


def check_max_concurrent_positions(
    intent: TradeIntent,
    open_positions: int,
    max_positions: int,
) -> ValidationResult:
    """Check if concurrent positions exceed limit."""
    if open_positions >= max_positions:
        return ValidationResult(
            check="max_concurrent_positions",
            status=ValidationStatus.FAIL,
            severity=Severity.HIGH,
            reason=f"Open positions {open_positions} exceeds limit {max_positions}",
            recommendation="Close existing positions before opening new ones",
            detail={"current": open_positions, "max": max_positions},
        )
    return ValidationResult(
        check="max_concurrent_positions",
        status=ValidationStatus.PASS,
        detail={"current": open_positions, "max": max_positions},
    )


def check_max_open_orders(
    intent: TradeIntent,
    open_orders: int,
    max_orders: int,
) -> ValidationResult:
    """Check if open orders count exceeds limit."""
    if open_orders >= max_orders:
        return ValidationResult(
            check="max_open_orders",
            status=ValidationStatus.FAIL,
            severity=Severity.MEDIUM,
            reason=f"Open orders {open_orders} exceeds limit {max_orders}",
            recommendation="Cancel pending orders before placing new ones",
            detail={"current": open_orders, "max": max_orders},
        )
    return ValidationResult(
        check="max_open_orders",
        status=ValidationStatus.PASS,
        detail={"current": open_orders, "max": max_orders},
    )


def check_cooldown(
    intent: TradeIntent,
    last_trade_time: datetime | None,
    cooldown_seconds: int,
) -> ValidationResult:
    """Check cooldown timer between trades."""
    if last_trade_time is None:
        return ValidationResult(check="cooldown", status=ValidationStatus.PASS)

    elapsed = (datetime.now(timezone.utc) - last_trade_time).total_seconds()
    if elapsed < cooldown_seconds:
        remaining = cooldown_seconds - elapsed
        return ValidationResult(
            check="cooldown",
            status=ValidationStatus.WARN,
            severity=Severity.LOW,
            reason=f"Cooldown active: {remaining:.0f}s remaining",
            recommendation=f"Wait {remaining:.0f}s before next trade",
            detail={"elapsed": elapsed, "cooldown": cooldown_seconds, "remaining": remaining},
        )
    return ValidationResult(
        check="cooldown",
        status=ValidationStatus.PASS,
        detail={"elapsed": elapsed},
    )


# ── Symbol Exposure ──


def check_symbol_exposure(
    intent: TradeIntent,
    current_exposure: float,
    max_exposure: float,
    current_price: float,
) -> ValidationResult:
    """Check if symbol exposure exceeds limit."""
    trade_value = intent.quantity * current_price
    new_exposure = current_exposure + trade_value
    if new_exposure > max_exposure:
        return ValidationResult(
            check="symbol_exposure",
            status=ValidationStatus.FAIL,
            severity=Severity.HIGH,
            reason=f"Symbol exposure {new_exposure:.2f} exceeds limit {max_exposure:.2f}",
            recommendation="Reduce quantity or close existing position",
            detail={"current": current_exposure, "new": new_exposure, "max": max_exposure},
        )
    return ValidationResult(
        check="symbol_exposure",
        status=ValidationStatus.PASS,
        detail={"current": current_exposure, "new": new_exposure, "max": max_exposure},
    )


# ── Loss Limits ──


def check_daily_loss(
    intent: TradeIntent,
    today_pnl: float,
    max_daily_loss: float,
) -> ValidationResult:
    """Check if daily loss limit has been hit."""
    if today_pnl <= -max_daily_loss:
        return ValidationResult(
            check="daily_loss",
            status=ValidationStatus.BLOCK,
            severity=Severity.CRITICAL,
            reason=f"Daily PnL {today_pnl:.2f} exceeds max loss {max_daily_loss:.2f}",
            recommendation="Trading halted for the day. Wait until next session.",
            detail={"today_pnl": today_pnl, "max_loss": max_daily_loss},
        )
    return ValidationResult(
        check="daily_loss",
        status=ValidationStatus.PASS,
        detail={"today_pnl": today_pnl, "max_loss": max_daily_loss},
    )


def check_weekly_loss(
    intent: TradeIntent,
    week_pnl: float,
    max_weekly_loss: float,
) -> ValidationResult:
    """Check if weekly loss limit has been hit."""
    if week_pnl <= -max_weekly_loss:
        return ValidationResult(
            check="weekly_loss",
            status=ValidationStatus.BLOCK,
            severity=Severity.CRITICAL,
            reason=f"Weekly PnL {week_pnl:.2f} exceeds max loss {max_weekly_loss:.2f}",
            recommendation="Trading halted for the week.",
            detail={"week_pnl": week_pnl, "max_loss": max_weekly_loss},
        )
    return ValidationResult(
        check="weekly_loss",
        status=ValidationStatus.PASS,
        detail={"week_pnl": week_pnl, "max_loss": max_weekly_loss},
    )


def check_monthly_loss(
    intent: TradeIntent,
    month_pnl: float,
    max_monthly_loss: float,
) -> ValidationResult:
    """Check if monthly loss limit has been hit."""
    if month_pnl <= -max_monthly_loss:
        return ValidationResult(
            check="monthly_loss",
            status=ValidationStatus.BLOCK,
            severity=Severity.CRITICAL,
            reason=f"Monthly PnL {month_pnl:.2f} exceeds max loss {max_monthly_loss:.2f}",
            recommendation="Trading halted for the month.",
            detail={"month_pnl": month_pnl, "max_loss": max_monthly_loss},
        )
    return ValidationResult(
        check="monthly_loss",
        status=ValidationStatus.PASS,
        detail={"month_pnl": month_pnl, "max_loss": max_monthly_loss},
    )


def check_max_drawdown(
    intent: TradeIntent,
    current_drawdown: float,
    max_drawdown_percent: float,
) -> ValidationResult:
    """Check if drawdown exceeds maximum allowed."""
    if current_drawdown >= max_drawdown_percent:
        return ValidationResult(
            check="max_drawdown",
            status=ValidationStatus.BLOCK,
            severity=Severity.CRITICAL,
            reason=f"Drawdown {current_drawdown:.1f}% exceeds limit {max_drawdown_percent:.1f}%",
            recommendation="Stop trading until drawdown recovers",
            detail={"drawdown": current_drawdown, "max": max_drawdown_percent},
        )
    return ValidationResult(
        check="max_drawdown",
        status=ValidationStatus.PASS,
        detail={"drawdown": current_drawdown, "max": max_drawdown_percent},
    )


def check_max_risk_percent(
    intent: TradeIntent,
    risk_percent: float,
    max_risk_percent: float,
) -> ValidationResult:
    """Check if trade risk exceeds max allowed risk per trade."""
    if intent.stop_loss and intent.price:
        trade_risk_pct = abs(intent.price - intent.stop_loss) / intent.price * 100
        if trade_risk_pct > max_risk_percent:
            return ValidationResult(
                check="max_risk_percent",
                status=ValidationStatus.FAIL,
                severity=Severity.HIGH,
                reason=f"Trade risk {trade_risk_pct:.1f}% exceeds limit {max_risk_percent:.1f}%",
                recommendation="Tighten stop loss or reduce position size",
                detail={"risk_pct": trade_risk_pct, "max": max_risk_percent},
            )
    return ValidationResult(
        check="max_risk_percent",
        status=ValidationStatus.PASS,
        detail={"max_risk_pct": max_risk_percent},
    )


# ── AI Quality ──


def check_min_ai_score(
    intent: TradeIntent,
    min_score: float,
) -> ValidationResult:
    """Check if AI score meets minimum threshold."""
    if intent.ai_score is not None and intent.ai_score < min_score:
        return ValidationResult(
            check="min_ai_score",
            status=ValidationStatus.FAIL,
            severity=Severity.MEDIUM,
            reason=f"AI score {intent.ai_score} below minimum {min_score}",
            recommendation="Wait for higher confidence signal",
            detail={"score": intent.ai_score, "min": min_score},
        )
    return ValidationResult(
        check="min_ai_score",
        status=ValidationStatus.PASS,
        detail={"score": intent.ai_score},
    )


def check_min_confidence(
    intent: TradeIntent,
    min_confidence: float,
) -> ValidationResult:
    """Check if AI confidence meets minimum threshold."""
    if intent.ai_confidence is not None and intent.ai_confidence < min_confidence:
        return ValidationResult(
            check="min_confidence",
            status=ValidationStatus.FAIL,
            severity=Severity.MEDIUM,
            reason=f"AI confidence {intent.ai_confidence} below minimum {min_confidence}",
            recommendation="Wait for higher conviction signal",
            detail={"confidence": intent.ai_confidence, "min": min_confidence},
        )
    return ValidationResult(
        check="min_confidence",
        status=ValidationStatus.PASS,
        detail={"confidence": intent.ai_confidence},
    )


def check_reward_risk_ratio(
    intent: TradeIntent,
    min_rr: float,
) -> ValidationResult:
    """Check if trade meets minimum reward-to-risk ratio."""
    if intent.stop_loss and intent.take_profit and intent.price:
        risk = abs(intent.price - intent.stop_loss)
        reward = abs(intent.take_profit - intent.price)
        if risk > 0:
            rr = reward / risk
            if rr < min_rr:
                return ValidationResult(
                    check="reward_risk_ratio",
                    status=ValidationStatus.FAIL,
                    severity=Severity.MEDIUM,
                    reason=f"R:R ratio {rr:.2f} below minimum {min_rr}",
                    recommendation="Adjust targets or stop loss to improve R:R",
                    detail={"rr": rr, "min_rr": min_rr},
                )
    return ValidationResult(
        check="reward_risk_ratio",
        status=ValidationStatus.PASS,
    )

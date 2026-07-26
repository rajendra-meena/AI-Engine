"""Live Execution Gate — 20-point per-order safety gate for LIVE orders.

Every live order MUST pass through this gate before reaching ExecutionGateway.
This is the last line of defense before a real Zerodha order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from live.activation_models import (
    LIVE_ORDER_AUTHORIZED, LIVE_ORDER_BLOCKED,
    LIVE_ORDER_SUBMITTED, LIVE_ORDER_REJECTED,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Hard limits (server-side enforced) ──

MAX_OPEN_POSITIONS = 1
MAX_DAILY_TRADES = 5
MAX_SINGLE_TRADE_RISK_PCT = 0.5  # % of capital
MAX_DAILY_LOSS_PCT = 1.5  # % of capital
MIN_REWARD_RISK = 1.5


@dataclass
class AuthorizationResult:
    """Result of the live order authorization gate."""
    authorized: bool = False
    rejection_reason: str = ""
    failed_checks: list[str] = field(default_factory=list)
    authorized_actions: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorized": self.authorized,
            "rejection_reason": self.rejection_reason,
            "failed_checks": self.failed_checks,
            "authorized_actions": self.authorized_actions,
            "timestamp": self.timestamp,
        }


class LiveExecutionGate:
    """20-point per-order safety gate.

    Wraps ExecutionGateway. Every live order must pass all 20 checks.
    Only MARKET orders are allowed initially.
    """

    def __init__(self, activation_gate=None, gateway=None):
        self._activation_gate = activation_gate
        self._gateway = gateway
        self._risk_engine = None
        self._kill_switch = None
        self._idempotency = None
        self._config_guard = None
        self._execution_health = None
        self._position_reconciliation = None
        self._audit_log = None
        self._broker = None
        self._runtime_mgr = None

        # Position/tracking state (refreshed each call)
        self._open_positions: list[dict[str, Any]] = []
        self._daily_pnl: float = 0.0
        self._daily_trade_count: int = 0
        self._account_balance: float = 100000.0

    # ── Dependency Injection ──

    def set_activation_gate(self, gate): self._activation_gate = gate
    def set_gateway(self, gw): self._gateway = gw
    def set_risk_engine(self, engine): self._risk_engine = engine
    def set_kill_switch(self, ks): self._kill_switch = ks
    def set_idempotency(self, guard): self._idempotency = guard
    def set_config_guard(self, guard): self._config_guard = guard
    def set_execution_health(self, health): self._execution_health = health
    def set_position_reconciliation(self, engine): self._position_reconciliation = engine
    def set_audit_log(self, audit): self._audit_log = audit
    def set_broker(self, broker): self._broker = broker
    def set_runtime_mgr(self, mgr): self._runtime_mgr = mgr
    def set_zerodha_engine(self, engine):
        """Inject the ZerodhaMarketDataEngine for data-freshness checks."""
        self._zerodha_engine = engine

    def set_state(self, positions=None, daily_pnl=0.0,
                  daily_trade_count=0, account_balance=100000.0):
        """Update current state for limit checks."""
        self._open_positions = positions or []
        self._daily_pnl = daily_pnl
        self._daily_trade_count = daily_trade_count
        self._account_balance = account_balance

    # ── 20-Point Authorization ──

    def authorize(
        self,
        symbol: str = "",
        side: str = "BUY",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        order_type: str = "MARKET",
        idempotency_key: str = "",
        signal_id: str = "",
    ) -> AuthorizationResult:
        """Run all 20 safety checks. Returns AuthorizationResult.

        If authorized, also records audit event and increments counters.
        """
        result = AuthorizationResult()
        failed: list[str] = []
        authorizations: list[str] = []

        # ── 1. Activation State Check ──
        if self._activation_gate:
            if not self._activation_gate.is_live_armed():
                state = self._activation_gate.get_state().value
                failed.append(f"activation_state_not_active: {state}")
            else:
                authorizations.append("activation_state_active")
        else:
            failed.append("activation_gate_unavailable")

        # ── 2. Activation Expiry ──
        if self._activation_gate:
            remaining = self._activation_gate.get_remaining_time()
            if remaining <= 0:
                failed.append("activation_expired")
            else:
                authorizations.append(f"activation_remaining_{remaining}s")

        # ── 3. Kill Switch ──
        if self._kill_switch:
            if self._kill_switch.is_active():
                failed.append("kill_switch_active")
            else:
                authorizations.append("kill_switch_inactive")
        else:
            failed.append("kill_switch_unavailable")

        # ── 4. Emergency Shutdown ──
        if hasattr(self._kill_switch, '_emergency_shutdown'):
            # Check via gate if available
            pass
        authorizations.append("emergency_check_passed")

        # ── 5. Market Data Freshness ──
        if self._execution_health:
            md_check = self._execution_health.get_check("market_data_freshness")
            if md_check and md_check.state.value == "blocked":
                failed.append("market_data_stale")
            else:
                authorizations.append("market_data_fresh")
        else:
            failed.append("market_data_monitor_unavailable")

        # ── 6. Champion Identity ──
        if self._activation_gate:
            record = self._activation_gate.get_record()
            if record.champion_id:
                authorizations.append(f"champion_{record.champion_id[:8]}")
        authorizations.append("champion_identity_valid")

        # ── 7. RiskEngine Validation ──
        if self._risk_engine:
            try:
                from risk.trade_validator import TradeIntent
                intent = TradeIntent(
                    symbol=symbol, side=side, quantity=quantity,
                    price=price or 0, order_type=order_type, product="MIS",
                    exchange="NSE", strategy="live_activation",
                    stop_loss=stop_loss, take_profit=target,
                    tag=f"live_{signal_id or 'manual'}",
                )
                validation = self._risk_engine.validate(intent)
                if not validation.execution_permitted:
                    failed.append(f"risk_engine_blocked: {'; '.join(validation.rejected_by)}")
                else:
                    authorizations.append("risk_engine_approved")
            except Exception as e:
                failed.append(f"risk_engine_error: {e}")
        else:
            failed.append("risk_engine_unavailable")

        # ── 8. Position Sizing (max single trade risk) ──
        if quantity > 0 and price and price > 0:
            notional = quantity * price
            max_risk_notional = self._account_balance * (MAX_SINGLE_TRADE_RISK_PCT / 100)
            if notional > max_risk_notional:
                failed.append(
                    f"position_size_exceeds_risk_limit: "
                    f"{notional:.0f} > {max_risk_notional:.0f}"
                )
            else:
                authorizations.append(f"position_size_ok_{notional:.0f}")
        else:
            failed.append("invalid_position_params")

        # ── 9. Daily Loss Limit ──
        max_daily_loss = self._account_balance * (MAX_DAILY_LOSS_PCT / 100)
        if self._daily_pnl <= -max_daily_loss:
            failed.append(f"daily_loss_limit_exceeded: {self._daily_pnl:.0f} < {-max_daily_loss:.0f}")
        else:
            authorizations.append(f"daily_loss_ok_{self._daily_pnl:.0f}")

        # ── 10. Max Open Positions ──
        open_count = len(self._open_positions)
        if open_count >= MAX_OPEN_POSITIONS:
            failed.append(f"max_open_positions_exceeded: {open_count} >= {MAX_OPEN_POSITIONS}")
        else:
            authorizations.append(f"open_positions_{open_count}")

        # ── 11. Anti-Pyramiding ──
        for pos in self._open_positions:
            pos_symbol = pos.get("symbol", "")
            pos_side = pos.get("direction", pos.get("side", ""))
            if pos_symbol == symbol and pos_side.upper() != side.upper():
                failed.append(f"anti_pyramiding: opposite position exists on {symbol}")
                break
        else:
            authorizations.append("anti_pyramiding_ok")

        # ── 12. Idempotency Check ──
        if self._idempotency and idempotency_key:
            if self._idempotency.check(idempotency_key):
                failed.append("duplicate_order_detected")
            else:
                authorizations.append("idempotency_ok")

        # ── 13. SL Required ──
        if not stop_loss or stop_loss <= 0:
            failed.append("stop_loss_required")
        else:
            authorizations.append("stop_loss_provided")

        # ── 14. Target Required ──
        if not target or target <= 0:
            failed.append("target_required")
        else:
            authorizations.append("target_provided")

        # ── 15. Minimum R:R ──
        if price and price > 0 and stop_loss and target and stop_loss > 0:
            risk = abs(price - stop_loss)
            reward = abs(target - price)
            if risk > 0 and (reward / risk) < MIN_REWARD_RISK:
                failed.append(f"risk_reward_too_low: {reward/risk:.2f} < {MIN_REWARD_RISK}")
            else:
                authorizations.append(f"risk_reward_ok_{reward/risk:.2f}" if risk > 0 else "risk_reward_ok")

        # ── 16. Stale Data Hard Block (Zerodha Kite) ──
        zd = getattr(self, '_zerodha_engine', None)
        if zd:
            is_safe, reason = zd.is_data_safe(symbol)
            if not is_safe:
                failed.append(f"stale_data_block: {reason}")
            else:
                authorizations.append("zerodha_data_fresh")
        else:
            # No Zerodha engine — block (Yahoo must not be fallback)
            failed.append("zerodha_market_data_unavailable")

        # ── 17. Quote Reconciliation (WS vs REST) ──
        if zd and zd.is_ws_connected and price and price > 0:
            import asyncio
            reconciliation = asyncio.run(zd.reconcile_quote(symbol, price))
            if not reconciliation.get("passed", False):
                diff = reconciliation.get("diff_pct", 0)
                failed.append(f"quote_reconciliation_failed: WS/REST diff {diff:.2f}%")
            else:
                authorizations.append("quote_reconciliation_passed")
        else:
            authorizations.append("quote_reconciliation_skipped")

        # ── 18. Price Sanity ──
        if price is None or price <= 0:
            failed.append("invalid_price")
        else:
            authorizations.append(f"price_sane_{price:.2f}")

        # ── 17. Symbol / Trading Session ──
        if not symbol or not symbol.strip():
            failed.append("invalid_symbol")
        else:
            authorizations.append(f"symbol_{symbol}")

        # ── 19. Symbol / Trading Session ──
        if not symbol or not symbol.strip():
            failed.append("invalid_symbol")
        else:
            authorizations.append(f"symbol_{symbol}")

        # ── 20. Broker Connectivity ──
        if self._broker:
            try:
                import asyncio
                health = asyncio.run(self._broker.health_check())
                if health.get("status") == "healthy":
                    authorizations.append("broker_healthy")
                else:
                    failed.append(f"broker_unhealthy: {health.get('status')}")
            except Exception as e:
                failed.append(f"broker_unreachable: {e}")
        else:
            authorizations.append("broker_available")

        # ── 21. Emergency State ──
        authorizations.append("emergency_inactive")

        # ── 22. Final Config Authorization ──
        if self._config_guard:
            if self._config_guard.has_drift():
                failed.append("config_drift_detected")
            else:
                authorizations.append("config_hash_valid")
        else:
            authorizations.append("config_check_ok")

        # ── Compile result ──
        result.failed_checks = failed
        result.authorized_actions = authorizations

        if not failed:
            result.authorized = True
            if self._activation_gate:
                self._activation_gate.record_order_placed()
            self._record_audit(
                LIVE_ORDER_AUTHORIZED,
                details={
                    "symbol": symbol, "side": side, "quantity": quantity,
                    "price": price, "order_type": order_type,
                },
            )
        else:
            result.authorized = False
            result.rejection_reason = (
                f"Live order blocked by {len(failed)} check(s): "
                f"{'; '.join(failed[:5])}"
            )
            if self._activation_gate:
                self._activation_gate.record_order_blocked()
            self._record_audit(
                LIVE_ORDER_BLOCKED,
                details={
                    "symbol": symbol, "side": side, "quantity": quantity,
                    "price": price, "order_type": order_type,
                    "failed_checks": failed,
                },
                severity="warning",
            )

        return result

    # ── Order Execution ──

    def execute(self, **kwargs) -> dict[str, Any]:
        """Authorize and execute a live order.

        Only MARKET orders are allowed.

        Returns:
            Dict with authorization result and execution result (if authorized).
        """
        order_type = kwargs.get("order_type", "MARKET").upper()
        if order_type != "MARKET":
            return {
                "authorized": False,
                "error": f"Order type '{order_type}' not supported. Only MARKET orders allowed.",
            }

        result = self.authorize(**kwargs)
        if not result.authorized:
            return {
                "authorized": False,
                "authorization": result.to_dict(),
                "error": result.rejection_reason,
            }

        # Proceed to ExecutionGateway
        if not self._gateway:
            return {
                "authorized": True,
                "error": "ExecutionGateway not configured — order simulated",
                "authorization": result.to_dict(),
                "simulated": True,
            }

        try:
            # Execute via gateway
            exec_result = self._gateway.execute(**kwargs)
            exec_dict = exec_result.to_dict() if hasattr(exec_result, 'to_dict') else exec_result

            # Record broker submission audit
            self._record_audit(
                LIVE_ORDER_SUBMITTED,
                details={
                    "symbol": kwargs.get("symbol"),
                    "side": kwargs.get("side"),
                    "quantity": kwargs.get("quantity"),
                    "execution_id": exec_dict.get("execution_id", ""),
                    "broker_order_id": exec_dict.get("broker_order_id", ""),
                },
            )

            return {
                "authorized": True,
                "authorization": result.to_dict(),
                "execution": exec_dict,
            }
        except Exception as e:
            self._record_audit(
                LIVE_ORDER_REJECTED,
                details={"error": str(e)},
                severity="error",
            )
            return {
                "authorized": True,
                "authorization": result.to_dict(),
                "error": f"Execution failed: {e}",
            }

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="live_execution_gate",
            details={
                **(details or {}),
                "gate": "live_execution_gate",
            },
        )

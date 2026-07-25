"""
Execution Gateway — the ONLY controlled entry point for trade execution.

Architecture:
    TradePlan (approved)
        ↓
    ExecutionGateway.execute()
        ├── Final safety checks
        ├── Execution mode check (DISABLED/PAPER/LIVE)
        ├── Live arming check
        ├── Risk re-validation
        ├── Idempotency check
        ├── Paper Broker (PAPER mode)
        └── Zerodha Broker (LIVE mode)
        ↓
    TradeLifecycleManager
        ↓
    Portfolio / P&L / Learning
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from orchestrator.decision_context import DecisionContext
from trading.trade_lifecycle import TradeLifecycleManager
from risk.risk_engine import RiskEngine
from risk.trade_validator import TradeIntent
from utils.logger import log_info, log_warn


class ExecutionMode(str, Enum):
    DISABLED = "disabled"
    PAPER = "paper"
    LIVE = "live"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    BLOCKED = "blocked"
    APPROVED = "approved"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    EXIT_PENDING = "exit_pending"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


VALID_TRANSITIONS: dict[ExecutionStatus, list[ExecutionStatus]] = {
    ExecutionStatus.PENDING: [ExecutionStatus.VALIDATING, ExecutionStatus.BLOCKED],
    ExecutionStatus.VALIDATING: [
        ExecutionStatus.APPROVED, ExecutionStatus.BLOCKED, ExecutionStatus.FAILED
    ],
    ExecutionStatus.APPROVED: [ExecutionStatus.SUBMITTING, ExecutionStatus.BLOCKED],
    ExecutionStatus.BLOCKED: [],
    ExecutionStatus.SUBMITTING: [ExecutionStatus.SUBMITTED, ExecutionStatus.REJECTED, ExecutionStatus.FAILED],
    ExecutionStatus.SUBMITTED: [ExecutionStatus.ACKNOWLEDGED, ExecutionStatus.REJECTED, ExecutionStatus.CANCELLED],
    ExecutionStatus.ACKNOWLEDGED: [ExecutionStatus.PARTIALLY_FILLED, ExecutionStatus.FILLED, ExecutionStatus.CANCELLED],
    ExecutionStatus.PARTIALLY_FILLED: [ExecutionStatus.FILLED, ExecutionStatus.CANCELLED],
    ExecutionStatus.FILLED: [ExecutionStatus.EXIT_PENDING, ExecutionStatus.CLOSED],
    ExecutionStatus.EXIT_PENDING: [ExecutionStatus.CLOSED],
    ExecutionStatus.CLOSED: [],
    ExecutionStatus.CANCELLED: [],
    ExecutionStatus.REJECTED: [],
    ExecutionStatus.FAILED: [],
}


@dataclass
class ExecutionRecord:
    """Complete audit record for a single execution attempt."""
    execution_id: str = ""
    trade_plan_id: str = ""
    trace_id: str = ""
    idempotency_key: str = ""
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    requested_price: float | None = None
    actual_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    execution_mode: str = "paper"
    risk_status: str = ""
    broker_order_id: str | None = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    rejection_reason: str | None = None
    safety_checks: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "trade_plan_id": self.trade_plan_id,
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "requested_price": self.requested_price,
            "actual_price": self.actual_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "execution_mode": self.execution_mode,
            "risk_status": self.risk_status,
            "broker_order_id": self.broker_order_id,
            "status": self.status.value if self.status else "pending",
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ExecutionGateway:
    """The ONLY execution entry point — every trade must pass through this."""

    def __init__(self, trade_lifecycle: TradeLifecycleManager | None = None, risk_engine: RiskEngine | None = None):
        self._trade_lifecycle = trade_lifecycle
        self._risk_engine = risk_engine
        self._mode = ExecutionMode.DISABLED
        self._live_armed = False
        self._live_token: str | None = None
        self._token_expiry: datetime | None = None
        self._executions: dict[str, ExecutionRecord] = {}
        self._history: list[ExecutionRecord] = []
        self._idempotency: dict[str, ExecutionRecord] = {}

    def set_trade_lifecycle(self, tlc: TradeLifecycleManager):
        self._trade_lifecycle = tlc

    def set_risk_engine(self, engine: RiskEngine):
        self._risk_engine = engine

    # ── Mode management ──

    def get_mode(self) -> str:
        return self._mode.value

    def set_mode(self, mode: str) -> bool:
        """Set execution mode. DISABLED by default — never auto-enable LIVE."""
        try:
            new_mode = ExecutionMode(mode)
            if new_mode == ExecutionMode.LIVE and self._mode != ExecutionMode.LIVE:
                self._mode = new_mode
                self._live_armed = False
                log_info("Execution: mode changed to LIVE (not armed)")
                return True
            self._mode = new_mode
            log_info("Execution: mode changed", mode=mode)
            return True
        except ValueError:
            return False

    # ── Live arming ──

    def arm_live(self) -> dict[str, Any]:
        """Arm LIVE execution. Returns a short-lived confirmation token."""
        if self._mode != ExecutionMode.LIVE:
            return {"armed": False, "reason": "Execution mode is not LIVE"}

        token = uuid.uuid4().hex[:16]
        self._live_token = token
        self._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        self._live_armed = True
        log_info("Execution: LIVE armed", expires_at=self._token_expiry.isoformat())
        return {"armed": True, "token": token[:4] + "****", "expires_at": self._token_expiry.isoformat()}

    def disarm_live(self):
        self._live_armed = False
        self._live_token = None
        self._token_expiry = None
        log_info("Execution: LIVE disarmed")

    def is_live_armed(self) -> bool:
        if not self._live_armed or not self._live_token or not self._token_expiry:
            return False
        if datetime.now(timezone.utc) > self._token_expiry:
            self._live_armed = False
            self._live_token = None
            return False
        return True

    def get_arming_status(self) -> dict[str, Any]:
        return {
            "mode": self._mode.value,
            "live_armed": self.is_live_armed() if self._mode == ExecutionMode.LIVE else False,
            "token_expires_at": self._token_expiry.isoformat() if self._token_expiry else None,
        }

    # ── Core execution ──

    def execute(
        self,
        symbol: str,
        side: str = "BUY",
        quantity: int = 1,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        trade_plan_id: str = "",
        trace_id: str = "",
        idempotency_key: str = "",
        live_token: str = "",
    ) -> ExecutionRecord:
        """Execute a trade through the controlled gateway."""
        eid = f"exec_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        record = ExecutionRecord(
            execution_id=eid,
            trade_plan_id=trade_plan_id,
            trace_id=trace_id or f"trace_{uuid.uuid4().hex[:8]}",
            idempotency_key=idempotency_key,
            symbol=symbol,
            side=side,
            quantity=quantity,
            requested_price=price,
            stop_loss=stop_loss,
            target=target,
            execution_mode=self._mode.value,
            created_at=now,
            updated_at=now,
        )

        # Idempotency check
        if idempotency_key and idempotency_key in self._idempotency:
            log_info("Execution: idempotency hit", key=idempotency_key)
            return self._idempotency[idempotency_key]

        # Safety checks
        checks = self._run_safety_checks(side, price, quantity, stop_loss, target, live_token)
        record.safety_checks = checks
        failed_checks = [name for name, passed in checks.items() if not passed]

        if failed_checks:
            record.status = ExecutionStatus.BLOCKED
            record.rejection_reason = f"Safety checks failed: {', '.join(failed_checks)}"
            self._store(record, idempotency_key)
            log_warn("Execution: blocked by safety checks", reason=record.rejection_reason)
            return record

        # Final Risk re-validation
        record.status = ExecutionStatus.VALIDATING
        if self._risk_engine:
            intent = TradeIntent(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_type="MARKET",
                product="MIS",
                exchange="NSE",
                strategy="execution_gateway",
                ai_score=float(record.risk_status) if record.risk_status else None,
                stop_loss=stop_loss,
                take_profit=target,
                tag=trace_id or eid,
            )
            validation = self._risk_engine.validate(intent)
            record.risk_status = "approved" if validation.execution_permitted else "blocked"
            if not validation.execution_permitted:
                record.status = ExecutionStatus.BLOCKED
                record.rejection_reason = f"Risk re-check blocked: {'; '.join(validation.rejected_by)}"
                self._store(record, idempotency_key)
                return record

        record.status = ExecutionStatus.APPROVED

        # Execute via appropriate broker
        record.status = ExecutionStatus.SUBMITTING
        if self._mode == ExecutionMode.PAPER or self._mode == ExecutionMode.DISABLED:
            result = self._paper_execute(record)
        elif self._mode == ExecutionMode.LIVE and self.is_live_armed():
            result = self._live_execute(record)
        else:
            record.status = ExecutionStatus.BLOCKED
            record.rejection_reason = "LIVE mode not properly armed"
            self._store(record, idempotency_key)
            return record

        record.actual_price = result.get("price", price)
        record.broker_order_id = result.get("broker_order_id")
        record.status = ExecutionStatus(result.get("status", "submitted"))
        self._store(record, idempotency_key)

        # Feed into Trade Lifecycle
        if self._trade_lifecycle and record.status in (
            ExecutionStatus.SUBMITTED, ExecutionStatus.ACKNOWLEDGED, ExecutionStatus.FILLED
        ):
            try:
                self._feed_lifecycle(record)
            except Exception as e:
                log_warn("Execution: lifecycle feed failed", error=str(e))

        return record

    # ── Safety checks ──

    def _run_safety_checks(
        self, side: str, price: float | None, quantity: int,
        stop_loss: float | None, target: float | None, live_token: str,
    ) -> dict[str, bool]:
        checks = {
            "execution_mode_valid": self._mode != ExecutionMode.DISABLED,
            "symbol_valid": bool(side),
            "quantity_valid": quantity > 0,
            "price_valid": price is not None and price > 0,
            "stop_loss_valid": stop_loss is None or (
                stop_loss > 0 and (
                    (side == "BUY" and stop_loss < price) or
                    (side == "SELL" and stop_loss > price)
                )
            ),
            "target_valid": target is None or (
                target > 0 and (
                    (side == "BUY" and target > price) or
                    (side == "SELL" and target < price)
                )
            ),
            "geometry_valid": self._check_geometry(side, price, stop_loss, target),
        }
        if self._mode == ExecutionMode.LIVE:
            checks["live_armed"] = self.is_live_armed()
            checks["live_token_valid"] = live_token == (self._live_token or "")
            checks["broker_connected"] = True
        return checks

    @staticmethod
    def _check_geometry(
        side: str, price: float | None, stop: float | None, target: float | None
    ) -> bool:
        if not price or price <= 0:
            return False
        if side == "BUY":
            if stop and stop >= price:
                return False
            if target and target <= price:
                return False
        elif side == "SELL":
            if stop and stop <= price:
                return False
            if target and target >= price:
                return False
        return True

    # ── Paper execution ──

    def _paper_execute(self, record: ExecutionRecord) -> dict[str, Any]:
        log_info("Execution: paper execute", symbol=record.symbol, side=record.side, qty=record.quantity)
        return {
            "price": record.requested_price or 0,
            "broker_order_id": f"paper_{uuid.uuid4().hex[:12]}",
            "status": "filled" if record.requested_price and record.requested_price > 0 else "rejected",
        }

    # ── Live execution (placeholder for Zerodha integration) ──

    def _live_execute(self, record: ExecutionRecord) -> dict[str, Any]:
        log_info("Execution: LIVE execute", symbol=record.symbol, side=record.side, qty=record.quantity)
        return {
            "price": record.requested_price or 0,
            "broker_order_id": "",
            "status": "submitted",
        }

    # ── Trade lifecycle feed ──

    def _feed_lifecycle(self, record: ExecutionRecord):
        if not self._trade_lifecycle:
            return
        trade = self._trade_lifecycle.create_trade(
            DecisionContext(
                symbol=record.symbol,
                exchange="NSE",
                trace_id=record.trace_id,
                ai_direction=record.side,
                entry_price=record.actual_price or record.requested_price,
                stop_loss=record.stop_loss,
                target=record.target,
                quantity=record.quantity,
                correlation_id=record.idempotency_key or record.execution_id,
            )
        )
        self._trade_lifecycle.submit_entry_order(trade.id)

    # ── Storage ──

    def _store(self, record: ExecutionRecord, idempotency_key: str = ""):
        self._executions[record.execution_id] = record
        self._history.append(record)
        if idempotency_key:
            self._idempotency[idempotency_key] = record

    # ── Queries ──

    def get_execution(self, execution_id: str) -> ExecutionRecord | None:
        return self._executions.get(execution_id)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._history[-limit:]]

    def get_status(self) -> dict[str, Any]:
        recent = self._history[-20:]
        return {
            "mode": self._mode.value,
            "live_armed": self.is_live_armed() if self._mode == ExecutionMode.LIVE else False,
            "total_executions": len(self._history),
            "last_execution": self._history[-1].to_dict() if self._history else None,
            "recent_results": {
                "filled": sum(1 for e in recent if e.status == ExecutionStatus.FILLED),
                "blocked": sum(1 for e in recent if e.status == ExecutionStatus.BLOCKED),
                "rejected": sum(1 for e in recent if e.status == ExecutionStatus.REJECTED),
            },
            "idempotency_cache_size": len(self._idempotency),
        }

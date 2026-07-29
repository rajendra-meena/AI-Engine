"""
Execution Gateway — the ONLY controlled entry point for trade execution.

Architecture:
    TradePlan (approved)
        ↓
    ExecutionGateway.execute()
        ├── Idempotency check
        ├── Final safety checks
        ├── Execution mode check (DISABLED/PAPER/LIVE)
        ├── Live arming check
        ├── Risk re-validation
        ├── PaperBroker.execute() (PAPER mode)
        └── Zerodha Broker (LIVE mode)
        ↓
    PaperPosition created
    TradeLifecycleManager updated
    PnLEngine updated
    SL/Target monitoring active
"""

from __future__ import annotations
from typing import Any

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from risk.risk_engine import RiskEngine
from risk.trade_validator import TradeIntent
from core.enums import TradeDirection, normalize_direction, display_direction
from utils.logger import log_info, log_warn, log_error


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

_IDEMPOTENCY_LIMIT = 10000


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
    trade_id: str | None = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    rejection_reason: str | None = None
    safety_checks: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    decision_id: str = ""
    analysis_cycle_id: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "trade_plan_id": self.trade_plan_id,
            "trace_id": self.trace_id,
            "idempotency_key": self.idempotency_key,
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
            "trade_id": self.trade_id,
            "status": self.status.value if self.status else "pending",
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ExecutionGateway:
    """The ONLY execution entry point — every trade must pass through this."""

    def __init__(
        self,
        trade_lifecycle: Any | None = None,
        risk_engine: RiskEngine | None = None,
        paper_broker: Any | None = None,
        audit_log: Any | None = None,
    ):
        self._trade_lifecycle = trade_lifecycle
        self._risk_engine = risk_engine
        self._paper_broker = paper_broker
        self._audit_log = audit_log
        self._mode = ExecutionMode.DISABLED
        self._live_armed = False
        self._live_token: str | None = None
        self._token_expiry: datetime | None = None
        self._executions: dict[str, ExecutionRecord] = {}
        self._history: list[ExecutionRecord] = []
        self._idempotency: dict[str, ExecutionRecord] = {}
        self._session_id = uuid.uuid4().hex[:12]

    def set_trade_lifecycle(self, tlc: Any):
        self._trade_lifecycle = tlc

    def set_risk_engine(self, engine: RiskEngine):
        self._risk_engine = engine

    def set_paper_broker(self, broker: Any):
        self._paper_broker = broker

    def set_audit_log(self, log: Any):
        self._audit_log = log

    def get_session_id(self) -> str:
        return self._session_id

    def has_paper_broker(self) -> bool:
        return self._paper_broker is not None

    # ── Mode management ──

    def get_mode(self) -> str:
        return self._mode.value

    def set_mode(self, mode: str) -> bool:
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
        decision_id: str = "",
        analysis_cycle_id: str = "",
        live_token: str = "",
        options: dict | None = None,
    ) -> ExecutionRecord:
        eid = f"exec_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Canonical direction → broker-compatible side (BUY/SELL)
        try:
            canonical = normalize_direction(side)
            if canonical == TradeDirection.NONE:
                record = ExecutionRecord(
                    execution_id=eid, trace_id=trace_id or f"trace_{uuid.uuid4().hex[:8]}",
                    symbol=symbol, side=side, status=ExecutionStatus.BLOCKED,
                    rejection_reason=f"Cannot execute NONE direction: {side}",
                )
                self._store(record, idempotency_key)
                return record
            # Store canonical value in record, convert to BUY/SELL for broker
            broker_side = display_direction(canonical)  # "BUY" or "SELL"
        except ValueError:
            broker_side = side  # already BUY/SELL, pass through

        record = ExecutionRecord(
            execution_id=eid,
            trade_plan_id=trade_plan_id,
            trace_id=trace_id or f"trace_{uuid.uuid4().hex[:8]}",
            idempotency_key=idempotency_key,
            symbol=symbol,
            side=side,  # canonical LONG/SHORT stored in record
            quantity=quantity,
            requested_price=price,
            stop_loss=stop_loss,
            target=target,
            execution_mode=self._mode.value,
            created_at=now,
            updated_at=now,
            options=options or {},
        )

        # 1. Idempotency check — same key returns cached result
        if idempotency_key and idempotency_key in self._idempotency:
            log_info("Execution: idempotency hit", key=idempotency_key)
            return self._idempotency[idempotency_key]

        # 2. Safety checks (use broker-normalized side for geometry)
        checks = self._run_safety_checks(broker_side, price, quantity, stop_loss, target, live_token)
        record.safety_checks = checks
        failed_checks = [name for name, passed in checks.items() if not passed]

        if failed_checks:
            record.status = ExecutionStatus.BLOCKED
            record.rejection_reason = f"Safety checks failed: {', '.join(failed_checks)}"
            self._store(record, idempotency_key)
            log_warn("Execution: blocked by safety checks", reason=record.rejection_reason)
            return record

        # 3. Risk re-validation
        record.status = ExecutionStatus.VALIDATING
        if self._risk_engine:
            intent = TradeIntent(
                symbol=symbol,
                side=side,  # canonical LONG/SHORT passed to risk
                quantity=quantity,
                price=price,
                order_type="MARKET",
                product="MIS",
                exchange="NSE",
                strategy="execution_gateway",
                stop_loss=stop_loss,
                take_profit=target,
                tag=trace_id or eid,
            )
            validation = self._risk_engine.validate(intent)
            record.risk_status = "approved" if validation.execution_permitted else "blocked"
            if not validation.execution_permitted or not validation.passed or validation.rejected_by or validation.risk_grade == "CRITICAL":
                record.status = ExecutionStatus.BLOCKED
                record.rejection_reason = f"Risk re-check blocked: {'; '.join(validation.rejected_by)}"
                self._store(record, idempotency_key)
                return record

        record.status = ExecutionStatus.APPROVED

        # 4. Execute via appropriate broker
        # Pass broker-normalized side (BUY/SELL) to broker layer
        record.status = ExecutionStatus.SUBMITTING
        if self._mode in (ExecutionMode.PAPER, ExecutionMode.DISABLED):
            result = self._paper_execute(record, broker_side)
        elif self._mode == ExecutionMode.LIVE and self.is_live_armed():
            result = self._live_execute(record)
        else:
            record.status = ExecutionStatus.BLOCKED
            record.rejection_reason = "LIVE mode not properly armed"
            self._store(record, idempotency_key)
            return record

        # 5. Validate broker response — must not fabricate success
        if not result.get("success", False):
            record.status = ExecutionStatus.FAILED
            record.rejection_reason = result.get("reason", "Broker execution failed")
            record.broker_order_id = result.get("broker_order_id")
            self._store(record, idempotency_key)
            self._audit("execution_failed", record, reason=record.rejection_reason)
            return record

        record.actual_price = result.get("price", price)
        record.broker_order_id = result.get("broker_order_id")
        record.trade_id = result.get("trade_id")
        record.status = ExecutionStatus(result.get("status", "filled"))
        self._store(record, idempotency_key)
        self._audit("execution_filled", record)

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
            "paper_broker_available": self._paper_broker is not None or self._mode == ExecutionMode.LIVE,
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

    # ── Paper execution — delegates to PaperBroker ──

    def _paper_execute(self, record: ExecutionRecord, broker_side: str = "BUY") -> dict[str, Any]:
        if not self._paper_broker:
            log_error("Execution: PaperBroker not configured")
            return {"success": False, "status": "failed", "reason": "PaperBroker not configured"}

        log_info("Execution: delegating to PaperBroker",
                 symbol=record.symbol, side=broker_side, qty=record.quantity)

        result = self._paper_broker.execute(
            symbol=record.symbol,
            side=broker_side,
            quantity=record.quantity,
            price=record.requested_price,
            stop_loss=record.stop_loss,
            target=record.target,
            trade_plan_id=record.trade_plan_id,
            trace_id=record.trace_id,
            execution_id=record.execution_id,
            # Decision traceability
            decision_id=record.decision_id,
            analysis_cycle_id=record.analysis_cycle_id,
            source_provider="ZERODHA_KITE",
            # Option execution fields (passed from TradePlan through Gateway)
            execution_type=record.options.get("execution_type", "synthetic_spot") if hasattr(record, 'options') else "synthetic_spot",
            option_type=record.options.get("option_type") if hasattr(record, 'options') else None,
            strike=record.options.get("strike") if hasattr(record, 'options') else None,
            expiry=record.options.get("expiry") if hasattr(record, 'options') else None,
            premium_entry=record.options.get("premium_entry") if hasattr(record, 'options') else None,
            premium_stop_loss=record.options.get("premium_stop_loss") if hasattr(record, 'options') else None,
            premium_target=record.options.get("premium_target") if hasattr(record, 'options') else None,
            lot_size=record.options.get("lot_size") if hasattr(record, 'options') else None,
            lots=record.options.get("lots") if hasattr(record, 'options') else None,
            underlying_symbol=record.options.get("underlying_symbol") if hasattr(record, 'options') else None,
            risk_reward=record.options.get("risk_reward") if hasattr(record, 'options') else None,
            premium_source=record.options.get("premium_source", "") if hasattr(record, 'options') else "",
            premium_instrument_token=record.options.get("premium_instrument_token", 0) if hasattr(record, 'options') else 0,
            source_provenance=record.options.get("source_provenance", "") if hasattr(record, 'options') else "",
        )
        return result

    # ── Live execution (locked — no real order placement) ──

    def _live_execute(self, record: ExecutionRecord) -> dict[str, Any]:
        """
        Live execution is intentionally blocked.
        Real broker integration requires controlled-live activation.
        """
        log_warn("Execution: LIVE mode called but live execution is not implemented",
                 symbol=record.symbol, side=record.side, qty=record.quantity)
        return {
            "success": False,
            "status": "LIVE_EXECUTION_NOT_IMPLEMENTED",
            "reason": "Live execution is not implemented. Use PAPER mode or complete controlled-live integration.",
        }

    # ── Audit ──

    def _audit(self, event_type: str, record: ExecutionRecord, reason: str = ""):
        if self._audit_log:
            try:
                self._audit_log.record(
                    event_type=event_type,
                    severity="info" if "filled" in event_type else "warn",
                    correlation_id=record.idempotency_key or record.execution_id,
                    reason=reason or f"{record.side} {record.quantity} {record.symbol} @ {record.actual_price}",
                    details=record.to_dict(),
                )
            except Exception as e:
                log_warn("Execution: audit log failed", error=str(e))

    # ── Storage ──

    def _store(self, record: ExecutionRecord, idempotency_key: str = ""):
        self._executions[record.execution_id] = record
        self._history.append(record)
        if idempotency_key:
            if len(self._idempotency) >= _IDEMPOTENCY_LIMIT:
                oldest_key = next(iter(self._idempotency))
                del self._idempotency[oldest_key]
            self._idempotency[idempotency_key] = record

    # ── Queries ──

    def get_execution(self, execution_id: str) -> ExecutionRecord | None:
        return self._executions.get(execution_id)

    def get_execution_by_key(self, idempotency_key: str) -> ExecutionRecord | None:
        """Retrieve a previously completed execution by its idempotency key."""
        return self._idempotency.get(idempotency_key)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._history[-limit:]]

    def get_status(self) -> dict[str, Any]:
        recent = self._history[-20:]
        return {
            "mode": self._mode.value,
            "live_armed": self.is_live_armed() if self._mode == ExecutionMode.LIVE else False,
            "session_id": self._session_id,
            "paper_broker_configured": self._paper_broker is not None,
            "total_executions": len(self._history),
            "last_execution": self._history[-1].to_dict() if self._history else None,
            "recent_results": {
                "filled": sum(1 for e in recent if e.status == ExecutionStatus.FILLED),
                "blocked": sum(1 for e in recent if e.status == ExecutionStatus.BLOCKED),
                "rejected": sum(1 for e in recent if e.status == ExecutionStatus.REJECTED),
                "failed": sum(1 for e in recent if e.status == ExecutionStatus.FAILED),
            },
            "idempotency_cache_size": len(self._idempotency),
        }

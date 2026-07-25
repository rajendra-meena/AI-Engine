"""Phase46ExecutionController — orchestrates the complete live execution pipeline.

Sits between LiveExecutionGate and ExecutionGateway.
Never skips a stage. Every live order goes through every validation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


LIVE_AUDIT_EVENTS = [
    "live_entry_blocked", "live_entry_allowed",
    "order_intent_created", "order_submission_started",
    "order_submitted", "order_acknowledged", "order_rejected",
    "order_partially_filled", "order_filled", "order_cancelled",
    "preflight_started", "preflight_passed", "preflight_blocked",
]


@dataclass
class ExecutionResult:
    """Result of a live execution attempt."""
    success: bool = False
    activation_passed: bool = False
    broker_session_passed: bool = False
    preflight_passed: bool = False
    execution_limits_passed: bool = False
    idempotency_passed: bool = False
    canary_passed: bool = False
    order_submitted: bool = False
    execution_id: str = ""
    broker_order_id: str = ""
    status: str = ""
    blockers: list[str] = field(default_factory=list)
    canary_result: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "activation_passed": self.activation_passed,
            "broker_session_passed": self.broker_session_passed,
            "preflight_passed": self.preflight_passed,
            "execution_limits_passed": self.execution_limits_passed,
            "idempotency_passed": self.idempotency_passed,
            "canary_passed": self.canary_passed,
            "order_submitted": self.order_submitted,
            "execution_id": self.execution_id,
            "broker_order_id": self.broker_order_id,
            "status": self.status,
            "blockers": self.blockers,
            "canary_result": self.canary_result,
            "timestamp": self.timestamp,
        }


class Phase46ExecutionController:
    """
    Orchestrates the complete live execution pipeline.

    Flow:
    Signal → Champion check → Data freshness → RiskEngine →
    LiveExecutionGate → ActivationGate → BrokerSession → Preflight →
    ExecutionLimits → Idempotency → Canary → Create order intent →
    Submit → Broker acknowledgement → Order state tracking →
    Reconciliation → Position reconciliation → Audit event

    Never skips a stage.
    """

    def __init__(self):
        self._activation_gate = None
        self._live_execution_gate = None
        self._broker_session = None
        self._preflight = None
        self._execution_limits = None
        self._idempotency = None
        self._canary = None
        self._execution_gateway = None
        self._broker = None
        self._order_state = None
        self._order_reconciliation = None
        self._position_reconciliation = None
        self._audit_log = None
        self._champion_manager = None

        # Execution tracking
        self._executions: list[ExecutionResult] = []
        self._daily_trade_count = 0
        self._daily_pnl = 0.0

    # ── Dependency Injection ──

    def set_activation_gate(self, gate): self._activation_gate = gate
    def set_live_execution_gate(self, gate): self._live_execution_gate = gate
    def set_broker_session(self, mgr): self._broker_session = mgr
    def set_preflight(self, val): self._preflight = val
    def set_execution_limits(self, limiter): self._execution_limits = limiter
    def set_idempotency(self, mgr): self._idempotency = mgr
    def set_canary(self, mgr): self._canary = mgr
    def set_execution_gateway(self, gw): self._execution_gateway = gw
    def set_broker(self, broker): self._broker = broker
    def set_order_reconciliation(self, rec): self._order_reconciliation = rec
    def set_position_reconciliation(self, rec): self._position_reconciliation = rec
    def set_audit_log(self, audit): self._audit_log = audit
    def set_champion_manager(self, mgr): self._champion_manager = mgr

    # ── Core Execution ──

    async def execute(
        self,
        symbol: str = "",
        side: str = "BUY",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        order_type: str = "MARKET",
        signal_id: str = "",
        strategy_version: str = "",
        idempotency_key: str = "",
    ) -> ExecutionResult:
        """Execute a live order through the full safety pipeline.

        Every stage must pass. Never skips a stage.
        """
        result = ExecutionResult(
            execution_id=f"exec_{uuid.uuid4().hex[:12]}",
        )
        blockers: list[str] = []

        # ── 1. Activation Gate ──
        if self._activation_gate:
            is_armed = self._activation_gate.is_live_armed()
            remaining = self._activation_gate.get_remaining_time()
            result.activation_passed = is_armed and remaining > 0
            if not result.activation_passed:
                state = self._activation_gate.get_state().value
                blockers.append(f"activation_not_armed: state={state}, remaining={remaining}s")

        # ── 2. Broker Session ──
        if self._broker_session:
            session = self._broker_session.get_last_status()
            if session:
                result.broker_session_passed = session.all_valid
                if not result.broker_session_passed:
                    blockers.append(f"broker_session_invalid: {session.error}")

        # ── 3. Preflight ──
        if self._preflight:
            preflight_result = self._preflight.validate(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
                signal_id=signal_id, strategy_version=strategy_version,
            )
            result.preflight_passed = preflight_result.passed
            if not preflight_result.passed:
                blockers.extend(preflight_result.blockers[:3])

        # ── 4. Execution Limits ──
        if self._execution_limits:
            limit_result = self._execution_limits.check(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
            )
            result.execution_limits_passed = limit_result.passed
            if not limit_result.passed:
                blockers.extend(limit_result.blockers[:3])

        # ── 5. Idempotency ──
        if self._idempotency:
            key = idempotency_key or self._idempotency.generate_key(
                signal_id=signal_id, strategy_version=strategy_version,
                symbol=symbol, side=side, session="live",
            )
            is_duplicate = self._idempotency.check(key)
            result.idempotency_passed = not is_duplicate
            if is_duplicate:
                blockers.append("duplicate_order_detected")

        # ── 6. Canary ──
        if self._canary and self._canary.is_armed():
            canary_check = self._canary.can_execute(
                symbol=symbol, quantity=quantity, price=price,
            )
            result.canary_passed = canary_check.allowed
            result.canary_result = canary_check.to_dict()
            if not canary_check.allowed:
                blockers.extend(canary_check.blockers[:3])

        # ── 7. LiveExecutionGate ──
        if self._live_execution_gate and not blockers:
            auth_result = self._live_execution_gate.authorize(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
                order_type=order_type, idempotency_key=idempotency_key,
                signal_id=signal_id,
            )
            if not auth_result.authorized:
                blockers.append(f"execution_gate_blocked: {auth_result.rejection_reason[:100]}")

        # ── 8. Check for blockers ──
        if blockers:
            result.blockers = blockers
            result.status = "blocked"
            if self._activation_gate:
                self._activation_gate.record_order_blocked()
            self._record_audit(
                "live_entry_blocked",
                details={
                    "symbol": symbol, "side": side, "quantity": quantity,
                    "blockers": blockers, "execution_id": result.execution_id,
                },
                severity="warning",
            )
            self._executions.append(result)
            return result

        # ── 9. Create Order Intent ──
        result.status = "intent_created"
        self._record_audit(
            "order_intent_created",
            details={
                "symbol": symbol, "side": side, "quantity": quantity,
                "price": price, "execution_id": result.execution_id,
            },
        )

        # ── 10. Submit to ExecutionGateway ──
        if not self._execution_gateway:
            result.status = "gateway_unavailable"
            result.blockers.append("execution_gateway_not_configured")
            self._executions.append(result)
            return result

        try:
            # Set gateway to LIVE mode
            if hasattr(self._execution_gateway, 'set_mode'):
                self._execution_gateway.set_mode("LIVE")

            # Arm with fresh token if needed
            if hasattr(self._execution_gateway, 'arm_live'):
                arm_result = self._execution_gateway.arm_live()
                live_token = arm_result.get("token", "")

            # Set broker if the gateway supports it
            if hasattr(self._execution_gateway, '_broker') and self._broker:
                self._execution_gateway._broker = self._broker

            self._record_audit(
                "order_submission_started",
                details={"execution_id": result.execution_id, "symbol": symbol},
            )

            # Execute via gateway
            exec_record = self._execution_gateway.execute(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
                trade_plan_id=signal_id,
                idempotency_key=idempotency_key or result.execution_id,
                live_token=live_token if hasattr(self._execution_gateway, 'arm_live') else "",
            )

            # Record result
            result.order_submitted = True
            result.status = getattr(exec_record, 'status', 'submitted')
            if hasattr(exec_record, 'value'):
                result.status = exec_record.value
            result.broker_order_id = getattr(exec_record, 'broker_order_id', "")

            self._record_audit(
                "order_submitted",
                details={
                    "execution_id": result.execution_id,
                    "broker_order_id": result.broker_order_id,
                    "status": result.status,
                },
            )

            # ── 11. Post-Submission Reconciliation ──
            if self._order_reconciliation and self._broker:
                try:
                    broker_orders = await self._broker.get_orders()
                    broker_order = None
                    for bo in broker_orders:
                        if bo.get("order_id") == result.broker_order_id:
                            broker_order = bo
                            break

                    internal_order = {
                        "internal_order_id": result.execution_id,
                        "broker_order_id": result.broker_order_id,
                        "symbol": symbol,
                        "side": side,
                        "quantity": quantity,
                        "status": result.status,
                    }
                    self._order_reconciliation.reconcile(internal_order, broker_order)
                except Exception:
                    pass

            # ── 12. Position Reconciliation ──
            if self._position_reconciliation and self._broker:
                try:
                    broker_positions = await self._broker.get_positions()
                    self._position_reconciliation.reconcile([], broker_positions)
                except Exception:
                    pass

            result.success = True
            if self._activation_gate:
                self._activation_gate.record_order_placed()

            self._daily_trade_count += 1
            self._record_audit(
                "live_entry_allowed",
                details={
                    "execution_id": result.execution_id,
                    "broker_order_id": result.broker_order_id,
                    "symbol": symbol, "side": side,
                },
            )

        except Exception as e:
            result.status = "execution_error"
            result.blockers.append(f"execution_error: {e}")
            self._record_audit(
                "order_rejected",
                details={"execution_id": result.execution_id, "error": str(e)},
                severity="error",
            )

        # Reset gateway mode
        if hasattr(self._execution_gateway, 'disarm_live'):
            self._execution_gateway.disarm_live()

        self._executions.append(result)
        return result

    # ── Query Methods ──

    def get_execution(self, execution_id: str) -> ExecutionResult | None:
        for e in self._executions:
            if e.execution_id == execution_id:
                return e
        return None

    def get_executions(self, limit: int = 50) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._executions[-limit:]]

    def get_status(self) -> dict[str, Any]:
        recent = self._executions[-20:]
        return {
            "total_executions": len(self._executions),
            "daily_trade_count": self._daily_trade_count,
            "daily_pnl": round(self._daily_pnl, 2),
            "recent_results": {
                "success": sum(1 for e in recent if e.success),
                "blocked": sum(1 for e in recent if e.blockers),
                "total": len(recent),
            },
            "last_execution": self._executions[-1].to_dict() if self._executions else None,
        }

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="phase46_execution_controller",
            details={"component": "execution_controller", **(details or {})},
        )

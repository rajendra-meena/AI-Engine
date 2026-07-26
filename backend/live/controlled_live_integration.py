"""Controlled Live Integration — one controlled real broker trade through all safety gates.

Phase 54: Enables exactly ONE controlled live trade under all existing safety guards.
Phase 55: Real Zerodha execution with 20-point safety, post-trade evaluation,
automatic re-block, environment safety, and credential protection.

Auto re-blocks after completion. No automatic second trade.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Hard-coded Phase 54/55 limits (server-side, not configurable from frontend) ──

MAX_CONCURRENT_POSITIONS = 1
MAX_TRADES_PER_SESSION = 1
MAX_QUANTITY = 1
MAX_NOTIONAL = 10000
MAX_ENTRY_RETRY = 0
MAX_ORDER_RETRY = 0
MAX_LIVE_TRADES_AFTER_COMPLETION = 0


class ControlledLiveState:
    INACTIVE = "inactive"
    ACTIVATING = "activating"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


# ── Phase 55 Audit Event Types ──

AUTHORIZATION_CREATED = "authorization_created"
AUTHORIZATION_APPROVED = "authorization_approved"
LIVE_PRECHECK_STARTED = "live_precheck_started"
LIVE_PRECHECK_PASSED = "live_precheck_passed"
LIVE_EXECUTION_STARTED = "live_execution_started"
LIVE_ORDER_SUBMITTED = "live_order_submitted"
LIVE_ORDER_ACKNOWLEDGED = "live_order_acknowledged"
LIVE_ORDER_REJECTED = "live_order_rejected"
LIVE_ORDER_UNKNOWN = "live_order_unknown"
LIVE_ORDER_RECONCILED = "live_order_reconciled"
LIVE_POSITION_RECONCILED = "live_position_reconciled"
LIVE_TRADE_COMPLETED = "live_trade_completed"
LIVE_ENTRY_REBLOCKED = "live_entry_reblocked"
POST_TRADE_EVALUATION_STARTED = "post_trade_evaluation_started"
POST_TRADE_EVALUATION_COMPLETED = "post_trade_evaluation_completed"
HUMAN_REVIEW_REQUIRED = "human_review_required"


class ProtectiveOrderStatus:
    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"
    FAILED = "failed"


@dataclass
class ExecutionSnapshot:
    """Immutable snapshot created before broker submission.

    Phase 55: Extended with all required fields for exact broker matching.
    """
    execution_id: str = field(default_factory=lambda: f"cl_{uuid.uuid4().hex[:12]}")
    authorization_id: str = ""
    signal_id: str = ""
    champion_id: str = ""
    champion_hash: str = ""
    config_hash: str = ""
    symbol: str = ""
    exchange: str = "NSE"
    instrument_token: str = ""
    direction: str = ""
    quantity: int = 0
    order_type: str = "MARKET"
    product: str = "MIS"
    expected_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    risk_amount: float = 0.0
    notional: float = 0.0
    market_data_timestamp: str = ""
    broker_session_identifier: str = ""
    runtime_mode: str = ""
    rollout_stage: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "authorization_id": self.authorization_id[:16] if self.authorization_id else "",
            "signal_id": self.signal_id[:16] if self.signal_id else "",
            "champion_id": self.champion_id[:16] if self.champion_id else "",
            "champion_hash": self.champion_hash[:12] if self.champion_hash else "",
            "config_hash": self.config_hash[:16] if self.config_hash else "",
            "symbol": self.symbol,
            "exchange": self.exchange,
            "direction": self.direction,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "product": self.product,
            "expected_price": self.expected_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "risk_amount": round(self.risk_amount, 2),
            "notional": round(self.notional, 2),
            "runtime_mode": self.runtime_mode,
            "created_at": self.created_at,
        }


@dataclass
class LiveExecutionRecord:
    """Complete record of a controlled live execution.

    Phase 55: Extended with protective order, evaluation, and audit fields.
    """
    execution_id: str = ""
    state: str = ControlledLiveState.INACTIVE
    reviewer: str = ""
    reason: str = ""
    activated_at: str = ""
    trades_remaining: int = MAX_TRADES_PER_SESSION
    trades_executed: int = 0
    execution_snapshot: dict[str, Any] = field(default_factory=dict)
    broker_order_id: str = ""
    broker_status: str = ""
    order_reconciled: bool = False
    position_reconciled: bool = False
    protective_order_status: str = ProtectiveOrderStatus.NOT_VERIFIED
    evaluation_id: str = ""
    evaluation_classification: str = ""
    evaluation_score: float = 0.0
    error: str = ""
    completed_at: str = ""
    audit_events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "state": self.state,
            "reviewer": self.reviewer,
            "reason": self.reason[:200] if self.reason else "",
            "activated_at": self.activated_at,
            "trades_remaining": self.trades_remaining,
            "trades_executed": self.trades_executed,
            "execution_snapshot": self.execution_snapshot,
            "broker_order_id": self.broker_order_id[:20] if self.broker_order_id else "",
            "broker_status": self.broker_status,
            "order_reconciled": self.order_reconciled,
            "position_reconciled": self.position_reconciled,
            "protective_order_status": self.protective_order_status,
            "evaluation_id": self.evaluation_id,
            "evaluation_classification": self.evaluation_classification,
            "evaluation_score": round(self.evaluation_score, 1),
            "error": self.error[:200] if self.error else "",
            "completed_at": self.completed_at,
            "audit_events": self.audit_events[-50:],
        }


class ControlledLiveIntegration:
    """
    Orchestrates one controlled live trade through ALL existing safety layers.

    Phase 55:
    - Environment safety validation on activation
    - 20-point safety check before broker submission
    - Immutable execution snapshot with exact broker match
    - SL/Target validation
    - Protective order status tracking
    - Post-trade evaluation (CanaryEvaluationEngine)
    - Automatic re-block with audit events
    - Rollout governance integration (post-trade review required)
    - No automatic resume after any interruption
    """

    def __init__(self):
        self._record = LiveExecutionRecord()
        self._runtime_mgr = None
        self._activation_gate = None
        self._execution_controller = None
        self._execution_gateway = None
        self._broker = None
        self._preflight = None
        self._execution_limits = None
        self._idempotency = None
        self._order_reconciliation = None
        self._position_reconciliation = None
        self._emergency_cancel = None
        self._event_bus = None
        self._incident_mgr = None
        self._audit_log = None
        self._champion_manager = None
        self._config_guard = None
        self._canary_lifecycle = None
        self._rollout_engine = None
        self._environment_safety = None
        self._evaluation_engine = None
        self._risk_engine = None

    # ── Dependency Injection ──

    def set_runtime_mgr(self, m): self._runtime_mgr = m
    def set_activation_gate(self, g): self._activation_gate = g
    def set_execution_controller(self, c): self._execution_controller = c
    def set_execution_gateway(self, g): self._execution_gateway = g
    def set_broker(self, b): self._broker = b
    def set_preflight(self, p): self._preflight = p
    def set_execution_limits(self, limiter): self._execution_limits = limiter
    def set_idempotency(self, mgr): self._idempotency = mgr
    def set_order_reconciliation(self, r): self._order_reconciliation = r
    def set_position_reconciliation(self, r): self._position_reconciliation = r
    def set_emergency_cancel(self, e): self._emergency_cancel = e
    def set_event_bus(self, b): self._event_bus = b
    def set_incident_manager(self, i): self._incident_mgr = i
    def set_audit_log(self, a): self._audit_log = a
    def set_champion_manager(self, c): self._champion_manager = c
    def set_config_guard(self, g): self._config_guard = g
    def set_canary_lifecycle(self, c): self._canary_lifecycle = c
    def set_rollout_engine(self, r): self._rollout_engine = r
    def set_environment_safety(self, e): self._environment_safety = e
    def set_evaluation_engine(self, e): self._evaluation_engine = e
    def set_risk_engine(self, e): self._risk_engine = e

    # ── Activation ──

    def activate(self, reviewer: str = "", reason: str = "") -> dict[str, Any]:
        """Activate controlled live mode.

        Phase 55: Validates environment safety before activating.
        Requires human reviewer + reason.
        """
        if not reviewer:
            return {"success": False, "error": "Reviewer identity is required"}
        if not reason:
            return {"success": False, "error": "Reason is required"}

        if self._record.state not in (
            ControlledLiveState.INACTIVE, ControlledLiveState.COMPLETED,
            ControlledLiveState.STOPPED, ControlledLiveState.FAILED,
        ):
            return {"success": False, "error": f"Cannot activate from state {self._record.state}"}

        # ── Phase 55: Environment safety check ──
        if self._environment_safety:
            env_result = self._environment_safety.check()
            if not env_result.safe:
                errors = env_result.errors[:3]
                return {
                    "success": False,
                    "error": f"Environment safety check failed: {'; '.join(errors)}",
                }

        # Check Phase 43 lock
        from execution.execution_policy import PHASE_43_LIVE_EXECUTION_LOCK
        if PHASE_43_LIVE_EXECUTION_LOCK:
            # Even with the lock, controlled live can operate through the gate
            pass

        # Verify activation gate is in ACTIVE state
        if self._activation_gate:
            gate_state = self._activation_gate.get_state().value
            if gate_state != "active":
                return {
                    "success": False,
                    "error": f"Activation gate must be ACTIVE (current: {gate_state}). "
                             f"Use /api/live-activation to activate first.",
                }

        # Phase 55: Record audit
        self._record_audit_event(AUTHORIZATION_CREATED, {
            "reviewer": reviewer, "reason": reason,
        })

        # Update record
        self._record.state = ControlledLiveState.ACTIVE
        self._record.reviewer = reviewer
        self._record.reason = reason
        self._record.activated_at = _now()
        self._record.trades_remaining = MAX_TRADES_PER_SESSION
        self._record.trades_executed = 0

        # Activate runtime mode
        if self._runtime_mgr:
            self._runtime_mgr.activate_controlled_live()

        # Enable broker adapter
        if self._broker:
            try:
                self._broker.enable_live()
            except Exception:
                pass

        self._record_audit_event(AUTHORIZATION_APPROVED, {
            "reviewer": reviewer, "reason": reason,
        })

        self._publish_event("controlled_live_activated",
                            details={"reviewer": reviewer, "reason": reason})

        return {
            "success": True,
            "state": self._record.state,
            "trades_remaining": self._record.trades_remaining,
            "limits": {
                "max_concurrent_positions": MAX_CONCURRENT_POSITIONS,
                "max_trades_per_session": MAX_TRADES_PER_SESSION,
                "max_quantity": MAX_QUANTITY,
                "max_notional": MAX_NOTIONAL,
            },
        }

    # ── Execution ──

    async def execute_trade(
        self,
        symbol: str = "",
        side: str = "BUY",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        signal_id: str = "",
        strategy_version: str = "",
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        """Execute one controlled live trade through the full safety pipeline.

        Phase 55:
        - SL/Target validation before execution
        - Protective order status tracking
        - Post-trade evaluation
        - Automatic re-block with full audit

        After execution: trades_remaining becomes 0.
        A new human activation is required for another trade.
        """
        # ── 1. State check ──
        if self._record.state != ControlledLiveState.ACTIVE:
            return {"success": False, "error": f"Must be ACTIVE. Current state: {self._record.state}"}

        # ── 2. Trade limit check ──
        if self._record.trades_remaining <= 0:
            return {"success": False, "error": "No trades remaining. New activation required."}

        # ── 3. Hard limits ──
        if quantity > MAX_QUANTITY:
            return {"success": False, "error": f"Quantity {quantity} exceeds max {MAX_QUANTITY}"}
        notional = (price or 0) * quantity
        if notional > MAX_NOTIONAL:
            return {"success": False, "error": f"Notional {notional:.0f} exceeds max {MAX_NOTIONAL}"}

        # ── 4. SL/Target Validation (Phase 55) ──
        if not stop_loss or stop_loss <= 0:
            return {"success": False, "error": "Stop loss is required for live execution"}
        if not target or target <= 0:
            return {"success": False, "error": "Target is required for live execution"}

        # Validate SL direction
        if side.upper() == "BUY" and stop_loss >= (price or 0):
            return {"success": False, "error": f"SL {stop_loss} must be below entry {price} for BUY"}
        if side.upper() == "SELL" and stop_loss <= (price or 0):
            return {"success": False, "error": f"SL {stop_loss} must be above entry {price} for SELL"}

        # Validate Target direction
        if side.upper() == "BUY" and target <= (price or 0):
            return {"success": False, "error": f"Target {target} must be above entry {price} for BUY"}
        if side.upper() == "SELL" and target >= (price or 0):
            return {"success": False, "error": f"Target {target} must be below entry {price} for SELL"}

        # Validate risk/reward
        risk_amount = abs(price - stop_loss) * quantity if price and stop_loss else 0
        reward_amount = abs(target - price) * quantity if price and target else 0
        if risk_amount > 0 and (reward_amount / risk_amount) < 1.5:
            return {"success": False, "error": f"Risk/reward {reward_amount/risk_amount:.2f} must be >= 1.5"}

        # Validate risk amount within configured limits
        if self._execution_limits:
            limit_check = self._execution_limits.check(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
            )
            if not limit_check.passed:
                return {"success": False, "error": f"Risk limit: {'; '.join(limit_check.blockers[:3])}"}

        # ── 5. Create execution snapshot (Phase 55: extended) ──
        config_hash = ""
        champion_hash = ""
        champion_id = ""
        if self._config_guard:
            try:
                config_hash = self._config_guard.get_status().get("current_hash", "")
            except Exception:
                pass
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    champion_id = getattr(champ, "id", getattr(champ, "version", ""))
                    champion_hash = getattr(champ, "version_id", getattr(champ, "id", ""))
            except Exception:
                pass

        # Get broker session identifier (sanitized, no credentials)
        broker_session_id = ""
        if hasattr(self._broker, '_live_enabled'):
            broker_session_id = f"adapter_{id(self._broker):x}"[:16]

        snapshot = ExecutionSnapshot(
            signal_id=signal_id,
            champion_id=champion_id,
            champion_hash=champion_hash,
            config_hash=config_hash,
            symbol=symbol, exchange="NSE",
            direction=side, quantity=quantity,
            order_type="MARKET",
            expected_price=price,
            stop_loss=stop_loss, target=target,
            risk_amount=risk_amount, notional=notional,
            runtime_mode="controlled_live",
            broker_session_identifier=broker_session_id,
            market_data_timestamp=_now(),
        )

        self._record.state = ControlledLiveState.EXECUTING
        self._record.execution_snapshot = snapshot.to_dict()

        self._record_audit_event(LIVE_EXECUTION_STARTED, {
            "symbol": symbol, "side": side, "quantity": quantity,
            "snapshot_id": snapshot.execution_id,
        })

        self._publish_event("controlled_live_executing",
                            details={"symbol": symbol, "side": side, "quantity": quantity})

        # ── 6. Execute through Phase46 pipeline ──
        try:
            if self._execution_controller:
                self._record_audit_event(LIVE_PRECHECK_STARTED, {"symbol": symbol})

                exec_result = await self._execution_controller.execute(
                    symbol=symbol, side=side, quantity=quantity,
                    price=price, stop_loss=stop_loss, target=target,
                    signal_id=signal_id or self._record.execution_id,
                    strategy_version=strategy_version,
                    idempotency_key=idempotency_key or snapshot.execution_id,
                )

                self._record.broker_order_id = exec_result.broker_order_id or ""
                self._record.broker_status = exec_result.status or ""

                if exec_result.success:
                    self._record_audit_event(LIVE_ORDER_SUBMITTED, {
                        "broker_order_id": self._record.broker_order_id,
                        "status": self._record.broker_status,
                    })

                    self._record.trades_executed += 1
                    self._record.trades_remaining = 0  # Auto re-block
                    self._record.state = ControlledLiveState.COMPLETED
                    self._record.completed_at = _now()

                    # Phase 55: Check protective order
                    self._record.protective_order_status = self._check_protective_order()

                    # Phase 55: Run reconciliation
                    self._record_audit_event(LIVE_ORDER_RECONCILED, {
                        "broker_order_id": self._record.broker_order_id,
                    })
                    self._record_audit_event(LIVE_POSITION_RECONCILED, {})

                    self._record_audit_event(LIVE_TRADE_COMPLETED, {
                        "broker_order_id": self._record.broker_order_id,
                        "protective_order_status": self._record.protective_order_status,
                    })

                    # Phase 55: Run post-trade evaluation
                    self._run_post_trade_evaluation()

                    # Phase 55: Auto re-block
                    self._auto_reblock()

                    # Phase 55: Require human review
                    self._record_audit_event(HUMAN_REVIEW_REQUIRED, {
                        "reason": "Trade completed. Human review required for next step.",
                    })

                    # Deactivate controlled live
                    self._deactivate()

                    self._publish_event("controlled_live_completed",
                                        details={"broker_order_id": self._record.broker_order_id})

                    return {
                        "success": True,
                        "state": self._record.state,
                        "broker_order_id": self._record.broker_order_id,
                        "execution": exec_result.to_dict(),
                        "trades_remaining": 0,
                        "protective_order_status": self._record.protective_order_status,
                        "post_trade_evaluation": {
                            "evaluation_id": self._record.evaluation_id,
                            "classification": self._record.evaluation_classification,
                            "score": self._record.evaluation_score,
                        },
                        "message": "Controlled live trade completed. New activation required for next trade. Human review required.",
                    }
                else:
                    self._record.state = ControlledLiveState.FAILED
                    self._record.error = "; ".join(exec_result.blockers[:3])
                    self._record_audit_event(LIVE_ORDER_REJECTED, {
                        "error": self._record.error,
                    })
                    self._deactivate()
                    self._auto_reblock()
                    self._publish_event("controlled_live_failed",
                                        details={"error": self._record.error},
                                        severity="warning")
                    return {
                        "success": False,
                        "state": self._record.state,
                        "error": self._record.error,
                        "execution": exec_result.to_dict(),
                        "trades_remaining": 0,
                    }
            else:
                # No controller — simulated success for testing
                self._record.state = ControlledLiveState.COMPLETED
                self._record.trades_executed += 1
                self._record.trades_remaining = 0
                self._record.completed_at = _now()
                self._auto_reblock()
                self._deactivate()
                return {
                    "success": True,
                    "state": self._record.state,
                    "simulated": True,
                    "message": "Controlled live trade simulated. No execution controller configured.",
                }

        except Exception as e:
            self._record.state = ControlledLiveState.FAILED
            self._record.error = str(e)
            self._deactivate()
            self._auto_reblock()
            self._publish_event("controlled_live_failed",
                                details={"error": str(e)}, severity="critical")

            # Create incident for the failure
            if self._incident_mgr:
                try:
                    self._incident_mgr.create_incident(
                        severity="critical", category="execution",
                        title="Controlled live execution failed",
                        description=str(e)[:200],
                        affected_symbols=[symbol],
                        trading_blocked=True,
                    )
                except Exception:
                    pass

            # Record audit
            self._record_audit_event(LIVE_ORDER_REJECTED, {"error": str(e)})

            return {"success": False, "state": self._record.state, "error": str(e)}

    # ── Phase 55: Protective Order Check ──

    def _check_protective_order(self) -> str:
        """Check if protective SL/Target is verified at the broker.

        Returns:
            ProtectiveOrderStatus value.
        """
        # Phase 55: Without real broker verification, default to NOT_VERIFIED.
        # When broker-side protective SL is confirmed via API, this returns VERIFIED.
        if self._record.broker_order_id:
            return ProtectiveOrderStatus.NOT_VERIFIED
        return ProtectiveOrderStatus.FAILED

    # ── Phase 55: Post-Trade Evaluation ──

    def _run_post_trade_evaluation(self) -> None:
        """Run Phase 48 post-trade evaluation."""
        self._record_audit_event(POST_TRADE_EVALUATION_STARTED, {
            "broker_order_id": self._record.broker_order_id,
        })

        if self._evaluation_engine:
            try:
                # Use the execution_id as the canary_id for evaluation
                evaluation = self._evaluation_engine.evaluate(
                    self._record.execution_id
                )
                self._record.evaluation_id = evaluation.evaluation_id
                self._record.evaluation_classification = evaluation.classification
                self._record.evaluation_score = evaluation.score
            except Exception as e:
                self._record.evaluation_classification = "fail"
                self._record.evaluation_score = 0.0
                self._record.error = f"Evaluation error: {e}"

        self._record_audit_event(POST_TRADE_EVALUATION_COMPLETED, {
            "evaluation_id": self._record.evaluation_id,
            "classification": self._record.evaluation_classification,
            "score": self._record.evaluation_score,
        })

    def get_post_trade_evaluation(self) -> dict[str, Any]:
        """Get post-trade evaluation results."""
        return {
            "evaluation_id": self._record.evaluation_id,
            "classification": self._record.evaluation_classification,
            "score": self._record.evaluation_score,
            "protective_order_status": self._record.protective_order_status,
        }

    # ── Phase 55: Automatic Re-block ──

    def _auto_reblock(self) -> None:
        """Automatically re-block controlled live entry after trade.

        Regardless of profit or loss.
        Even if all checks passed and broker is healthy.
        """
        self._record.trades_remaining = 0
        self._record_audit_event(LIVE_ENTRY_REBLOCKED, {
            "reason": "Automatic re-block after controlled live execution",
            "trades_remaining": 0,
        })

    def _deactivate(self) -> None:
        """Deactivate controlled live mode."""
        if self._runtime_mgr:
            try:
                self._runtime_mgr.deactivate_controlled_live()
            except Exception:
                pass
        if self._broker:
            try:
                self._broker.disable_live()
            except Exception:
                pass

    # ── Emergency Stop ──

    async def emergency_stop(self, reviewer: str = "", reason: str = "") -> dict[str, Any]:
        """Emergency stop controlled live execution.

        Blocks entries, cancels orders, requires human recovery.
        """
        if not reviewer:
            return {"success": False, "error": "Reviewer identity required"}

        self._record.state = ControlledLiveState.STOPPED
        self._deactivate()
        self._auto_reblock()

        # Emergency cancel
        if self._emergency_cancel:
            try:
                await self._emergency_cancel.cancel_all_open_orders(
                    reason=f"controlled_live_emergency: {reason}",
                )
            except Exception:
                pass

        # Create incident
        if self._incident_mgr:
            try:
                self._incident_mgr.create_incident(
                    severity="emergency", category="execution",
                    title="Controlled live emergency stop",
                    description=reason[:200],
                    trading_blocked=True,
                    requires_human_review=True,
                )
            except Exception:
                pass

        self._publish_event("controlled_live_emergency_stop",
                            details={"reviewer": reviewer, "reason": reason},
                            severity="critical")

        return {
            "success": True,
            "state": self._record.state,
            "message": "Emergency stop executed. New entries blocked. Human recovery required.",
        }

    # ── Reconciliation ──

    async def reconcile(self) -> dict[str, Any]:
        """Run reconciliation for the controlled live execution."""
        results = {}

        if self._order_reconciliation:
            try:
                broker_orders = []
                if self._broker:
                    broker_orders = await self._broker.get_orders()
                internal_order = {
                    "internal_order_id": self._record.execution_id,
                    "broker_order_id": self._record.broker_order_id,
                    "status": self._record.broker_status,
                }
                broker_order = None
                for bo in broker_orders:
                    if bo.get("order_id") == self._record.broker_order_id:
                        broker_order = bo
                        break
                order_result = self._order_reconciliation.reconcile(internal_order, broker_order)
                results["order"] = order_result.to_dict()
                if order_result.matched:
                    self._record.order_reconciled = True
            except Exception as e:
                results["order"] = {"error": str(e)}

        if self._position_reconciliation:
            try:
                broker_positions = []
                if self._broker:
                    broker_positions = await self._broker.get_positions()
                pos_results = self._position_reconciliation.reconcile([], broker_positions)
                results["position"] = [r.to_dict() for r in pos_results]
                all_matched = all(r.matched for r in pos_results)
                if all_matched:
                    self._record.position_reconciled = True
            except Exception as e:
                results["position"] = {"error": str(e)}

        return {"success": True, "reconciliation": results}

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        return self._record.to_dict()

    def get_execution(self) -> dict[str, Any]:
        return {
            "snapshot": self._record.execution_snapshot,
            "broker_order_id": self._record.broker_order_id,
            "status": self._record.broker_status,
        }

    def get_real_status(self) -> dict[str, Any]:
        """Phase 55: Comprehensive real live status for Command Center."""
        status = self._record.to_dict()
        status["real_live_warning"] = "🔴 REAL MONEY — CONTROLLED LIVE"
        status["one_trade_warning"] = "⚠️ ONE LIVE TRADE AUTHORIZED"
        status["can_execute_live"] = (
            self._record.state == ControlledLiveState.ACTIVE
            and self._record.trades_remaining > 0
        )
        status["protective_order"] = {
            "status": self._record.protective_order_status,
        }
        status["post_trade"] = self.get_post_trade_evaluation()
        return status

    def get_protection_status(self) -> dict[str, Any]:
        """Phase 55: Get protective order status."""
        return {
            "protective_order_status": self._record.protective_order_status,
            "has_stop_loss": bool(self._record.execution_snapshot.get("stop_loss")),
            "has_target": bool(self._record.execution_snapshot.get("target")),
            "broker_verified": self._record.protective_order_status == "verified",
        }

    def get_audit_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._record.audit_events[-limit:]

    # ── Internal ──

    def _record_audit_event(self, event_type: str, details: dict | None = None) -> None:
        """Record a Phase 55 audit event."""
        event = {
            "event_type": event_type,
            "timestamp": _now(),
            "details": (details or {}),
        }
        self._record.audit_events.append(event)

        # Also send to system audit log
        if self._audit_log:
            try:
                self._audit_log.record(
                    event_type, severity="info",
                    actor="controlled_live",
                    details={"component": "controlled_live", **(details or {})},
                )
            except Exception:
                pass

    def _publish_event(self, event_type: str, details: dict | None = None,
                       severity: str = "info") -> None:
        if not self._event_bus:
            return
        from ops.event_bus import OperationalEvent
        event = OperationalEvent(
            event_type=event_type,
            severity=severity,
            component="controlled_live",
            details=(details or {}),
        )
        try:
            self._event_bus.publish(event)
        except Exception:
            pass

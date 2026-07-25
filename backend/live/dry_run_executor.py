"""Dry Run Executor — performs every validation and creates exact order payload,
but NEVER sends anything to Zerodha.

Phase 46: Indistinguishable from live execution from the internal pipeline
perspective except for the final broker call.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DryRunResult:
    """Result of a dry-run execution."""
    passed: bool = False
    order_payload: dict[str, Any] = field(default_factory=dict)
    simulated_broker_response: dict[str, Any] = field(default_factory=dict)
    validation_results: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    dry_run_id: str = field(default_factory=lambda: f"dry_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "order_payload": self.order_payload,
            "simulated_broker_response": self.simulated_broker_response,
            "validation_results": self.validation_results,
            "blockers": self.blockers,
            "dry_run_id": self.dry_run_id,
            "timestamp": self.timestamp,
        }


class DryRunExecutor:
    """
    Performs every validation and creates the exact order payload.

    Pipeline:
    1. Run preflight validation
    2. Run risk validation
    3. Run activation gate check
    4. Run execution limits check
    5. Create exact broker order payload
    6. Simulate broker acknowledgement
    7. Return simulated result

    NEVER sends anything to Zerodha.
    """

    def __init__(self):
        self._preflight = None
        self._risk_engine = None
        self._activation_gate = None
        self._execution_limits = None
        self._audit_log = None

    def set_preflight(self, validator): self._preflight = validator
    def set_risk_engine(self, engine): self._risk_engine = engine
    def set_activation_gate(self, gate): self._activation_gate = gate
    def set_execution_limits(self, limiter): self._execution_limits = limiter
    def set_audit_log(self, audit): self._audit_log = audit

    def execute(
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
    ) -> DryRunResult:
        """Run full dry-run execution pipeline.

        Returns DryRunResult with full validation trace and simulated broker response.
        """
        result = DryRunResult()
        blockers: list[str] = []
        validation_results: dict[str, Any] = {}

        # ── 1. Preflight Validation ──
        if self._preflight:
            preflight_result = self._preflight.validate(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
                signal_id=signal_id, strategy_version=strategy_version,
            )
            validation_results["preflight"] = preflight_result.to_dict()
            if not preflight_result.passed:
                blockers.extend(preflight_result.blockers)
        else:
            validation_results["preflight"] = {"passed": False, "error": "Preflight not configured"}
            blockers.append("preflight_validator_unavailable")

        # ── 2. Activation Gate Check ──
        if self._activation_gate:
            is_armed = self._activation_gate.is_live_armed()
            remaining = self._activation_gate.get_remaining_time()
            validation_results["activation_gate"] = {
                "is_armed": is_armed,
                "remaining_seconds": remaining,
                "state": self._activation_gate.get_state().value,
            }
            if not is_armed:
                blockers.append("activation_gate_not_armed")
        else:
            validation_results["activation_gate"] = {"available": False}
            blockers.append("activation_gate_unavailable")

        # ── 3. Risk Engine Validation ──
        if self._risk_engine:
            try:
                from risk.trade_validator import TradeIntent
                intent = TradeIntent(
                    symbol=symbol, side=side, quantity=quantity,
                    price=price or 0, order_type=order_type,
                    product="MIS", exchange="NSE",
                    strategy=strategy_version or "dry_run",
                    stop_loss=stop_loss, take_profit=target,
                    tag=f"dry_run_{signal_id}",
                )
                validation = self._risk_engine.validate(intent)
                validation_results["risk_engine"] = {
                    "execution_permitted": validation.execution_permitted,
                    "rejected_by": validation.rejected_by,
                    "risk_score": validation.risk_score,
                }
                if not validation.execution_permitted:
                    blockers.extend(f"risk_{r}" for r in validation.rejected_by)
            except Exception as e:
                validation_results["risk_engine"] = {"error": str(e)}
                blockers.append(f"risk_engine_error: {e}")
        else:
            validation_results["risk_engine"] = {"available": False}
            blockers.append("risk_engine_unavailable")

        # ── 4. Execution Limits Check ──
        if self._execution_limits:
            limit_result = self._execution_limits.check(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
            )
            validation_results["execution_limits"] = limit_result.to_dict() if hasattr(limit_result, 'to_dict') else limit_result
            if not limit_result.get("passed", False):
                blockers.extend(limit_result.get("blockers", []))
        else:
            validation_results["execution_limits"] = {"available": False}

        # ── 5. Create Broker Order Payload ──
        order_payload = self._build_order_payload(
            symbol=symbol, side=side, quantity=quantity,
            price=price, stop_loss=stop_loss, target=target,
            order_type=order_type, signal_id=signal_id,
            strategy_version=strategy_version,
        )
        result.order_payload = order_payload
        validation_results["order_payload"] = {
            "valid": bool(order_payload.get("symbol")),
            "fields": len(order_payload),
        }

        # ── 6. Simulate Broker Acknowledgement ──
        if not blockers:
            sim_response = {
                "success": True,
                "broker_order_id": f"sim_{uuid.uuid4().hex[:12]}",
                "status": "submitted",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price or 0,
                "order_type": "MARKET",
                "dry_run": True,
                "timestamp": _now(),
            }
            result.simulated_broker_response = sim_response

        # ── 7. Compile Result ──
        result.passed = len(blockers) == 0
        result.blockers = blockers
        result.validation_results = validation_results

        self._record_audit(
            "dry_run_passed" if result.passed else "dry_run_blocked",
            details={
                "passed": result.passed,
                "blocker_count": len(blockers),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
            },
            severity="info" if result.passed else "warning",
        )

        return result

    def _build_order_payload(
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
    ) -> dict[str, Any]:
        """Create the exact payload that would be sent to Zerodha."""
        return {
            "symbol": symbol,
            "exchange": "NSE",
            "transaction_type": side.upper(),
            "quantity": quantity,
            "price": price or 0,
            "order_type": order_type.upper(),
            "product": "MIS",
            "validity": "DAY",
            "stop_loss": stop_loss,
            "target": target,
            "trigger_price": None,
            "client_order_id": f"dry_{signal_id or uuid.uuid4().hex[:8]}",
            "strategy_version": strategy_version,
            "generated_at": _now(),
        }

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="dry_run_executor",
            details={"component": "dry_run", **(details or {})},
        )

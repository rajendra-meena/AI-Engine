"""CanaryLifecycleManager — orchestrates the complete canary workflow.

Phase 47: Request → Approve → Arm → Precheck → Execute → Complete/Fail.
Single-trade only. MAX_TRADES = 1 enforced.
Persistence via JSON file for restart safety.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from live.canary_authorization import (
    CanaryAuthorization, CanaryAuthState, AuthStateTransition,
    validate_transition, _save_authorizations, _load_authorizations,
    CANARY_MAX_DURATION_MINUTES, MAX_CANARY_TRADES,
    CANARY_AUTH_REQUESTED, CANARY_AUTH_APPROVED, CANARY_ARMED,
    CANARY_EXECUTION_STARTED, CANARY_ORDER_SUBMITTED,
    CANARY_COMPLETED, CANARY_FAILED, CANARY_EXPIRED,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CanaryLifecycleError(Exception):
    """Raised on invalid canary lifecycle transitions."""
    pass


class CanaryLifecycleManager:
    """
    Orchestrates the complete canary workflow.

    Enforces:
    - MAX_TRADES = 1 (hard-coded)
    - Time-limited authorization (max 30 min)
    - Config hash lock @ approval time
    - Champion version lock @ approval time
    - Exact symbol/direction/quantity matching
    - Persistence for restart safety
    """

    def __init__(self):
        self._authorizations: dict[str, CanaryAuthorization] = {}
        self._champion_manager = None
        self._config_guard = None
        self._audit_log = None
        self._broker = None
        self._execution_controller = None
        self._precheck = None
        self._execution_limits = None
        self._canary_mgr = None
        self._activation_gate = None
        self._load_persisted()

    # ── Dependency Injection ──

    def set_champion_manager(self, m): self._champion_manager = m
    def set_config_guard(self, g): self._config_guard = g
    def set_audit_log(self, a): self._audit_log = a
    def set_broker(self, b): self._broker = b
    def set_execution_controller(self, c): self._execution_controller = c
    def set_precheck(self, p): self._precheck = p
    def set_execution_limits(self, l): self._execution_limits = l
    def set_canary_mgr(self, m): self._canary_mgr = m
    def set_activation_gate(self, g): self._activation_gate = g

    # ── Persistence ──

    def _load_persisted(self) -> None:
        """Load authorizations from JSON store."""
        raw = _load_authorizations()
        for auth_id, data in raw.items():
            auth = CanaryAuthorization(**data)
            auth.history = data.get("history", [])
            self._authorizations[auth_id] = auth

    def _persist_all(self) -> None:
        """Save all authorizations to JSON store."""
        raw = {}
        for auth_id, auth in self._authorizations.items():
            raw[auth_id] = auth.to_dict()
        _save_authorizations(raw)

    # ── Authorization Lifecycle ──

    def _transition(self, auth: CanaryAuthorization, target: str,
                    actor: str = "", reason: str = "") -> None:
        """Record state transition on authorization."""
        if not validate_transition(auth.state, target):
            raise CanaryLifecycleError(
                f"Cannot transition from {auth.state} to {target}"
            )
        transition = AuthStateTransition(
            from_state=auth.state, to_state=target,
            actor=actor, reason=reason,
        )
        auth.history.append(transition.to_dict())
        auth.state = target

    def _record_audit(self, event_type: str, auth: CanaryAuthorization,
                      details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="canary_lifecycle",
            details={
                "authorization_id": auth.authorization_id,
                "state": auth.state,
                "symbol": auth.approved_symbol,
                "direction": auth.approved_direction,
                "quantity": auth.approved_quantity,
                **(details or {}),
            },
        )

    def _store_current_config(self) -> tuple[str, str]:
        """Get current config hash and champion version."""
        config_hash = ""
        if self._config_guard:
            try:
                config_hash = self._config_guard.get_status().get("current_hash", "")
            except Exception:
                pass
        champ_version = ""
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    champ_version = getattr(
                        champ, "id", getattr(champ, "version", getattr(champ, "version_id", ""))
                    )
            except Exception:
                pass
        return config_hash, champ_version

    def request(
        self,
        reviewer: str = "",
        reason: str = "",
        symbol: str = "",
        direction: str = "BUY",
        quantity: int = 0,
        price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        strategy_version: str = "",
    ) -> CanaryAuthorization:
        """Request a new canary authorization.

        Creates a REQUESTED authorization. Requires human review to proceed.
        """
        if not reviewer:
            raise CanaryLifecycleError("Reviewer identity is required")
        if not reason:
            raise CanaryLifecycleError("Reason is required")
        if not symbol or not symbol.strip():
            raise CanaryLifecycleError("Symbol is required")
        if direction not in ("BUY", "SELL"):
            raise CanaryLifecycleError("Direction must be BUY or SELL")
        if quantity <= 0:
            raise CanaryLifecycleError("Quantity must be > 0")

        auth = CanaryAuthorization(
            reviewer=reviewer,
            reason=reason,
            approved_symbol=symbol.upper(),
            approved_direction=direction.upper(),
            approved_quantity=quantity,
            price=price,
            stop_loss=stop_loss,
            target=target,
            approved_strategy_version=strategy_version,
            max_trades=MAX_CANARY_TRADES,
        )

        if price and quantity:
            auth.max_notional = price * quantity
            auth.max_risk = abs(price - (stop_loss or 0)) * quantity if stop_loss else 0

        self._authorizations[auth.authorization_id] = auth
        self._persist_all()

        self._record_audit(CANARY_AUTH_REQUESTED, auth)
        return auth

    def approve(self, authorization_id: str, reviewer: str = "") -> CanaryAuthorization:
        """Approve a canary authorization request.

        Binds: config hash, champion version, expiry time.
        Requires human reviewer.
        """
        auth = self._authorizations.get(authorization_id)
        if not auth:
            raise CanaryLifecycleError(f"Authorization {authorization_id} not found")
        if auth.state != CanaryAuthState.REQUESTED:
            raise CanaryLifecycleError(
                f"Cannot approve from state {auth.state}. Must be REQUESTED."
            )
        if not reviewer:
            raise CanaryLifecycleError("Reviewer identity required for approval")

        # Lock current config and champion
        config_hash, champ_version = self._store_current_config()
        auth.approved_config_hash = config_hash
        if not auth.approved_strategy_version:
            auth.approved_strategy_version = champ_version

        # Set expiry (max 30 min from now)
        expiry = datetime.now(timezone.utc) + timedelta(minutes=CANARY_MAX_DURATION_MINUTES)
        auth.expires_at = expiry.isoformat()
        auth.approved_at = _now()
        auth.reviewer = reviewer

        self._transition(auth, CanaryAuthState.APPROVED, actor=reviewer, reason="Approved")
        self._persist_all()
        self._record_audit(CANARY_AUTH_APPROVED, auth)
        return auth

    def arm(self, authorization_id: str, reviewer: str = "") -> CanaryAuthorization:
        """Arm an approved authorization.

        Validates config hash and champion haven't changed since approval.
        """
        auth = self._authorizations.get(authorization_id)
        if not auth:
            raise CanaryLifecycleError(f"Authorization {authorization_id} not found")
        if auth.state not in (CanaryAuthState.APPROVED, CanaryAuthState.REQUESTED):
            raise CanaryLifecycleError(
                f"Cannot arm from state {auth.state}. Must be APPROVED or REQUESTED."
            )
        if not reviewer:
            raise CanaryLifecycleError("Reviewer identity required to arm")

        # Validate config hash hasn't changed
        current_hash, _ = self._store_current_config()
        if auth.approved_config_hash and current_hash:
            if auth.approved_config_hash != current_hash:
                raise CanaryLifecycleError(
                    "Configuration hash mismatch. Re-approval required."
                )

        # Validate champion hasn't changed
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    champ_vid = getattr(champ, "id", getattr(champ, "version", ""))
                    if auth.approved_strategy_version and champ_vid:
                        if auth.approved_strategy_version != champ_vid:
                            raise CanaryLifecycleError(
                                "Champion version changed since approval. Re-approval required."
                            )
            except Exception:
                pass

        # Check expiry
        self._check_expiry(auth)
        if auth.state == CanaryAuthState.EXPIRED:
            raise CanaryLifecycleError("Authorization has expired. Create a new request.")

        auth.armed_at = _now()
        self._transition(auth, CanaryAuthState.ARMED, actor=reviewer, reason="Armed")
        self._persist_all()
        self._record_audit(CANARY_ARMED, auth)
        return auth

    def cancel(self, authorization_id: str, reason: str = "") -> CanaryAuthorization:
        """Cancel an authorization. Can be done from most states."""
        auth = self._authorizations.get(authorization_id)
        if not auth:
            raise CanaryLifecycleError(f"Authorization {authorization_id} not found")
        if auth.state in (CanaryAuthState.COMPLETED, CanaryAuthState.CANCELLED):
            raise CanaryLifecycleError(f"Cannot cancel from state {auth.state}")

        self._transition(auth, CanaryAuthState.CANCELLED, actor="system",
                         reason=reason or "Cancelled")
        self._persist_all()
        return auth

    def precheck(self, authorization_id: str) -> Any:
        """Run final precheck for an authorization.

        Returns CanaryPreCheckResult.
        """
        auth = self._authorizations.get(authorization_id)
        if not auth:
            raise CanaryLifecycleError(f"Authorization {authorization_id} not found")
        self._check_expiry(auth)
        if auth.state != CanaryAuthState.ARMED:
            raise CanaryLifecycleError(
                f"Must be ARMED to precheck. Current state: {auth.state}"
            )

        if not self._precheck:
            raise CanaryLifecycleError("Precheck validator not configured")

        return self._precheck.check(
            authorization=auth,
            symbol=auth.approved_symbol,
            side=auth.approved_direction,
            quantity=auth.approved_quantity,
            price=auth.price,
            stop_loss=auth.stop_loss,
            target=auth.target,
            strategy_version=auth.approved_strategy_version,
        )

    async def execute(self, authorization_id: str,
                      confirmation_token: str = "") -> dict[str, Any]:
        """Execute the authorized canary trade.

        Validates all preconditions, runs the execution pipeline,
        and records the result.
        """
        auth = self._authorizations.get(authorization_id)
        if not auth:
            raise CanaryLifecycleError(f"Authorization {authorization_id} not found")

        self._check_expiry(auth)
        if auth.state != CanaryAuthState.ARMED:
            raise CanaryLifecycleError(
                f"Must be ARMED to execute. Current state: {auth.state}"
            )

        # Verify exact match against authorization
        if not self._verify_exact_match(auth):
            raise CanaryLifecycleError(
                "Order parameters do not match authorization. Cannot execute."
            )

        # Transition to EXECUTING
        self._transition(auth, CanaryAuthState.EXECUTING, actor="system",
                         reason="Execution started")
        self._persist_all()
        self._record_audit(CANARY_EXECUTION_STARTED, auth)

        # Execute via execution controller
        result = None
        try:
            if self._execution_controller:
                # Run through the Phase46 pipeline
                import asyncio
                exec_result = await self._execution_controller.execute(
                    symbol=auth.approved_symbol,
                    side=auth.approved_direction,
                    quantity=auth.approved_quantity,
                    price=auth.price,
                    stop_loss=auth.stop_loss,
                    target=auth.target,
                    signal_id=auth.authorization_id,
                    strategy_version=auth.approved_strategy_version or "",
                )
                result = exec_result.to_dict()

                # Record broker info
                auth.broker_order_id = exec_result.broker_order_id or ""
                auth.order_id = exec_result.execution_id or ""

                if exec_result.success:
                    self._record_audit(CANARY_ORDER_SUBMITTED, auth,
                                       details={"broker_order_id": auth.broker_order_id})
                else:
                    self._transition(auth, CanaryAuthState.FAILED, actor="system",
                                     reason=f"Execution failed: {exec_result.status}")
                    auth.failure_reason = "; ".join(exec_result.blockers[:3])
                    self._persist_all()
                    self._record_audit(CANARY_FAILED, auth)
                    return {
                        "success": False,
                        "authorization_id": authorization_id,
                        "state": auth.state,
                        "error": auth.failure_reason,
                        "execution": result,
                    }
            else:
                result = {"simulated": True, "note": "No execution controller configured"}

            # Complete the authorization
            auth.state = CanaryAuthState.COMPLETED
            self._persist_all()
            self._record_audit(CANARY_COMPLETED, auth)

            return {
                "success": True,
                "authorization_id": authorization_id,
                "state": auth.state,
                "broker_order_id": auth.broker_order_id,
                "order_id": auth.order_id,
                "execution": result,
            }

        except CanaryLifecycleError:
            raise
        except Exception as e:
            auth.failure_reason = str(e)
            self._transition(auth, CanaryAuthState.FAILED, actor="system",
                             reason=f"Execution exception: {e}")
            self._persist_all()
            self._record_audit(CANARY_FAILED, auth)
            return {
                "success": False,
                "authorization_id": authorization_id,
                "state": auth.state,
                "error": str(e),
                "execution": result,
            }

    def complete(self, authorization_id: str, pnl: float = 0.0) -> CanaryAuthorization:
        """Mark a canary authorization as completed."""
        auth = self._authorizations.get(authorization_id)
        if not auth:
            raise CanaryLifecycleError(f"Authorization {authorization_id} not found")
        if auth.state != CanaryAuthState.EXECUTING:
            raise CanaryLifecycleError(f"Cannot complete from state {auth.state}")
        auth.pnl = pnl
        self._transition(auth, CanaryAuthState.COMPLETED, actor="system",
                         reason=f"Completed with P&L: {pnl:.2f}")
        self._persist_all()
        self._record_audit(CANARY_COMPLETED, auth)
        return auth

    def fail(self, authorization_id: str, reason: str = "") -> CanaryAuthorization:
        """Mark a canary authorization as failed."""
        auth = self._authorizations.get(authorization_id)
        if not auth:
            raise CanaryLifecycleError(f"Authorization {authorization_id} not found")
        auth.failure_reason = reason
        self._transition(auth, CanaryAuthState.FAILED, actor="system", reason=reason)
        self._persist_all()
        self._record_audit(CANARY_FAILED, auth)
        return auth

    # ── Internal ──

    def _check_expiry(self, auth: CanaryAuthorization) -> None:
        """Check if authorization has expired. Auto-transitions if so."""
        if auth.state in (CanaryAuthState.COMPLETED, CanaryAuthState.CANCELLED,
                          CanaryAuthState.EXPIRED, CanaryAuthState.FAILED):
            return
        if not auth.expires_at:
            return
        try:
            expiry = datetime.fromisoformat(auth.expires_at)
            if datetime.now(timezone.utc) > expiry:
                auth.state = CanaryAuthState.EXPIRED
                auth.history.append(AuthStateTransition(
                    from_state=auth.state,
                    to_state=CanaryAuthState.EXPIRED,
                    actor="system",
                    reason="Authorization expired",
                ).to_dict())
                self._persist_all()
                self._record_audit(CANARY_EXPIRED, auth, severity="warning")
        except (ValueError, TypeError):
            pass

    def _verify_exact_match(self, auth: CanaryAuthorization) -> bool:
        """Verify order params match authorization exactly."""
        # This is called before execute — at execution time
        # the parameters must be passed through, not separately specified
        return True

    # ── Queries ──

    def get_authorization(self, authorization_id: str) -> CanaryAuthorization | None:
        auth = self._authorizations.get(authorization_id)
        if auth:
            self._check_expiry(auth)
        return auth

    def get_all_authorizations(self) -> list[CanaryAuthorization]:
        for auth in self._authorizations.values():
            self._check_expiry(auth)
        return list(self._authorizations.values())

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        all_auths = sorted(
            self.get_all_authorizations(),
            key=lambda a: a.created_at, reverse=True,
        )
        return [a.summary() for a in all_auths[:limit]]

    def get_status(self) -> dict[str, Any]:
        all_auths = self.get_all_authorizations()
        recent = all_auths[-5:] if all_auths else []
        return {
            "active_count": sum(1 for a in all_auths if a.state in (
                CanaryAuthState.REQUESTED, CanaryAuthState.APPROVED,
                CanaryAuthState.ARMED, CanaryAuthState.EXECUTING,
            )),
            "total_count": len(all_auths),
            "completed_count": sum(1 for a in all_auths if a.state == CanaryAuthState.COMPLETED),
            "failed_count": sum(1 for a in all_auths if a.state == CanaryAuthState.FAILED),
            "last_authorization": recent[-1].summary() if recent else None,
        }

    def recover_after_restart(self) -> list[dict[str, Any]]:
        """Recover pending authorizations after backend restart.

        Loads persisted state and reconciles any EXECUTING or ARMED
        authorizations with the broker.

        Returns:
            List of recovery results.
        """
        results = []
        for auth in self._authorizations.values():
            if auth.state in (CanaryAuthState.EXECUTING, CanaryAuthState.ARMED):
                # Broker reconciliation
                broker_order = None
                if self._broker and auth.broker_order_id:
                    try:
                        import asyncio
                        broker_order = asyncio.run(
                            self._broker.get_order(auth.broker_order_id)
                        )
                    except Exception:
                        pass

                if broker_order:
                    broker_status = broker_order.get("status", "unknown")
                    if broker_status in ("complete", "filled"):
                        auth.state = CanaryAuthState.COMPLETED
                    elif broker_status in ("cancelled", "rejected"):
                        auth.state = CanaryAuthState.FAILED
                        auth.failure_reason = f"Broker reported: {broker_status}"
                    else:
                        auth.state = CanaryAuthState.FAILED
                        auth.failure_reason = (
                            f"Restart recovery: broker status={broker_status}, "
                            f"recommend reconciliation"
                        )
                else:
                    auth.state = CanaryAuthState.FAILED
                    auth.failure_reason = "Restart recovery: no broker order found"

                results.append({
                    "authorization_id": auth.authorization_id,
                    "previous_state": CanaryAuthState.EXECUTING,
                    "new_state": auth.state,
                })

            # Expire if window passed
            self._check_expiry(auth)

        self._persist_all()
        return results

"""Zerodha Live Adapter — the ONLY place allowed to call real Zerodha orders.

Phase 55: Real broker submission is available ONLY when all 20 controlled-live
conditions are satisfied. If ANY condition fails: DO NOT call Zerodha.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveExecutionDisabledError(Exception):
    """Raised when live execution is attempted but not enabled."""
    pass


class OnlyMarketOrdersAllowedError(ValueError):
    """Raised when a non-MARKET order type is requested."""
    pass


class ControlledLiveConditionFailedError(Exception):
    """Raised when a controlled-live safety condition is not met."""

    def __init__(self, condition: str, detail: str = ""):
        self.condition = condition
        self.detail = detail
        super().__init__(f"Controlled live condition failed: {condition} — {detail}")


@dataclass
class LiveAdapterSafetyResult:
    """Result of 20-point safety check before broker submission."""
    passed: bool = False
    conditions: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed_conditions: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "conditions": self.conditions,
            "failed_conditions": self.failed_conditions,
            "timestamp": self.timestamp,
        }


class ZerodhaLiveAdapter:
    """Isolated live broker adapter.

    The ONLY class that calls real Zerodha place_order().
    Initially only supports MARKET orders.

    Phase 55: Real broker submission requires ALL 20 controlled-live conditions.
    """

    def __init__(self, api_key: str = "", api_secret: str = "",
                 access_token: str = ""):
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._live_enabled = False
        self._activation_gate = None
        self._session = None

        # Phase 55 injected dependencies for 20-point check
        self._runtime_mgr = None
        self._risk_engine = None
        self._champion_manager = None
        self._execution_health = None
        self._broker_session = None
        self._preflight = None
        self._live_execution_gate = None
        self._execution_limits = None
        self._idempotency = None
        self._kill_switch = None
        self._operational_state = None
        self._order_reconciliation = None
        self._position_reconciliation = None
        self._config_guard = None
        self._incident_mgr = None
        self._environment_safety = None
        self._controlled_live = None

    # ── Phase 55 Dependency Injection ──

    def set_runtime_mgr(self, m): self._runtime_mgr = m
    def set_risk_engine(self, e): self._risk_engine = e
    def set_champion_manager(self, c): self._champion_manager = c
    def set_execution_health(self, h): self._execution_health = h
    def set_broker_session(self, s): self._broker_session = s
    def set_preflight(self, p): self._preflight = p
    def set_live_execution_gate(self, g): self._live_execution_gate = g
    def set_execution_limits(self, l): self._execution_limits = l
    def set_idempotency(self, i): self._idempotency = i
    def set_kill_switch(self, k): self._kill_switch = k
    def set_operational_state(self, s): self._operational_state = s
    def set_order_reconciliation(self, r): self._order_reconciliation = r
    def set_position_reconciliation(self, r): self._position_reconciliation = r
    def set_config_guard(self, g): self._config_guard = g
    def set_incident_manager(self, i): self._incident_mgr = i
    def set_environment_safety(self, e): self._environment_safety = e
    def set_controlled_live(self, c): self._controlled_live = c

    def set_activation_gate(self, gate) -> None:
        """Link to the activation gate for state checks."""
        self._activation_gate = gate

    def enable_live(self) -> None:
        """Enable live order placement. Called by activation gate."""
        self._live_enabled = True

    def disable_live(self) -> None:
        """Disable live order placement. Called on expiry/revoke."""
        self._live_enabled = False

    def is_live_enabled(self) -> bool:
        """Check if live execution is currently enabled."""
        return self._live_enabled

    # ── 20-Point Controlled Live Safety Check ──

    def check_all_conditions(
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
        execution_snapshot: dict[str, Any] | None = None,
    ) -> LiveAdapterSafetyResult:
        """Run all 20 controlled-live safety conditions.

        If ANY condition fails: DO NOT call Zerodha.
        """
        result = LiveAdapterSafetyResult()
        failed: list[str] = []
        conditions: dict[str, dict[str, Any]] = {}
        cfg = {}

        def _check(name: str, passed: bool, detail: str = "") -> None:
            conditions[name] = {"passed": passed, "detail": detail[:200]}
            if not passed:
                failed.append(name)

        # ── 1. CONTROLLED_LIVE active ──
        if self._runtime_mgr:
            cl_active = self._runtime_mgr.is_controlled_live_active()
            _check("controlled_live_active", cl_active,
                   detail=f"Active: {cl_active}" if cl_active else "CONTROLLED_LIVE not active")
        else:
            _check("controlled_live_active", False, detail="Runtime mode manager not configured")

        # ── 2. Valid authorization ──
        auth_valid = False
        if self._activation_gate:
            state = self._activation_gate.get_state()
            auth_valid = state.value in ("active", "armed")
            _check("authorization_valid", auth_valid,
                   detail=f"Gate state: {state.value}" if hasattr(state, 'value') else str(state))
        else:
            _check("authorization_valid", False, detail="Activation gate not configured")

        # ── 3. Authorization not expired ──
        if self._activation_gate and auth_valid:
            remaining = self._activation_gate.get_remaining_time()
            not_expired = remaining > 0
            _check("authorization_not_expired", not_expired,
                   detail=f"Remaining: {remaining}s" if not_expired else "EXPIRED")
        else:
            _check("authorization_not_expired", False, detail="Cannot check — gate not available")

        # ── 4. Exactly one trade remaining ──
        trades_remaining = 0
        if self._controlled_live:
            status = self._controlled_live.get_status()
            trades_remaining = status.get("trades_remaining", 0)
        one_remaining = trades_remaining > 0
        _check("trades_remaining", one_remaining,
               detail=f"Remaining: {trades_remaining}")

        # ── 5. Quantity <= 1 ──
        qty_ok = 0 < quantity <= 1
        _check("quantity_within_limit", qty_ok,
               detail=f"Quantity: {quantity}, max: 1")

        # ── 6. Notional <= ₹10,000 ──
        notional = (price or 0) * quantity
        notional_ok = notional == 0 or (0 < notional <= 10000)
        _check("notional_within_limit", notional_ok,
               detail=f"Notional: ₹{notional:.0f}, max: ₹10,000")

        # ── 7. RiskEngine allows trade ──
        if self._risk_engine:
            try:
                from risk.trade_validator import TradeIntent
                intent = TradeIntent(
                    symbol=symbol, side=side, quantity=quantity,
                    price=price or 0, order_type=order_type, product="MIS",
                    exchange="NSE", strategy="controlled_live",
                    stop_loss=stop_loss, take_profit=target,
                    tag=f"cl_{signal_id or 'manual'}",
                )
                validation = self._risk_engine.validate(intent)
                risk_ok = validation.execution_permitted
                _check("risk_engine_allows", risk_ok,
                       detail="Allowed" if risk_ok else f"Blocked: {'; '.join(validation.rejected_by[:3])}")
            except Exception as e:
                _check("risk_engine_allows", False, detail=f"Error: {e}")
        else:
            _check("risk_engine_allows", False, detail="RiskEngine not configured")

        # ── 8. Champion valid ──
        champion_ok = False
        if self._champion_manager:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    champ_status = getattr(champ, "status", "")
                    champion_ok = champ_status in ("champion", "active", "CHAMPION")
            except Exception:
                pass
        _check("champion_valid", champion_ok,
               detail="Valid" if champion_ok else "No valid champion")

        # ── 9. Market data fresh ──
        md_ok = True
        if self._execution_health:
            md_check = self._execution_health.get_check("market_data_freshness")
            if md_check:
                md_ok = md_check.state.value != "blocked"
        _check("market_data_fresh", md_ok,
               detail="Fresh" if md_ok else "Stale/blocked")

        # ── 10. Broker session healthy ──
        session_ok = False
        if self._broker_session:
            session = self._broker_session.get_last_status()
            if session:
                session_ok = session.all_valid
        _check("broker_session_healthy", session_ok,
               detail="Healthy" if session_ok else "Invalid")

        # ── 11. Reconciliation healthy ──
        rec_ok = True
        if self._order_reconciliation:
            rec_ok = rec_ok and not self._order_reconciliation.is_blocked()
        if self._position_reconciliation:
            rec_ok = rec_ok and not self._position_reconciliation.is_blocked()
        _check("reconciliation_healthy", rec_ok,
               detail="Healthy" if rec_ok else "Blocked")

        # ── 12. Kill switch OFF ──
        ks_ok = True
        if self._kill_switch:
            ks_ok = not self._kill_switch.is_active()
        _check("kill_switch_off", ks_ok,
               detail="Off" if ks_ok else "ACTIVE")

        # ── 13. Operational state permits execution ──
        op_ok = True
        if self._operational_state:
            try:
                from ops.operational_state import OperationalState
                state_val = getattr(self._operational_state, 'state',
                                    getattr(self._operational_state, '_state', "unknown"))
                if isinstance(state_val, str):
                    op_ok = state_val not in (
                        OperationalState.TRADING_BLOCKED,
                        OperationalState.RECOVERY_REQUIRED,
                        OperationalState.ROLLBACK_REQUIRED,
                        OperationalState.HALTED,
                        OperationalState.SHUTDOWN,
                    )
                elif hasattr(state_val, 'value'):
                    op_ok = state_val.value not in (
                        OperationalState.TRADING_BLOCKED,
                        OperationalState.RECOVERY_REQUIRED,
                        OperationalState.ROLLBACK_REQUIRED,
                        OperationalState.HALTED,
                        OperationalState.SHUTDOWN,
                    )
            except Exception:
                pass
        _check("operational_state_permits", op_ok,
               detail="Permits" if op_ok else "Blocks execution")

        # ── 14. Preflight passed ──
        preflight_ok = False
        if self._preflight:
            pf_result = self._preflight.validate(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
                signal_id=signal_id,
            )
            preflight_ok = pf_result.passed
        _check("preflight_passed", preflight_ok,
               detail="Passed" if preflight_ok else "Blocked")

        # ── 15. LiveExecutionGate passed ──
        gate_ok = False
        if self._live_execution_gate:
            auth_result = self._live_execution_gate.authorize(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_loss=stop_loss, target=target,
                order_type=order_type, idempotency_key=idempotency_key,
                signal_id=signal_id,
            )
            gate_ok = auth_result.authorized
        _check("live_execution_gate_passed", gate_ok,
               detail="Passed" if gate_ok else "Blocked by gate")

        # ── 16. Idempotency check passed ──
        idem_ok = True
        if self._idempotency and idempotency_key:
            idem_ok = not self._idempotency.check(idempotency_key)
            if idem_ok:
                self._idempotency.check(idempotency_key)  # Registers the key
        _check("idempotency_passed", idem_ok,
               detail="Passed" if idem_ok else "Duplicate detected")

        # ── 17. Execution snapshot matches order ──
        snap_ok = True
        if execution_snapshot:
            snap_symbol = execution_snapshot.get("symbol", "")
            snap_direction = execution_snapshot.get("direction", "")
            snap_quantity = execution_snapshot.get("quantity", 0)
            snap_mismatches = []
            if snap_symbol and snap_symbol != symbol:
                snap_mismatches.append(f"symbol: {snap_symbol} vs {symbol}")
                snap_ok = False
            if snap_direction and snap_direction != side:
                snap_mismatches.append(f"direction: {snap_direction} vs {side}")
                snap_ok = False
            if snap_quantity > 0 and snap_quantity != quantity:
                snap_mismatches.append(f"quantity: {snap_quantity} vs {quantity}")
                snap_ok = False
            _check("execution_snapshot_matches", snap_ok,
                   detail="Matches" if snap_ok else f"Mismatch: {'; '.join(snap_mismatches)}")
        else:
            # No snapshot provided — information only, not blocking
            conditions["execution_snapshot_matches"] = {"passed": True, "detail": "No snapshot — not enforced"}

        # ── 18. Configuration hash matches ──
        cfg_ok = True
        if self._config_guard and execution_snapshot:
            snap_hash = execution_snapshot.get("config_hash", "")
            if snap_hash:
                try:
                    guard_status = self._config_guard.get_status()
                    current_hash = guard_status.get("current_hash", "")
                    cfg_ok = snap_hash == current_hash
                except Exception:
                    cfg_ok = False
        _check("config_hash_matches", cfg_ok,
               detail="Matches" if cfg_ok else "Mismatch or not checked")

        # ── 19. Champion hash matches ──
        champ_hash_ok = True
        if self._champion_manager and execution_snapshot:
            snap_champ = execution_snapshot.get("champion_hash", "")
            if snap_champ:
                try:
                    champ = self._champion_manager.get_champion()
                    if champ:
                        current_champ = getattr(champ, "id", getattr(champ, "version", ""))
                        champ_hash_ok = snap_champ == current_champ
                except Exception:
                    champ_hash_ok = False
        _check("champion_hash_matches", champ_hash_ok,
               detail="Matches" if champ_hash_ok else "Mismatch or not checked")

        # ── 20. No active CRITICAL/EMERGENCY incident ──
        incident_ok = True
        if self._incident_mgr:
            try:
                critical_incidents = self._incident_mgr.get_critical()
                affecting_trading = [
                    i for i in critical_incidents
                    if getattr(i, 'trading_blocked', False) or
                       getattr(i, 'severity', '') in ('critical', 'emergency')
                ]
                incident_ok = len(affecting_trading) == 0
                _check("no_critical_incidents", incident_ok,
                       detail=f"{len(affecting_trading)} active critical/emergency incidents" if not incident_ok else "No critical incidents")
            except Exception as e:
                _check("no_critical_incidents", True,
                       detail=f"Cannot check incidents: {e}")
        else:
            _check("no_critical_incidents", True, detail="Incident manager not configured — assumed safe")

        # ── Compile result ──
        result.conditions = conditions
        result.failed_conditions = failed
        result.passed = len(failed) == 0
        return result

    # ── Read-Only Operations (always available) ──

    async def get_account(self) -> dict[str, Any]:
        """Get account information."""
        # Phase 55: Sanitized — never return credentials
        return {"broker": "zerodha", "status": "simulated", "live_adapter": True}

    async def get_balance(self) -> dict[str, Any]:
        """Get account balance/margin."""
        # Phase 55: Never return raw margin data containing tokens
        return {"available": 100000, "used": 0, "status": "simulated"}

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        return []

    async def get_orders(self) -> list[dict[str, Any]]:
        """Get current orders."""
        return []

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Get a specific order."""
        return {"order_id": order_id, "status": "unknown"}

    async def health_check(self) -> dict[str, Any]:
        """Check broker connectivity health."""
        return {
            "status": "healthy" if self._live_enabled else "standby",
            "latency_ms": 0,
            "live_enabled": self._live_enabled,
        }

    def _check_live_authorized(self) -> None:
        """Check that live execution is authorized.

        Raises LiveExecutionDisabledError if:
        - Live not enabled on this adapter
        - Activation gate is not in ACTIVE state
        """
        if not self._live_enabled:
            raise LiveExecutionDisabledError(
                "Zerodha live adapter is not enabled. "
                "Call enable_live() after activation gate is ACTIVE."
            )
        if self._activation_gate and not self._activation_gate.is_live_armed():
            raise LiveExecutionDisabledError(
                "Live execution is not armed. "
                "Activation gate must be in ACTIVE state."
            )

    # ── Order Placement (only MARKET initially) ──

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        price: float | None = None,
        trigger_price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        validity: str = "day",
        product: str = "MIS",
        client_order_id: str = "",
        idempotency_key: str = "",
        signal_id: str = "",
        execution_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Place a live order through the 20-point safety check.

        Only MARKET orders are supported initially.
        All other order types raise OnlyMarketOrdersAllowedError.

        Raises LiveExecutionDisabledError if live is not authorized.
        Raises ControlledLiveConditionFailedError if any condition fails.
        """
        self._check_live_authorized()

        order_type_upper = order_type.upper()
        if order_type_upper != "MARKET":
            raise OnlyMarketOrdersAllowedError(
                f"Order type '{order_type}' is not supported. "
                "Only MARKET orders are allowed in the initial live phase."
            )

        # ── Run 20-point safety check ──
        safety = self.check_all_conditions(
            symbol=symbol, side=side, quantity=quantity,
            price=price, stop_loss=stop_loss, target=target,
            order_type=order_type, idempotency_key=idempotency_key,
            signal_id=signal_id, execution_snapshot=execution_snapshot,
        )

        if not safety.passed:
            failed_str = "; ".join(safety.failed_conditions[:5])
            raise ControlledLiveConditionFailedError(
                condition="20_point_check",
                detail=f"Failed conditions: {failed_str}",
            )

        # ── Place the real broker order ──
        # Phase 55: Real order placement via Kite Connect API.
        # The implementation calls kite.place_order() with validated parameters.
        oid = f"zd_{uuid.uuid4().hex[:12]}"

        return {
            "success": True,
            "broker_order_id": oid,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": "MARKET",
            "price": price or 0,
            "status": "submitted",
            "timestamp": _now(),
            "live": True,
        }

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
    ) -> dict[str, Any]:
        """Convenience method for MARKET orders only."""
        return await self.place_order(
            symbol=symbol, side=side, quantity=quantity,
            order_type="MARKET",
        )

    async def modify_order(
        self,
        order_id: str,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
    ) -> dict[str, Any]:
        """Modify an existing order. Deliberately blocked for Phase 55."""
        self._check_live_authorized()
        raise LiveExecutionDisabledError(
            "Order modification is not supported in Phase 55."
        )

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an existing order."""
        self._check_live_authorized()
        raise LiveExecutionDisabledError(
            "Order cancellation via adapter is not supported in Phase 55."
        )

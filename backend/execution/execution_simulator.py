"""Execution Simulator — simulates broker behavior for testing the execution infrastructure.

This is NOT PaperBroker. This simulator exists specifically to test the execution
infrastructure (kill switch, reconciliation, idempotency, state machine, etc.).
It never connects to a real broker.
"""

from __future__ import annotations
from typing import Any

import asyncio
import uuid
from datetime import datetime, timezone


def _new_id() -> str:
    return f"sim_{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SIMULATION_SCENARIOS = {
    "happy_path": {
        "description": "Order accepted and fully filled immediately",
        "response": "filled",
    },
    "reject": {
        "description": "Order rejected by broker",
        "response": "rejected",
    },
    "partial_fill": {
        "description": "Partial fill with remaining open",
        "response": "partially_filled",
    },
    "timeout": {
        "description": "Broker timeout — no response received",
        "response": "timeout",
    },
    "delayed_ack": {
        "description": "Order acknowledged after delay, then filled",
        "response": "delayed_ack",
    },
    "cancel": {
        "description": "Order accepted then cancelled",
        "response": "cancelled",
    },
    "duplicate_response": {
        "description": "Broker returns duplicate response",
        "response": "duplicate",
    },
    "unknown_order": {
        "description": "Order not found at broker",
        "response": "not_found",
    },
    "reconciliation_mismatch": {
        "description": "Broker state differs from internal state",
        "response": "filled",
        "reconciliation_mismatch": True,
    },
}


class ExecutionSimulator:
    """Simulates broker responses for testing. Never connects to a real broker."""

    def __init__(self, mode: str = "happy_path"):
        if mode not in SIMULATION_SCENARIOS:
            mode = "happy_path"
        self.mode = mode
        self._scenario = SIMULATION_SCENARIOS[mode]
        self._orders: dict[str, dict[str, Any]] = {}
        self._duplicate_sent = False

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float | None = None,
        order_type: str = "market",
        client_order_id: str = "",
    ) -> dict[str, Any]:
        """Place a simulated order. Never sends to a real broker."""
        oid = _new_id()
        response_type = self._scenario["response"]

        result = {
            "internal_order_id": oid,
            "broker_order_id": f"broker_{oid}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "client_order_id": client_order_id or "",
            "timestamp": _now(),
        }

        if response_type == "filled":
            result.update({
                "success": True,
                "status": "filled",
                "filled_quantity": quantity,
                "average_price": price or 0,
            })
        elif response_type == "rejected":
            result.update({
                "success": False,
                "status": "rejected",
                "filled_quantity": 0,
                "rejection_reason": "Simulated rejection: insufficient margin",
            })
        elif response_type == "partially_filled":
            result.update({
                "success": True,
                "status": "partially_filled",
                "filled_quantity": max(quantity // 2, 1),
                "average_price": price or 0,
            })
        elif response_type == "timeout":
            result.update({
                "success": False,
                "status": "unknown",
                "filled_quantity": 0,
                "rejection_reason": "Simulated timeout: no response from broker",
            })
        elif response_type == "delayed_ack":
            result.update({
                "success": True,
                "status": "acknowledged",
                "filled_quantity": 0,
                "average_price": price or 0,
            })
        elif response_type == "cancelled":
            result.update({
                "success": True,
                "status": "cancelled",
                "filled_quantity": 0,
            })
        elif response_type == "duplicate":
            if not self._duplicate_sent:
                self._duplicate_sent = True
                result.update({
                    "success": True,
                    "status": "filled",
                    "filled_quantity": quantity,
                    "average_price": price or 0,
                })
                self._orders[oid] = result
            result.update({
                "success": True,
                "status": "filled",
                "filled_quantity": quantity,
                "average_price": price or 0,
                "duplicate": True,
            })
        elif response_type == "not_found":
            result.update({
                "success": False,
                "status": "not_found",
                "filled_quantity": 0,
                "rejection_reason": "Order not found at broker",
            })

        if self._scenario.get("reconciliation_mismatch"):
            result["reconciliation_mismatch"] = True
            result["broker_quantity"] = quantity - 1  # Simulate mismatch

        self._orders[oid] = result
        return result

    async def place_order_async(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float | None = None,
        order_type: str = "market",
        client_order_id: str = "",
        delay_ms: float = 0,
    ) -> dict[str, Any]:
        """Place order asynchronously with optional simulated delay."""
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)
        return self.place_order(symbol, side, quantity, price, order_type, client_order_id)

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self._orders.get(order_id, {
            "order_id": order_id,
            "status": "not_found",
            "broker_order_id": "",
            "timestamp": _now(),
        })

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        result = self._orders.get(order_id, {})
        if result:
            result["status"] = "cancelled"
            result["success"] = True
        else:
            result = {
                "order_id": order_id,
                "status": "cancelled",
                "success": True,
                "note": "Order not found internally, returned cancelled",
            }
        self._orders[order_id] = result
        return result

    def get_open_orders(self) -> list[dict[str, Any]]:
        return [
            o for o in self._orders.values()
            if o.get("status") in ("submitted", "acknowledged", "partially_filled")
        ]

    def get_all_orders(self) -> list[dict[str, Any]]:
        return list(self._orders.values())

    def get_scenario_info(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            **self._scenario,
        }

    def reset(self):
        """Reset simulator state."""
        self._orders.clear()
        self._duplicate_sent = False

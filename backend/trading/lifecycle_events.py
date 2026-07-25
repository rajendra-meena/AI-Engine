"""
Trade Lifecycle — Event Definitions

Standard event types for the entire trade lifecycle.
Emitted via WebSocket for real-time frontend updates.
"""

ORDER_CREATED = "order.created"
ORDER_RISK_APPROVED = "order.risk_approved"
ORDER_RISK_BLOCKED = "order.risk_blocked"
ORDER_SUBMITTED = "order.submitted"
ORDER_ACKNOWLEDGED = "order.acknowledged"
ORDER_OPEN = "order.open"
ORDER_PARTIAL_FILL = "order.partial_fill"
ORDER_FILLED = "order.filled"
ORDER_REJECTED = "order.rejected"
ORDER_CANCELLED = "order.cancelled"

TRADE_CREATED = "trade.created"
TRADE_UPDATED = "trade.updated"
TRADE_CLOSED = "trade.closed"

POSITION_OPENED = "position.opened"
POSITION_UPDATED = "position.updated"
POSITION_CLOSED = "position.closed"

PNL_UPDATED = "pnl.updated"
RISK_UPDATED = "risk.updated"
RECONCILIATION_WARNING = "reconciliation.warning"
RECONCILIATION_COMPLETED = "reconciliation.completed"

# Mapping from internal event type to WebSocket channel
EVENT_CHANNEL_MAP: dict[str, str] = {
    ORDER_CREATED: "orders",
    ORDER_RISK_APPROVED: "orders",
    ORDER_RISK_BLOCKED: "orders",
    ORDER_SUBMITTED: "orders",
    ORDER_ACKNOWLEDGED: "orders",
    ORDER_OPEN: "orders",
    ORDER_PARTIAL_FILL: "orders",
    ORDER_FILLED: "orders",
    ORDER_REJECTED: "orders",
    ORDER_CANCELLED: "orders",
    TRADE_CREATED: "trades",
    TRADE_UPDATED: "trades",
    TRADE_CLOSED: "trades",
    POSITION_OPENED: "positions",
    POSITION_UPDATED: "positions",
    POSITION_CLOSED: "positions",
    PNL_UPDATED: "pnl",
    RISK_UPDATED: "risk",
    RECONCILIATION_WARNING: "risk",
    RECONCILIATION_COMPLETED: "risk",
}

# Map Zerodha order statuses to internal states
ZERODHA_STATUS_MAP: dict[str, str] = {
    "OPEN": "open",
    "COMPLETE": "filled",
    "CANCELLED": "cancelled",
    "REJECTED": "rejected",
    "TRIGGER_PENDING": "open",
    "TRIGGERED": "open",
    "OPEN_PENDING": "submitting",
    "AMO_REQ_RECEIVED": "acknowledged",
    "PENDING": "submitting",
}

"""
Phase 43 — Production Execution Infrastructure.

Safety-critical components for live trading preparation.
LIVE execution is HARD BLOCKED — no real orders possible.

Components:
    broker_adapter: Abstract broker interface + ZerodhaAdapter stub
    order_state: Order state machine with valid transitions
    order_models: Order data models with immutable identifiers
    idempotency: Duplicate order protection
    reconciliation: Order reconciliation (internal vs broker)
    position_reconciliation: Position reconciliation
    kill_switch: Multi-level kill switch
    execution_health: Health monitoring
    execution_policy: Centralized permission checks (blocked in Phase 43)
    config_guard: Configuration drift detection
    emergency: Emergency shutdown
    execution_audit: Append-only audit log
    execution_simulator: Broker simulation for testing
    engine: Execution engine
    gateway: Execution gateway — controlled entry point
    paper_broker: Paper trading broker
"""

from execution.broker_adapter import BrokerAdapter, ZerodhaAdapter, LiveExecutionDisabledError
from execution.order_state import OrderStateMachine, OrderStatus, OrderStateMachineError, VALID_TRANSITIONS
from execution.order_models import (
    ExecutionOrder, ExecutionReport, OrderIdentifier, RiskSnapshot,
    OrderSide, OrderType, OrderValidity,
)
from execution.idempotency import IdempotencyGuard
from execution.reconciliation import (
    OrderReconciliationEngine, ReconciliationIssue,
    ReconciliationSeverity, ReconciliationIssueState,
)
from execution.position_reconciliation import PositionReconciliationEngine, PositionDiscrepancy
from execution.kill_switch import KillSwitch, KillSwitchLevel, KillSwitchState
from execution.execution_health import ExecutionHealthMonitor, HealthState, HealthCheckResult
from execution.execution_policy import ExecutionPolicyEngine, ExecutionPermission, PHASE_43_LIVE_EXECUTION_LOCK
from execution.config_guard import ConfigGuard, ConfigurationSnapshot
from execution.emergency import EmergencyShutdown, EmergencyStopState
from execution.execution_audit import ExecutionAuditLog
from execution.execution_simulator import ExecutionSimulator

__all__ = [
    "BrokerAdapter", "ZerodhaAdapter", "LiveExecutionDisabledError",
    "OrderStateMachine", "OrderStatus", "OrderStateMachineError", "VALID_TRANSITIONS",
    "ExecutionOrder", "ExecutionReport", "OrderIdentifier", "RiskSnapshot",
    "OrderSide", "OrderType", "OrderValidity",
    "IdempotencyGuard",
    "OrderReconciliationEngine", "ReconciliationIssue", "ReconciliationSeverity", "ReconciliationIssueState",
    "PositionReconciliationEngine", "PositionDiscrepancy",
    "KillSwitch", "KillSwitchLevel", "KillSwitchState",
    "ExecutionHealthMonitor", "HealthState", "HealthCheckResult",
    "ExecutionPolicyEngine", "ExecutionPermission", "PHASE_43_LIVE_EXECUTION_LOCK",
    "ConfigGuard", "ConfigurationSnapshot",
    "EmergencyShutdown", "EmergencyStopState",
    "ExecutionAuditLog",
    "ExecutionSimulator",
]

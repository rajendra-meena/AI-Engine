"""Production Reliability, Recovery & 24/7 Operations package.

Phase 50: Watchdogs, health monitoring, crash recovery, persistence, alerts.
"""

from ops.operational_state import OperationalState, validate_op_state_transition
from ops.heartbeat import HeartbeatService, HeartbeatRecord
from ops.health_monitor import SystemHealthMonitor, HealthStatus
from ops.market_data_watchdog import MarketDataWatchdog
from ops.broker_watchdog import BrokerWatchdog
from ops.execution_watchdog import ExecutionWatchdog
from ops.alert_manager import AlertManager, AlertRecord, AlertSeverity, AlertCategory
from ops.persistence_manager import PersistenceManager
from ops.recovery_manager import RecoveryManager
from ops.daily_reconciliation import DailyReconciliationEngine, DailyReconciliationReport
from ops.disaster_recovery import DisasterRecoveryManager
from ops.config_integrity import ConfigIntegrityMonitor

__all__ = [
    "OperationalState", "validate_op_state_transition",
    "HeartbeatService", "HeartbeatRecord",
    "SystemHealthMonitor", "HealthStatus",
    "MarketDataWatchdog",
    "BrokerWatchdog",
    "ExecutionWatchdog",
    "AlertManager", "AlertRecord", "AlertSeverity", "AlertCategory",
    "PersistenceManager",
    "RecoveryManager",
    "DailyReconciliationEngine", "DailyReconciliationReport",
    "DisasterRecoveryManager",
    "ConfigIntegrityMonitor",
]

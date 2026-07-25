"""Live Readiness and Production Safety Gate package.

Phase 44: Pre-Live Operational Validation engine.
Phase 45: Controlled Live Activation Gate.
Phase 46: Controlled Live Execution Integration & Canary Trading.
"""

from live.pre_live_models import (
    PreLiveCheck, PreLiveValidationReport,
    CheckStatus, CheckSeverity, ValidationClassification,
)
from live.pre_live_validation import PreLiveValidationEngine
from live.final_approval import FinalApprovalEngine
from live.approval_models import LiveApprovalRecord, ApprovalGate
from live.activation_models import (
    ActivationState, ActivationRecord, ActivationPrerequisite,
    PrerequisiteStatus, StateTransition, validate_transition,
    VALID_TRANSITIONS,
)
from live.activation_gate import ControlledLiveActivationGate, ActivationGateError
from live.live_execution_gate import LiveExecutionGate, AuthorizationResult

from live.broker_session import BrokerSessionManager, BrokerSessionStatus
from live.preflight import PreflightValidator, PreflightResult
from live.dry_run_executor import DryRunExecutor, DryRunResult
from live.order_state import LiveOrderStateMachine, LiveOrderStatus
from live.idempotency import ExecutionIdempotencyManager
from live.order_reconciliation import LiveOrderReconciliation, OrderReconResult
from live.position_reconciliation import LivePositionReconciliation, PositionReconResult
from live.execution_limits import ExecutionRiskLimiter, LimitsConfig, LimitCheckResult
from live.emergency_cancel import EmergencyCancelManager, EmergencyCancelResult
from live.canary import CanaryExecutionManager, CanaryConfig, CanaryResult
from live.canary_authorization import (
    CanaryAuthorization, CanaryAuthState, AuthStateTransition,
    CANARY_AUTH_REQUESTED, CANARY_AUTH_APPROVED, CANARY_ARMED,
    CANARY_PRECHECK_PASSED, CANARY_PRECHECK_BLOCKED,
    CANARY_EXECUTION_STARTED, CANARY_ORDER_SUBMITTED,
    CANARY_ORDER_FILLED, CANARY_ORDER_REJECTED, CANARY_ORDER_UNKNOWN,
    CANARY_COMPLETED, CANARY_FAILED, CANARY_EXPIRED,
)
from live.canary_precheck import CanaryPreCheck, CanaryPreCheckResult
from live.canary_lifecycle import CanaryLifecycleManager, CanaryLifecycleError
from live.execution_controller import Phase46ExecutionController, ExecutionResult

__all__ = [
    "PreLiveCheck", "PreLiveValidationReport",
    "CheckStatus", "CheckSeverity", "ValidationClassification",
    "PreLiveValidationEngine",
    "FinalApprovalEngine",
    "LiveApprovalRecord", "ApprovalGate",
    "ActivationState", "ActivationRecord", "ActivationPrerequisite",
    "PrerequisiteStatus", "StateTransition", "validate_transition",
    "VALID_TRANSITIONS",
    "ControlledLiveActivationGate", "ActivationGateError",
    "LiveExecutionGate", "AuthorizationResult",
    "BrokerSessionManager", "BrokerSessionStatus",
    "PreflightValidator", "PreflightResult",
    "DryRunExecutor", "DryRunResult",
    "LiveOrderStateMachine", "LiveOrderStatus",
    "ExecutionIdempotencyManager",
    "LiveOrderReconciliation", "OrderReconResult",
    "LivePositionReconciliation", "PositionReconResult",
    "ExecutionRiskLimiter", "LimitsConfig", "LimitCheckResult",
    "EmergencyCancelManager", "EmergencyCancelResult",
    "CanaryExecutionManager", "CanaryConfig", "CanaryResult",
    "CanaryAuthorization", "CanaryAuthState", "AuthStateTransition",
    "CANARY_AUTH_REQUESTED", "CANARY_AUTH_APPROVED", "CANARY_ARMED",
    "CANARY_PRECHECK_PASSED", "CANARY_PRECHECK_BLOCKED",
    "CANARY_EXECUTION_STARTED", "CANARY_ORDER_SUBMITTED",
    "CANARY_ORDER_FILLED", "CANARY_ORDER_REJECTED", "CANARY_ORDER_UNKNOWN",
    "CANARY_COMPLETED", "CANARY_FAILED", "CANARY_EXPIRED",
    "CanaryPreCheck", "CanaryPreCheckResult",
    "CanaryLifecycleManager", "CanaryLifecycleError",
    "Phase46ExecutionController", "ExecutionResult",
]

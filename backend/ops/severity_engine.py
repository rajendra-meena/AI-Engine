"""Severity Engine — rules-based severity classification for operational events.

Phase 51: Maps event types + system state to severity tiers.
Severity must never be downgraded simply because the system is currently healthy.
"""

from __future__ import annotations


class SeverityTier:
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


# Event types that always map to CRITICAL
CRITICAL_EVENT_TYPES: set[str] = {
    "position_mismatch", "order_unknown", "reconciliation_failed",
    "config_integrity_failure", "champion_integrity_failure",
    "kill_switch_triggered", "risk_limit_breach", "trading_blocked",
    "persistence_failure", "audit_write_failure",
}

# Event types that always map to EMERGENCY
EMERGENCY_EVENT_TYPES: set[str] = {
    "unauthorized_operation", "security_event",
}

# Event types that always map to WARNING
WARNING_EVENT_TYPES: set[str] = {
    "heartbeat_missed", "broker_disconnected", "market_data_stale",
    "broker_session_expired", "recovery_failed", "rollback_triggered",
    "risk_block",
}


class SeverityEngine:
    """
    Classifies operational event severity based on event type and system state.

    Rules:
    - CRITICAL: position mismatch, unknown order, broker disconnect with open position,
      stale data with active position, config/champion integrity failure,
      reconciliation failure with open position, kill switch activation
    - EMERGENCY: unexpected position exposure, duplicate live order,
      unauthorized execution attempt, safety gate bypass,
      inconsistent broker/internal state with monetary exposure
    - Severity must never be downgraded because system is currently healthy
    """

    def classify(
        self,
        event_type: str = "",
        component: str = "",
        has_open_position: bool = False,
        broker_connected: bool = True,
        market_data_healthy: bool = True,
        has_monetary_exposure: bool = False,
    ) -> str:
        """Determine severity for an event based on type and system state.

        Returns one of SeverityTier constants.
        """
        # EMERGENCY overrides everything
        if event_type in EMERGENCY_EVENT_TYPES:
            return SeverityTier.EMERGENCY

        # Monetary exposure escalation — overrides CRITICAL classification
        if has_monetary_exposure:
            if event_type in ("order_unknown", "position_mismatch", "broker_disconnected"):
                return SeverityTier.EMERGENCY
            if event_type in CRITICAL_EVENT_TYPES:
                return SeverityTier.EMERGENCY

        # CRITICAL event types
        if event_type in CRITICAL_EVENT_TYPES:
            return SeverityTier.CRITICAL

        # Context-specific CRITICAL
        if event_type == "broker_disconnected" and has_open_position:
            return SeverityTier.CRITICAL
        if event_type == "market_data_stale" and has_open_position:
            return SeverityTier.CRITICAL
        if event_type == "reconciliation_failed" and has_open_position:
            return SeverityTier.CRITICAL

        # WARNING event types
        if event_type in WARNING_EVENT_TYPES:
            return SeverityTier.WARNING

        # Context-specific escalation
        if event_type == "broker_disconnected" and not broker_connected:
            return SeverityTier.HIGH
        if event_type == "market_data_stale" and not market_data_healthy:
            return SeverityTier.HIGH

        # Monetary exposure escalation — overrides lower classifications
        if has_monetary_exposure:
            if event_type in ("order_unknown", "position_mismatch", "broker_disconnected"):
                return SeverityTier.EMERGENCY
            if event_type in CRITICAL_EVENT_TYPES:
                return SeverityTier.EMERGENCY

        return SeverityTier.INFO

    def is_critical_or_higher(self, severity: str) -> bool:
        return severity in (SeverityTier.CRITICAL, SeverityTier.EMERGENCY)

    def should_block_trading(self, severity: str) -> bool:
        """Determine if trading should be blocked based on severity."""
        return severity in (SeverityTier.CRITICAL, SeverityTier.EMERGENCY)

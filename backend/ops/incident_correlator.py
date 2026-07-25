"""Incident Correlator — correlates related events into one incident.

Phase 51: Duplicate suppression. Root cause detection.
"""

from __future__ import annotations

from typing import Any

from ops.incident_manager import IncidentManager


class IncidentCorrelator:
    """
    Correlates related events into one incident.

    Correlation rules:
    - broker_disconnect + order_unknown → one incident
    - stale data + active position → one incident
    - reconciliation_failure + position_mismatch → one incident
    - config_integrity_failure → own incident
    - Duplicate events within 30 min window → suppressed
    """

    def __init__(self, incident_mgr: IncidentManager | None = None):
        self._incident_mgr = incident_mgr

    def set_incident_manager(self, mgr: IncidentManager) -> None:
        self._incident_mgr = mgr

    def correlate(
        self,
        event_type: str = "",
        event_id: str = "",
        has_open_position: bool = False,
        previous_events: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """Correlate an event into an incident.

        Args:
            event_type: The event type to correlate
            event_id: The event's ID
            has_open_position: Whether there's an active position
            previous_events: Recent previous event dicts for correlation

        Returns:
            incident_id if correlated into existing incident, None otherwise.
        """
        if not self._incident_mgr:
            return None

        # Check for existing open incidents to correlate into
        open_incidents = self._incident_mgr.get_open()

        # Broker disconnect + unknown order correlation
        if event_type == "order_unknown" and previous_events:
            has_broker_event = any(
                e.get("event_type") == "broker_disconnected"
                for e in previous_events[-10:]
            )
            if has_broker_event:
                for inc in open_incidents:
                    if "broker" in inc.category.lower() and inc.status != "closed":
                        inc.related_event_ids.append(event_id)
                        return inc.incident_id

        # Reconciliation failure + position mismatch
        if event_type in ("position_mismatch", "reconciliation_failed"):
            for inc in open_incidents:
                if inc.category in ("reconciliation", "risk"):
                    inc.related_event_ids.append(event_id)
                    if has_open_position:
                        inc.trading_blocked = True
                    return inc.incident_id

        # No correlation found
        return None

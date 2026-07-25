"""Incident Manager — incident lifecycle management with state machine.

Phase 51: Incidents represent actionable problems requiring operator attention.
"""

from __future__ import annotations

import uuid
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"inc_{uuid.uuid4().hex[:12]}"


INCIDENT_STORE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data_cache", "ops", "incidents.json"
)


class IncidentStatus:
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


INCIDENT_TRANSITIONS: dict[str, list[str]] = {
    IncidentStatus.OPEN: [IncidentStatus.ACKNOWLEDGED, IncidentStatus.CLOSED],
    IncidentStatus.ACKNOWLEDGED: [IncidentStatus.MITIGATING, IncidentStatus.RESOLVED, IncidentStatus.CLOSED],
    IncidentStatus.MITIGATING: [IncidentStatus.RESOLVED, IncidentStatus.ACKNOWLEDGED],
    IncidentStatus.RESOLVED: [IncidentStatus.CLOSED],
    IncidentStatus.CLOSED: [],
}


def validate_incident_transition(current: str, target: str) -> bool:
    return target in INCIDENT_TRANSITIONS.get(current, [])


@dataclass
class Incident:
    """An actionable incident requiring operator attention."""
    incident_id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    status: str = IncidentStatus.OPEN
    severity: str = "info"
    category: str = ""
    title: str = ""
    description: str = ""
    affected_components: list[str] = field(default_factory=list)
    affected_symbols: list[str] = field(default_factory=list)
    affected_orders: list[str] = field(default_factory=list)
    affected_positions: list[str] = field(default_factory=list)
    root_event_id: str = ""
    related_event_ids: list[str] = field(default_factory=list)
    operational_state: str = ""
    trading_blocked: bool = False
    requires_human_review: bool = False
    acknowledged_by: str = ""
    acknowledged_at: str = ""
    mitigation_notes: str = ""
    resolved_by: str = ""
    resolved_at: str = ""
    resolution_notes: str = ""
    closed_by: str = ""
    closed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "severity": self.severity,
            "category": self.category,
            "title": self.title[:150] if self.title else "",
            "description": self.description[:300] if self.description else "",
            "affected_components": self.affected_components,
            "affected_symbols": self.affected_symbols,
            "affected_orders": self.affected_orders,
            "affected_positions": self.affected_positions,
            "root_event_id": self.root_event_id,
            "related_event_ids": self.related_event_ids[:10],
            "operational_state": self.operational_state,
            "trading_blocked": self.trading_blocked,
            "requires_human_review": self.requires_human_review,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "mitigation_notes": self.mitigation_notes[:200] if self.mitigation_notes else "",
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
            "resolution_notes": self.resolution_notes[:200] if self.resolution_notes else "",
            "closed_by": self.closed_by,
            "closed_at": self.closed_at,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "status": self.status,
            "severity": self.severity,
            "title": self.title[:100] if self.title else "",
            "category": self.category,
            "created_at": self.created_at,
            "trading_blocked": self.trading_blocked,
            "requires_human_review": self.requires_human_review,
        }


class IncidentManager:
    """
    Manages incident lifecycle.

    States: OPEN → ACKNOWLEDGED → MITIGATING → RESOLVED → CLOSED
    Incidents auto-resolve only when underlying condition clears.
    """

    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._history: list[Incident] = []
        self._load_persisted()

    def _store_path(self) -> str:
        return INCIDENT_STORE_PATH

    def _save_persisted(self) -> None:
        path = self._store_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {}
        for iid, inc in self._incidents.items():
            if inc.status in (IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED, IncidentStatus.MITIGATING):
                data[iid] = inc.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_persisted(self) -> None:
        path = self._store_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for iid, d in data.items():
                inc = Incident(**d)
                self._incidents[iid] = inc
        except (json.JSONDecodeError, IOError):
            pass

    def _transition(self, incident: Incident, target: str,
                    actor: str = "", notes: str = "") -> Incident:
        if not validate_incident_transition(incident.status, target):
            raise ValueError(
                f"Cannot transition incident {incident.incident_id} "
                f"from {incident.status} to {target}"
            )
        incident.status = target
        incident.updated_at = _now()
        if target == IncidentStatus.ACKNOWLEDGED:
            incident.acknowledged_by = actor
            incident.acknowledged_at = _now()
        elif target == IncidentStatus.MITIGATING:
            incident.mitigation_notes = notes
        elif target == IncidentStatus.RESOLVED:
            incident.resolved_by = actor
            incident.resolved_at = _now()
            incident.resolution_notes = notes
        elif target == IncidentStatus.CLOSED:
            incident.closed_by = actor
            incident.closed_at = _now()
        self._save_persisted()
        return incident

    def create_incident(
        self,
        severity: str = "info",
        category: str = "",
        title: str = "",
        description: str = "",
        affected_components: list[str] | None = None,
        affected_symbols: list[str] | None = None,
        affected_orders: list[str] | None = None,
        affected_positions: list[str] | None = None,
        root_event_id: str = "",
        related_event_ids: list[str] | None = None,
        trading_blocked: bool = False,
        requires_human_review: bool = False,
    ) -> Incident:
        """Create a new incident."""
        # Duplicate suppression: don't create if open incident exists for same root_event
        if root_event_id:
            for inc in self._incidents.values():
                if inc.root_event_id == root_event_id and inc.status in (
                    IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED,
                ):
                    return inc

        inc = Incident(
            severity=severity, category=category, title=title,
            description=description,
            affected_components=affected_components or [],
            affected_symbols=affected_symbols or [],
            affected_orders=affected_orders or [],
            affected_positions=affected_positions or [],
            root_event_id=root_event_id,
            related_event_ids=related_event_ids or [],
            trading_blocked=trading_blocked,
            requires_human_review=requires_human_review,
        )
        self._incidents[inc.incident_id] = inc
        self._history.append(inc)
        self._save_persisted()
        return inc

    def acknowledge(self, incident_id: str, reviewer: str = "") -> Incident:
        inc = self._get(incident_id)
        if not reviewer:
            raise ValueError("Reviewer identity required to acknowledge incident")
        return self._transition(inc, IncidentStatus.ACKNOWLEDGED, actor=reviewer)

    def start_mitigation(self, incident_id: str, notes: str = "") -> Incident:
        inc = self._get(incident_id)
        return self._transition(inc, IncidentStatus.MITIGATING, notes=notes)

    def resolve(self, incident_id: str, reviewer: str = "",
                reason: str = "", notes: str = "") -> Incident:
        inc = self._get(incident_id)
        if not reviewer:
            raise ValueError("Reviewer identity required to resolve incident")
        if not reason:
            raise ValueError("Reason required to resolve incident")
        full_notes = f"{reason}. {notes}" if notes else reason
        return self._transition(inc, IncidentStatus.RESOLVED, actor=reviewer, notes=full_notes)

    def close(self, incident_id: str, reviewer: str = "", notes: str = "") -> Incident:
        inc = self._get(incident_id)
        if not reviewer:
            raise ValueError("Reviewer identity required to close incident")
        return self._transition(inc, IncidentStatus.CLOSED, actor=reviewer, notes=notes)

    def _get(self, incident_id: str) -> Incident:
        inc = self._incidents.get(incident_id)
        if not inc:
            raise KeyError(f"Incident {incident_id} not found")
        return inc

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def get_open(self) -> list[Incident]:
        return [
            i for i in self._incidents.values()
            if i.status != IncidentStatus.CLOSED
        ]

    def get_critical(self) -> list[Incident]:
        return [
            i for i in self._incidents.values()
            if i.severity in ("critical", "emergency") and i.status != IncidentStatus.CLOSED
        ]

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [i.summary() for i in self._history[-limit:]]

    def get_all(self) -> list[Incident]:
        return list(self._incidents.values())

    def duplicate_exists(self, root_event_id: str, time_window_minutes: int = 30) -> bool:
        """Check if an open incident exists for the same root cause within time window."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        for inc in self._incidents.values():
            if inc.root_event_id == root_event_id and inc.status != IncidentStatus.CLOSED:
                try:
                    created = datetime.fromisoformat(inc.created_at)
                    if created > cutoff:
                        return True
                except (ValueError, TypeError):
                    return True
        return False

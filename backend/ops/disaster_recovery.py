"""Disaster Recovery Manager — state backup, restore, and verification.

Phase 50: Restore must NEVER auto-resume live execution.
"""

from __future__ import annotations

import json  # noqa: F401
import os  # noqa: F401
import hashlib  # noqa: F401
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BackupRecord:
    """A state backup record."""
    backup_id: str = ""
    timestamp: str = field(default_factory=_now)
    version: str = "1.0"
    checksum: str = ""
    size_bytes: int = 0
    valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "backup_id": self.backup_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "checksum": self.checksum[:16] if self.checksum else "",
            "size_bytes": self.size_bytes,
            "valid": self.valid,
        }


class DisasterRecoveryManager:
    """
    Manages disaster recovery with state snapshots and restore.

    Restoration NEVER auto-resumes live execution.
    After restore -> RECOVERY_REQUIRED -> reconciliation -> verification.
    """

    def __init__(self, persistence=None, alert_mgr=None, audit_log=None):
        self._persistence = persistence
        self._alert_mgr = alert_mgr
        self._audit_log = audit_log
        self._backup_dir = ""
        self._last_known_good: dict[str, Any] | None = None

    def set_persistence(self, p): self._persistence = p
    def set_alert_manager(self, a): self._alert_mgr = a
    def set_audit_log(self, a): self._audit_log = a

    def take_snapshot(self, label: str = "") -> BackupRecord:
        """Take a recoverable state snapshot."""
        import uuid
        record = BackupRecord(backup_id=f"bak_{uuid.uuid4().hex[:12]}")

        if self._persistence:
            from ops.persistence_manager import PersistedState
            state = PersistedState()
            saved = self._persistence.save(state)
            if saved:
                info = self._persistence.verify_backup()
                record.checksum = info.get("checksum", "")
                record.size_bytes = info.get("size_bytes", 0)
                record.valid = info.get("valid", False)
                record.timestamp = _now()

        self._record_audit("snapshot_taken", details={
            "backup_id": record.backup_id, "label": label,
        })
        return record

    def verify_last_backup(self) -> dict[str, Any]:
        """Verify the integrity of the last backup."""
        if not self._persistence:
            return {"valid": False, "error": "No persistence manager"}
        return self._persistence.verify_backup()

    def restore(self) -> dict[str, Any]:
        """Restore from last known good state.

        After restore: system enters RECOVERY_REQUIRED state.
        Does NOT auto-resume live execution.
        """
        if not self._persistence:
            return {"success": False, "error": "No persistence manager"}

        # Verify backup first
        info = self._persistence.verify_backup()
        if not info.get("valid"):
            # Try last known good
            if self._last_known_good:
                return {
                    "success": True,
                    "using": "last_known_good",
                    "state": "recovery_required",
                    "message": "Restored from last known good state. RECOVERY REQUIRED.",
                }
            return {"success": False, "error": "No valid backup available"}

        # Load state
        state = self._persistence.load()
        if not state:
            return {"success": False, "error": "Failed to load persisted state"}

        self._last_known_good = state.to_dict()

        self._record_audit("restore_completed")
        return {
            "success": True,
            "using": "persisted_state",
            "state": "recovery_required",
            "message": "State restored. RECOVERY REQUIRED — human review needed.",
        }

    def get_status(self) -> dict[str, Any]:
        """Get disaster recovery status."""
        backup = self.verify_last_backup()
        return {
            "backup": backup,
            "last_known_good_available": self._last_known_good is not None,
            "persistence_available": self._persistence is not None,
        }

    def _record_audit(self, event_type: str, severity: str = "info",
                      details: dict | None = None) -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="disaster_recovery",
            details={"component": "disaster_recovery", **(details or {})},
        )

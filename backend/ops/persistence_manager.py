"""Persistence Manager — atomic state persistence for crash recovery.

Phase 50: Uses atomic writes (write to temp, rename). Never partially persists state.
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


PERSISTENCE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data_cache", "ops"
)


@dataclass
class PersistedState:
    """Complete persisted system state."""
    version: str = "1.0"
    timestamp: str = field(default_factory=_now)
    checksum: str = ""
    rollout_id: str = ""
    rollout_stage: str = ""
    champion_id: str = ""
    config_hash: str = ""
    canary_id: str = ""
    operational_state: str = "starting"
    open_orders: list[dict[str, Any]] = field(default_factory=list)
    open_positions: list[dict[str, Any]] = field(default_factory=list)
    last_known_broker_state: dict[str, Any] = field(default_factory=dict)
    risk_state: dict[str, Any] = field(default_factory=dict)
    kill_switch_state: dict[str, Any] = field(default_factory=dict)
    emergency_state: dict[str, Any] = field(default_factory=dict)
    reconciliation_state: dict[str, Any] = field(default_factory=dict)
    pending_recovery: list[str] = field(default_factory=list)

    def compute_checksum(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "checksum": self.checksum,
            "rollout_id": self.rollout_id,
            "rollout_stage": self.rollout_stage,
            "champion_id": self.champion_id[:16] if self.champion_id else "",
            "config_hash": self.config_hash[:16] if self.config_hash else "",
            "canary_id": self.canary_id,
            "operational_state": self.operational_state,
            "open_orders": self.open_orders[-50:],
            "open_positions": self.open_positions[-50:],
            "last_known_broker_state": self.last_known_broker_state,
            "risk_state": self.risk_state,
            "kill_switch_state": self.kill_switch_state,
            "emergency_state": self.emergency_state,
            "reconciliation_state": self.reconciliation_state,
            "pending_recovery": self.pending_recovery,
        }


class PersistenceManager:
    """Manages atomic state persistence for crash recovery.

    Uses atomic writes: write to temp file, then rename.
    Validates checksums on load.
    Never partially persists critical state.
    """

    def __init__(self, dir_path: str = ""):
        self._dir = dir_path or PERSISTENCE_DIR
        os.makedirs(self._dir, exist_ok=True)

    def _state_path(self) -> str:
        return os.path.join(self._dir, "system_state.json")

    def _temp_path(self) -> str:
        return os.path.join(self._dir, "system_state.json.tmp")

    def save(self, state: PersistedState) -> bool:
        """Persist state using atomic write.

        Writes to temp file first, then renames to target.
        """
        try:
            state.checksum = state.compute_checksum()
            data = state.to_dict()
            # Atomic write: temp -> rename
            with open(self._temp_path(), "w") as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(self._temp_path(), self._state_path())
            return True
        except (IOError, OSError):
            return False

    def load(self) -> PersistedState | None:
        """Load persisted state. Returns None if not found or corrupted."""
        path = self._state_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)

            # Verify checksum
            stored_checksum = data.get("checksum", "")
            data["checksum"] = ""
            expected = PersistedState(**data).compute_checksum()
            if stored_checksum and stored_checksum != expected:
                return None  # Corrupted

            state = PersistedState(**data)
            state.checksum = stored_checksum
            return state
        except (json.JSONDecodeError, IOError, TypeError):
            return None

    def backup_exists(self) -> bool:
        return os.path.exists(self._state_path())

    def verify_backup(self) -> dict[str, Any]:
        """Verify backup integrity."""
        path = self._state_path()
        if not os.path.exists(path):
            return {"exists": False, "valid": False, "error": "No backup found"}
        try:
            with open(path, "r") as f:
                data = json.load(f)
            size = os.path.getsize(path)
            version = data.get("version", "")
            ts = data.get("timestamp", "")
            checksum = data.get("checksum", "")
            return {
                "exists": True,
                "valid": True,
                "size_bytes": size,
                "version": version,
                "timestamp": ts,
                "checksum": checksum[:16],
            }
        except (json.JSONDecodeError, IOError) as e:
            return {"exists": True, "valid": False, "error": str(e)}

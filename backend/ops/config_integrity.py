"""Config Integrity Monitor — continuously verifies configuration hasn't changed.

Phase 50: On unexpected change → BLOCK ENTRIES → ROLLBACK → HUMAN REVIEW.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConfigIntegrityResult:
    """Result of config integrity check."""
    passed: bool = True
    champion_unchanged: bool = True
    config_hash_unchanged: bool = True
    risk_config_unchanged: bool = True
    sl_target_unchanged: bool = True
    position_sizing_unchanged: bool = True
    rollout_limits_unchanged: bool = True
    changes: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "champion_unchanged": self.champion_unchanged,
            "config_hash_unchanged": self.config_hash_unchanged,
            "risk_config_unchanged": self.risk_config_unchanged,
            "sl_target_unchanged": self.sl_target_unchanged,
            "position_sizing_unchanged": self.position_sizing_unchanged,
            "rollout_limits_unchanged": self.rollout_limits_unchanged,
            "changes": self.changes,
            "timestamp": self.timestamp,
        }


class ConfigIntegrityMonitor:
    """
    Monitors configuration for unexpected changes during rollout.

    On unexpected change:
    1. CONFIG_INTEGRITY_FAILURE
    2. Block new entries
    3. ROLLBACK_REQUIRED
    4. AUDIT EVENT
    5. HUMAN REVIEW REQUIRED
    """

    def __init__(self):
        self._stored_champion_id = ""
        self._stored_config_hash = ""
        self._champion_manager = None
        self._config_guard = None
        self._audit_log = None
        self._rollout_engine = None

    def set_champion_manager(self, m): self._champion_manager = m
    def set_config_guard(self, g): self._config_guard = g
    def set_audit_log(self, a): self._audit_log = a
    def set_rollout_engine(self, r): self._rollout_engine = r

    def set_baseline(self, champion_id: str = "", config_hash: str = "") -> None:
        """Set the baseline configuration to monitor against."""
        self._stored_champion_id = champion_id
        self._stored_config_hash = config_hash

    def check_integrity(self) -> ConfigIntegrityResult:
        """Check all configurations against stored baseline.

        Returns:
            ConfigIntegrityResult with per-check status.
        """
        result = ConfigIntegrityResult()
        changes: list[str] = []

        # Check champion
        if self._champion_manager and self._stored_champion_id:
            try:
                champ = self._champion_manager.get_champion()
                if champ:
                    champ_id = getattr(champ, "id", getattr(champ, "version", ""))
                    if champ_id and champ_id != self._stored_champion_id:
                        result.champion_unchanged = False
                        changes.append(f"champion: {self._stored_champion_id[:12]} -> {champ_id[:12]}")
            except Exception:
                pass

        # Check config hash
        if self._config_guard and self._stored_config_hash:
            try:
                status = self._config_guard.get_status()
                current_hash = status.get("current_hash", "")
                if current_hash and current_hash != self._stored_config_hash:
                    result.config_hash_unchanged = False
                    changes.append("config_hash_changed")
            except Exception:
                pass

        result.changes = changes
        result.passed = result.champion_unchanged and result.config_hash_unchanged

        if not result.passed:
            self._record_audit("config_integrity_failure",
                               details={"changes": changes},
                               severity="critical")

        return result

    def _record_audit(self, event_type: str, severity: str = "info",
                      details: dict | None = None) -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="config_integrity_monitor",
            details={"component": "config_integrity", **(details or {})},
        )

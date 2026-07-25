"""Configuration Guard — detects configuration drift after final approval."""

from __future__ import annotations
from typing import Any

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


CONFIGURATION_DRIFT_DETECTED = "configuration_drift_detected"


@dataclass
class ConfigurationSnapshot:
    """Immutable snapshot of configuration at approval time."""
    champion_strategy: dict[str, Any] = field(default_factory=dict)
    risk_configuration: dict[str, Any] = field(default_factory=dict)
    execution_parameters: dict[str, Any] = field(default_factory=dict)
    sl_target_rules: dict[str, Any] = field(default_factory=dict)
    position_sizing: dict[str, Any] = field(default_factory=dict)
    allowed_symbols: list[str] = field(default_factory=list)
    trading_session: dict[str, Any] = field(default_factory=dict)
    loss_limits: dict[str, Any] = field(default_factory=dict)
    drawdown_limits: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def compute_hash(self) -> str:
        """Compute deterministic hash of all configuration fields."""
        raw = json.dumps({
            "champion_strategy": self._sorted(self.champion_strategy),
            "risk_configuration": self._sorted(self.risk_configuration),
            "execution_parameters": self._sorted(self.execution_parameters),
            "sl_target_rules": self._sorted(self.sl_target_rules),
            "position_sizing": self._sorted(self.position_sizing),
            "allowed_symbols": sorted(self.allowed_symbols),
            "trading_session": self._sorted(self.trading_session),
            "loss_limits": self._sorted(self.loss_limits),
            "drawdown_limits": self._sorted(self.drawdown_limits),
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _sorted(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: ConfigurationSnapshot._sorted(v) for k, v in sorted(obj.items())}
        if isinstance(obj, list):
            try:
                return sorted(obj, key=str)
            except TypeError:
                return obj
        return obj

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.compute_hash(),
            "champion_strategy": self.champion_strategy,
            "risk_configuration": self.risk_configuration,
            "execution_parameters": self.execution_parameters,
            "sl_target_rules": self.sl_target_rules,
            "position_sizing": self.position_sizing,
            "allowed_symbols": self.allowed_symbols,
            "trading_session": self.trading_session,
            "loss_limits": self.loss_limits,
            "drawdown_limits": self.drawdown_limits,
            "timestamp": self.timestamp,
        }


class ConfigGuard:
    """
    Monitors configuration for drift after final approval.
    If configuration changes, invalidates the live-review approval and blocks execution.
    """

    def __init__(self):
        self._approval_snapshot: ConfigurationSnapshot | None = None
        self._current_snapshot: ConfigurationSnapshot | None = None
        self._drift_detected = False
        self._drift_reason: str = ""

    def capture_approval_snapshot(self, config: ConfigurationSnapshot):
        """Capture configuration at the time of final approval."""
        self._approval_snapshot = config
        self._current_snapshot = config
        self._drift_detected = False
        self._drift_reason = ""

    def check_for_drift(self, current_config: ConfigurationSnapshot) -> bool:
        """
        Compare current config against approval config.
        Returns True if drift is detected.
        """
        self._current_snapshot = current_config
        if self._approval_snapshot is None:
            self._drift_detected = True
            self._drift_reason = "No approval snapshot captured"
            return True

        approval_hash = self._approval_snapshot.compute_hash()
        current_hash = current_config.compute_hash()

        if approval_hash != current_hash:
            self._drift_detected = True
            self._drift_reason = f"Configuration hash changed: {approval_hash} -> {current_hash}"
            return True

        self._drift_detected = False
        self._drift_reason = ""
        return False

    def has_drift(self) -> bool:
        return self._drift_detected

    def get_drift_reason(self) -> str:
        return self._drift_reason

    def get_status(self) -> dict[str, Any]:
        return {
            "has_approval_snapshot": self._approval_snapshot is not None,
            "has_current_snapshot": self._current_snapshot is not None,
            "drift_detected": self._drift_detected,
            "drift_reason": self._drift_reason,
            "approval_hash": self._approval_snapshot.compute_hash() if self._approval_snapshot else "",
            "current_hash": self._current_snapshot.compute_hash() if self._current_snapshot else "",
        }

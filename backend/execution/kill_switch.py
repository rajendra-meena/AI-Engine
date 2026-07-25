"""Multi-level kill switch for execution safety."""

from __future__ import annotations
from typing import Any

from datetime import datetime, timezone
from enum import Enum


class KillSwitchLevel(str, Enum):
    GLOBAL = "global"
    ACCOUNT = "account"
    STRATEGY = "strategy"
    SYMBOL = "symbol"
    SESSION = "session"


class KillSwitchState(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIGGERED = "triggered"
    RECOVERING = "recovering"


class KillSwitch:
    """Centralized kill switch with multiple levels."""

    def __init__(self):
        self._switches: dict[str, dict[str, Any]] = {}

    def _get_key(self, level: KillSwitchLevel, name: str = "") -> str:
        return f"{level.value}:{name}" if name else level.value

    def activate(
        self,
        level: KillSwitchLevel = KillSwitchLevel.GLOBAL,
        name: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        key = self._get_key(level, name)
        entry = {
            "key": key,
            "level": level.value,
            "state": KillSwitchState.ACTIVE.value,
            "reason": reason,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._switches[key] = entry
        return entry

    def trigger(
        self,
        level: KillSwitchLevel = KillSwitchLevel.GLOBAL,
        name: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        key = self._get_key(level, name)
        entry = {
            "key": key,
            "level": level.value,
            "state": KillSwitchState.TRIGGERED.value,
            "reason": reason,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._switches[key] = entry
        return entry

    def reset(self, level: KillSwitchLevel = KillSwitchLevel.GLOBAL, name: str = ""):
        key = self._get_key(level, name)
        self._switches.pop(key, None)

    def is_active(
        self,
        level: KillSwitchLevel = KillSwitchLevel.GLOBAL,
        name: str = "",
    ) -> bool:
        key = self._get_key(level, name)
        entry = self._switches.get(key)
        if entry and entry["state"] in (KillSwitchState.ACTIVE.value, KillSwitchState.TRIGGERED.value):
            return True
        # Global kills all sub-levels
        if level != KillSwitchLevel.GLOBAL:
            global_key = self._get_key(KillSwitchLevel.GLOBAL)
            global_entry = self._switches.get(global_key)
            if global_entry and global_entry["state"] in (
                KillSwitchState.ACTIVE.value, KillSwitchState.TRIGGERED.value
            ):
                return True
        return False

    def get_active_switches(self) -> list[dict[str, Any]]:
        return [
            v for v in self._switches.values()
            if v["state"] in (KillSwitchState.ACTIVE.value, KillSwitchState.TRIGGERED.value)
        ]

    def get_status(self) -> dict[str, Any]:
        return {
            "active": self.is_active(),
            "active_count": len(self.get_active_switches()),
            "switches": self.get_active_switches(),
            "blocking_execution": self.is_active(),
        }

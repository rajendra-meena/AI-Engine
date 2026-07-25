"""
Runtime Mode — strict execution mode with safety guards.
Phase 39: only OBSERVE and SHADOW allowed.
"""

from __future__ import annotations

from enum import Enum


class RuntimeMode(str, Enum):
    OBSERVE = "observe"
    SHADOW = "shadow"
    PAPER = "paper"
    LIVE = "live"


# Phase 39 hard-coded allowed modes
ALLOWED_MODES = {RuntimeMode.OBSERVE, RuntimeMode.SHADOW}


class RuntimeModeManager:
    """Manages runtime mode with strict safety enforcement."""

    def __init__(self):
        self._mode = RuntimeMode.OBSERVE
        self._phase_39_lock = True  # Hard lock for Phase 39

    @property
    def mode(self) -> RuntimeMode:
        return self._mode

    def set_mode(self, mode: str) -> dict:
        """Set runtime mode. PAPER and LIVE are always blocked in Phase 39."""
        try:
            new_mode = RuntimeMode(mode)
        except ValueError:
            return {"success": False, "message": f"Unknown mode: {mode}"}

        if new_mode not in ALLOWED_MODES:
            return {"success": False, "message": f"Mode '{mode}' is disabled in this phase"}

        self._mode = new_mode
        return {"success": True, "mode": self._mode.value}

    def is_observe(self) -> bool:
        return self._mode == RuntimeMode.OBSERVE

    def is_shadow(self) -> bool:
        return self._mode == RuntimeMode.SHADOW

    def is_paper(self) -> bool:
        return self._mode == RuntimeMode.PAPER

    def is_live(self) -> bool:
        return self._mode == RuntimeMode.LIVE

    def can_execute_live(self) -> bool:
        return False  # Phase 39: NEVER

    def can_execute_paper(self) -> bool:
        return False  # Phase 39: NEVER

    def get_status(self) -> dict:
        return {
            "mode": self._mode.value,
            "observe": self.is_observe(),
            "shadow": self.is_shadow(),
            "paper_enabled": self.is_paper(),
            "live_enabled": False,
            "phase_39_lock": self._phase_39_lock,
            "allowed_modes": [m.value for m in ALLOWED_MODES],
        }

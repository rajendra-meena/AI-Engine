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
    CONTROLLED_LIVE = "controlled_live"


# Phase 39 hard-coded allowed modes + CONTROLLED_LIVE for Phase 54
ALLOWED_MODES = {RuntimeMode.OBSERVE, RuntimeMode.SHADOW}
CONTROLLED_LIVE_ENABLED = False  # Set True during authorized controlled live session


class RuntimeModeManager:
    """Manages runtime mode with strict safety enforcement."""

    def __init__(self):
        self._mode = RuntimeMode.OBSERVE
        self._phase_39_lock = True  # Hard lock for Phase 39
        self._controlled_live_active = False

    @property
    def mode(self) -> RuntimeMode:
        return self._mode

    def set_mode(self, mode: str) -> dict:
        """Set runtime mode. PAPER and LIVE are always blocked in Phase 39."""
        try:
            new_mode = RuntimeMode(mode)
        except ValueError:
            return {"success": False, "message": f"Unknown mode: {mode}"}

        if new_mode not in ALLOWED_MODES and new_mode != RuntimeMode.PAPER:
            # CONTROLLED_LIVE is set via dedicated method
            if new_mode == RuntimeMode.CONTROLLED_LIVE:
                return {"success": False, "message": "Use activate_controlled_live() to enable controlled live mode"}
            return {"success": False, "message": f"Mode '{mode}' is disabled in this phase"}

        self._mode = new_mode
        return {"success": True, "mode": self._mode.value}

    def activate_controlled_live(self) -> dict:
        """Activate controlled live mode. Validated by caller."""
        self._mode = RuntimeMode.CONTROLLED_LIVE
        self._controlled_live_active = True
        return {"success": True, "mode": self._mode.value}

    def deactivate_controlled_live(self) -> dict:
        """Deactivate controlled live mode. Returns to OBSERVE."""
        self._mode = RuntimeMode.OBSERVE
        self._controlled_live_active = False
        return {"success": True, "mode": self._mode.value}

    def is_controlled_live_active(self) -> bool:
        return self._controlled_live_active

    def is_observe(self) -> bool:
        return self._mode == RuntimeMode.OBSERVE

    def is_shadow(self) -> bool:
        return self._mode == RuntimeMode.SHADOW

    def is_paper(self) -> bool:
        return self._mode == RuntimeMode.PAPER

    def is_live(self) -> bool:
        return self._mode == RuntimeMode.LIVE

    def can_execute_live(self) -> bool:
        # Phase 39: NEVER for LIVE mode
        # Phase 54: CONTROLLED_LIVE allows one trade through safety gate
        return self._controlled_live_active

    def can_execute_paper(self) -> bool:
        return False  # Phase 39: NEVER

    def get_status(self) -> dict:
        return {
            "mode": self._mode.value,
            "observe": self.is_observe(),
            "shadow": self.is_shadow(),
            "paper_enabled": self.is_paper(),
            "live_enabled": False,
            "controlled_live_active": self._controlled_live_active,
            "phase_39_lock": self._phase_39_lock,
            "allowed_modes": [m.value for m in ALLOWED_MODES],
        }

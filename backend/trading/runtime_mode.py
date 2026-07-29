"""
Runtime Mode — strict execution mode with safety guards.
Phase 39: only OBSERVE and SHADOW allowed.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from enum import Enum


class RuntimeMode(str, Enum):
    OBSERVE = "observe"
    SHADOW = "shadow"
    PAPER = "paper"
    LIVE = "live"
    CONTROLLED_LIVE = "controlled_live"


# Allowed modes: OBSERVE, SHADOW, and PAPER (paper trading active)
ALLOWED_MODES = {RuntimeMode.OBSERVE, RuntimeMode.SHADOW, RuntimeMode.PAPER}
CONTROLLED_LIVE_ENABLED = False  # Set True during authorized controlled live session


class RuntimeModeManager:
    """Manages runtime mode with strict safety enforcement.
    Default mode is PAPER for zero-config paper trading.
    Mode persists in a file so restart returns to the last safe mode.
    """

    def __init__(self, persist_path: str = ""):
        self._mode = RuntimeMode.PAPER
        self._persist_path = persist_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data_cache",
            "runtime_mode.json",
        )
        self._phase_39_lock = True  # Hard lock for Phase 39
        self._controlled_live_active = False
        self._load()

    def _load(self):
        """Load persisted mode if available."""
        try:
            if os.path.exists(self._persist_path):
                import json
                with open(self._persist_path) as f:
                    data = json.load(f)
                    mode_str = data.get("mode", "paper")
                    self._mode = RuntimeMode(mode_str)
        except Exception:
            self._mode = RuntimeMode.PAPER

    def _save(self):
        """Persist current mode."""
        try:
            import json
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, "w") as f:
                json.dump({"mode": self._mode.value, "updated_at": datetime.now(timezone.utc).isoformat()}, f)
        except Exception:
            pass

    @property
    def mode(self) -> RuntimeMode:
        return self._mode

    def set_mode(self, mode: str) -> dict:
        """Set runtime mode. PAPER and LIVE are always blocked in Phase 39."""
        try:
            new_mode = RuntimeMode(mode)
        except ValueError:
            return {"success": False, "message": f"Unknown mode: {mode}"}

        if new_mode == RuntimeMode.CONTROLLED_LIVE:
            return {"success": False, "message": "Use activate_controlled_live() to enable controlled live mode"}
        if new_mode not in ALLOWED_MODES:
            return {"success": False, "message": f"Mode '{mode}' is disabled in this phase"}

        self._mode = new_mode
        self._save()
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
        return self._mode == RuntimeMode.PAPER

    def reset_to_paper_default(self) -> dict:
        """Reset to paper trading default mode."""
        self._mode = RuntimeMode.PAPER
        self._controlled_live_active = False
        self._save()
        return {"success": True, "mode": self._mode.value}

    def get_status(self) -> dict:
        return {
            "mode": self._mode.value,
            "observe": self.is_observe(),
            "shadow": self.is_shadow(),
            "paper_enabled": self.is_paper(),
            "paper": self.is_paper(),
            "live_enabled": False,
            "controlled_live_active": self._controlled_live_active,
            "phase_39_lock": self._phase_39_lock,
            "allowed_modes": [m.value for m in ALLOWED_MODES],
        }

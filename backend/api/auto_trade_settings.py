"""
Auto Trade Settings — authoritative backend-persisted user settings for /auto-trade.

All settings survive engine stop/start and backend restart.
GET /api/auto-trade/settings — read all settings
PATCH /api/auto-trade/settings — partial update, returns full authoritative state
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException
from utils.logger import log_info

router = APIRouter(tags=["auto-trade"])

_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data_cache",
    "auto_trade_settings.json",
)


class ExecutionType(str, Enum):
    SYNTHETIC_SPOT = "synthetic_spot"
    OPTION_BUYING = "option_buying"


class LotMode(str, Enum):
    MANUAL = "manual"
    AUTO_RISK_BASED = "auto_risk_based"


class StrikeMode(str, Enum):
    ATM = "ATM"


class ExpiryMode(str, Enum):
    NEAREST_WEEKLY = "NEAREST_WEEKLY"


class PremiumSource(str, Enum):
    ZERODHA = "ZERODHA"
    SIMULATED = "SIMULATED"


@dataclass
class AutoTradeSettings:
    market_universe: str = "all"
    max_trades_per_day: int = 20
    min_ai_confidence: int = 40
    min_trade_grade: str = "C"
    min_risk_reward: float = 1.5
    allow_buy_trades: bool = True
    allow_sell_trades: bool = True
    auto_execute_paper_trades: bool = True
    execution_type: str = "option_buying"
    lot_mode: str = "manual"
    manual_lots: int = 1
    max_auto_lots: int = 20
    strike_mode: str = "ATM"
    expiry_mode: str = "NEAREST_WEEKLY"
    premium_source: str = "ZERODHA"
    settings_version: int = 1
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> list[str]:
        errors = []
        if not (1 <= self.manual_lots <= 20):
            errors.append(f"manual_lots must be 1-20, got {self.manual_lots}")
        if not (1 <= self.max_auto_lots <= 100):
            errors.append(f"max_auto_lots must be 1-100, got {self.max_auto_lots}")
        if self.max_trades_per_day < 1:
            errors.append(f"max_trades_per_day must be >= 1")
        if self.min_ai_confidence < 0 or self.min_ai_confidence > 100:
            errors.append(f"min_ai_confidence must be 0-100")
        return errors


# ── Singleton settings store ──

_settings: AutoTradeSettings | None = None


def _load_settings() -> AutoTradeSettings:
    """Load from file or return defaults."""
    try:
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE) as f:
                data = json.load(f)
            # Filter to only known fields
            valid = AutoTradeSettings()
            for k in asdict(valid):
                if k in data:
                    setattr(valid, k, data[k])
            log_info("AutoTrade: settings loaded", file=_SETTINGS_FILE)
            return valid
    except Exception as e:
        log_info("AutoTrade: settings load failed, using defaults", error=str(e))
    return AutoTradeSettings()


def _save_settings(s: AutoTradeSettings):
    """Persist to file."""
    os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
    s.updated_at = datetime.now(timezone.utc).isoformat()
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(s.to_dict(), f, indent=2, default=str)
    log_info("AutoTrade: settings saved", file=_SETTINGS_FILE)


def get_settings() -> AutoTradeSettings:
    global _settings
    if _settings is None:
        _settings = _load_settings()
    return _settings


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    global _settings
    s = get_settings()
    allowed = set(asdict(AutoTradeSettings()).keys()) - {"settings_version", "updated_at"}
    for k, v in updates.items():
        if k in allowed:
            setattr(s, k, v)
    errs = s.validate()
    if errs:
        return {"success": False, "errors": errs}
    _settings = s
    _save_settings(s)
    return {"success": True, **s.to_dict()}


def reset_settings():
    global _settings
    _settings = AutoTradeSettings()
    _save_settings(_settings)


# ── API Routes ──


@router.get("/api/auto-trade/settings")
async def auto_trade_get_settings():
    return get_settings().to_dict()


@router.patch("/api/auto-trade/settings")
async def auto_trade_patch_settings(payload: dict):
    result = update_settings(payload)
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("errors", ["Invalid settings"]))
    return result
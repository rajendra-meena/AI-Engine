"""
Execution Configuration — controls which execution model is active.

Synthetic Spot: original model (index price × quantity)
Option Buying: premium-based option execution

Both paths coexist. Toggle via API or config.
"""

from __future__ import annotations

from enum import Enum


class ExecutionType(str, Enum):
    SYNTHETIC_SPOT = "synthetic_spot"
    OPTION_BUYING = "option_buying"


# Global execution config (singleton, mutable at runtime)
_execution_config: dict = {
    "execution_type": ExecutionType.OPTION_BUYING,
}


def get_execution_type() -> ExecutionType:
    """Get the current execution type."""
    return _execution_config.get("execution_type", ExecutionType.OPTION_BUYING)


def set_execution_type(execution_type: str) -> dict:
    """Set the execution type. Returns result dict."""
    try:
        et = ExecutionType(execution_type.lower().strip())
    except ValueError:
        return {"success": False, "message": f"Unknown execution type: {execution_type}"}
    _execution_config["execution_type"] = et
    return {"success": True, "execution_type": et.value}


def is_option_buying() -> bool:
    """True when option buying execution is active."""
    return get_execution_type() == ExecutionType.OPTION_BUYING


def is_synthetic_spot() -> bool:
    """True when synthetic spot execution is active."""
    return get_execution_type() == ExecutionType.SYNTHETIC_SPOT
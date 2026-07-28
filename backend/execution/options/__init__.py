"""
Option Buying Execution Module.

Bridge between AI TradePlan and option-specific execution.
Uses existing backend/options/ infrastructure for chain/premium data.
"""

from execution.options.planner import OptionExecutionPlanner
from execution.options.models import OptionExecutionPlan

__all__ = [
    "OptionExecutionPlanner",
    "OptionExecutionPlan",
]
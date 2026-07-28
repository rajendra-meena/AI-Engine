"""
Option Execution Planner — converts TradePlan into option-specific execution.
"""

from __future__ import annotations

from typing import Any

from execution.options.models import OptionExecutionPlan
from execution.options.selector import OptionSelector
from execution.options.premium import PremiumFetcher
from execution.options.sizing import LotSizer
from execution.execution_config import is_option_buying
from utils.logger import log_info


class OptionExecutionPlanner:
    """
    Builds an option execution plan from a TradePlan.

    Called after TradePlanner.build_plan() in the execution pipeline.
    """

    @staticmethod
    async def execute(
        symbol: str,
        direction: str,
        underlying_price: float,
        underlying_sl: float | None = None,
        underlying_target: float | None = None,
        capital: float = 100000.0,
        risk_percent: float = 2.0,
    ) -> OptionExecutionPlan | None:
        """
        Build a complete option execution plan.

        Steps:
          1. Select option contract (expiry, strike, type)
          2. Fetch premium (Zerodha or simulated)
          3. Size position (lots from risk budget)
          4. Compute premium-level SL and target
          5. Return OptionExecutionPlan
        """
        if not is_option_buying():
            return None

        # 1. Select option contract
        selection = OptionSelector.select(symbol, direction, underlying_price)
        option_type = selection["option_type"]
        expiry = selection["expiry"]
        strike = selection["strike"]
        lot_size = selection["lot_size"]

        # 2. Fetch premium
        premium_data = await PremiumFetcher.fetch_premium(
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            underlying_price=underlying_price,
        )
        premium = premium_data["premium"]

        # 3. Estimate premium-level SL (premium loss equal to underlying stop distance %)
        if underlying_sl and underlying_price > 0:
            underlying_risk_pct = abs(underlying_price - underlying_sl) / underlying_price
            premium_sl = round(premium * (1 - underlying_risk_pct), 2)
        else:
            premium_sl = round(premium * 0.8, 2)  # default 20% premium stop

        # 4. Estimate premium-level target (same R:R as underlying)
        if underlying_sl and underlying_target and underlying_price > 0:
            underlying_rr = abs(underlying_target - underlying_price) / abs(underlying_price - underlying_sl)
            premium_target = round(premium + (premium - premium_sl) * underlying_rr, 2)
        else:
            premium_target = round(premium * 1.5, 2)  # default 50% premium target

        # 5. Size position in lots
        sizing = LotSizer.compute(
            capital=capital,
            risk_percent=risk_percent,
            premium_entry=premium,
            premium_sl=premium_sl,
            lot_size=lot_size,
        )

        plan = OptionExecutionPlan(
            underlying_symbol=symbol,
            direction=direction,
            option_type=option_type,
            expiry=expiry,
            strike=strike,
            strike_interval=OptionSelector.get_strike_interval(symbol),
            expiry_type="weekly",
            execution_symbol=f"{symbol} {strike:.0f} {option_type} {expiry}",
            lot_size=lot_size,
            lots=sizing["lots"],
            premium=premium,
            premium_source=premium_data.get("source", "simulated"),
            total_cost=sizing["total_cost"],
            capital_required=sizing["capital_required"],
            underlying_entry=underlying_price,
            underlying_sl=underlying_sl or 0,
            underlying_target=underlying_target or 0,
            premium_entry=premium,
            premium_sl=premium_sl,
            premium_target=premium_target,
            risk_per_lot=sizing["risk_per_lot"],
        )

        log_info("OptionExecutionPlan created",
                 symbol=symbol,
                 option=f"{strike:.0f}{option_type}",
                 lots=sizing["lots"],
                 premium=premium,
                 total_cost=sizing["total_cost"],
                 source=plan.premium_source)

        return plan
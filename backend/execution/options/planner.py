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
from utils.logger import log_info, log_warn


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
        override_plan: dict[str, Any] | None = None,
        premium_source: str | None = None,
    ) -> OptionExecutionPlan | None:
        """
        Build a complete option execution plan.

        Steps:
          1. Select option contract (expiry, strike, type)
          2. Fetch premium (Zerodha or simulated)
          3. Size position (lots from risk budget)
          4. Compute premium-level SL and target
          5. Return OptionExecutionPlan

        When override_plan is provided, its values take precedence over
        selection/fetch/sizing for controlled testing.

        When premium_source='ZERODHA' and override_plan is None,
        a real Zerodha quote is required — simulated fallback is blocked.
        """
        if not is_option_buying():
            return None

        # 1. Select option contract (use override if provided)
        if override_plan and "option_type" in override_plan and "strike" in override_plan:
            option_type = override_plan["option_type"]
            expiry = override_plan.get("expiry", "")
            strike = override_plan["strike"]
            lot_size = override_plan.get("lot_size", 50)
        else:
            selection = OptionSelector.select(symbol, direction, underlying_price)
            option_type = selection["option_type"]
            expiry = selection["expiry"]
            strike = selection["strike"]
            lot_size = selection["lot_size"]

        # 2. Fetch premium (use override if provided)
        if override_plan and "premium" in override_plan:
            premium = override_plan["premium"]
            premium_sl = override_plan.get("premium_sl", round(premium * 0.8, 2))
            premium_target = override_plan.get("premium_target", round(premium * 1.5, 2))
            premium_source = override_plan.get("premium_source", "CONTROLLED_TEST_FIXTURE")
        else:
            effective_source = premium_source or "ZERODHA"
            premium_data = await PremiumFetcher.fetch_premium(
                symbol=symbol,
                option_type=option_type,
                strike=strike,
                underlying_price=underlying_price,
                expiry=expiry,
                lot_size=lot_size,
                source=effective_source,
                trading_symbol=selection.get("trading_symbol", ""),
                instrument_token=selection.get("instrument_token", 0),
            )
            premium = premium_data.get("premium", 0.0)
            if premium <= 0:
                error_detail = premium_data.get("error_detail", "Premium unavailable")
                log_warn("OptionExecutionPlanner: premium fetch failed",
                         symbol=symbol, source=effective_source, error=error_detail)
                return None
            premium_source = premium_data.get("source", effective_source)

        # 3. Premium-level SL (use override or compute)
        if not (override_plan and ("premium_sl" in override_plan or "premium_target" in override_plan)):
            if underlying_sl and underlying_price > 0:
                underlying_risk_pct = abs(underlying_price - underlying_sl) / underlying_price
                premium_sl = round(premium * (1 - underlying_risk_pct), 2)
            else:
                premium_sl = round(premium * 0.8, 2)

            # 4. Premium-level target
            if underlying_sl and underlying_target and underlying_price > 0:
                underlying_rr = abs(underlying_target - underlying_price) / abs(underlying_price - underlying_sl)
                premium_target = round(premium + (premium - premium_sl) * underlying_rr, 2)
            else:
                premium_target = round(premium * 1.5, 2)

        # 5. Size position in lots (use override if provided)
        if override_plan and "lots" in override_plan:
            override_lots = override_plan["lots"]
            sizing = {
                "lots": override_lots,
                "total_cost": premium * lot_size * override_lots,
                "capital_required": premium * lot_size * override_lots,
                "risk_per_lot": (premium - premium_sl) * lot_size,
            }
        else:
            sizing = LotSizer.compute(
                capital=capital,
                risk_percent=risk_percent,
                premium_entry=premium,
                premium_sl=premium_sl,
                lot_size=lot_size,
            )

        # Build execution_symbol
        if override_plan and "execution_symbol" in override_plan:
            exec_symbol = override_plan["execution_symbol"]
        else:
            exec_symbol = f"{symbol} {strike:.0f} {option_type} {expiry}"

        # Instrument token
        instr_token = override_plan.get("instrument_token", 0) if override_plan else 0

        plan = OptionExecutionPlan(
            underlying_symbol=symbol,
            direction=direction,
            option_type=option_type,
            expiry=expiry,
            strike=strike,
            strike_interval=OptionSelector.get_strike_interval(symbol) if not override_plan else "",
            expiry_type="weekly",
            execution_symbol=exec_symbol,
            lot_size=lot_size,
            lots=sizing["lots"],
            premium=premium,
            premium_source=premium_source,
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
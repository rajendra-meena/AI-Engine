"""
Runtime Orchestrator — ties champion strategy to market data through the production pipeline.
Enforces runtime mode (OBSERVE/SHADOW). NEVER calls broker execution in Phase 39.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trading.runtime_mode import RuntimeModeManager, RuntimeMode
from trading.champion_runtime import ChampionRuntimeResolver
from trading.shadow_tracker import ShadowTradeTracker
from risk.risk_engine import RiskEngine
from risk.trade_validator import TradeIntent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeOrchestrator:
    """
    Coordinates champion strategy execution through the production pipeline.
    Enforces runtime mode restrictions.
    """

    def __init__(
        self,
        champion_resolver: ChampionRuntimeResolver | None = None,
        mode_manager: RuntimeModeManager | None = None,
        shadow_tracker: ShadowTradeTracker | None = None,
        risk_engine: RiskEngine | None = None,
    ):
        self._champion_resolver = champion_resolver
        self._mode_manager = mode_manager or RuntimeModeManager()
        self._shadow_tracker = shadow_tracker
        self._risk_engine = risk_engine
        self._decisions: list[dict] = []

    def set_champion_resolver(self, r: ChampionRuntimeResolver):
        self._champion_resolver = r

    def set_shadow_tracker(self, t: ShadowTradeTracker):
        self._shadow_tracker = t

    def set_risk_engine(self, e: RiskEngine):
        self._risk_engine = e

    def process_decision(
        self,
        symbol: str,
        direction: str = "WAIT",
        ai_score: int = 0,
        ai_confidence: int = 0,
        market_regime: str = "",
        entry_price: float | None = None,
        stop_loss: float | None = None,
        target: float | None = None,
        quantity: int = 1,
        decision_id: str = "",
        trade_plan_id: str = "",
        timeframe: str = "15m",
        data_freshness: str = "live",
    ) -> dict[str, Any]:
        """Process a decision through the champion runtime pipeline."""
        mode = self._mode_manager.mode
        _ = self._mode_manager.get_status()

        # Resolve champion
        champion = None
        if self._champion_resolver:
            champion = self._champion_resolver.resolve_for_symbol(symbol)

        strat_version_id = ""
        if champion:
            strat_version_id = champion.get("strategy_version_id", "")

        # Record decision
        decision_record = {
            "timestamp": _now(),
            "symbol": symbol,
            "direction": direction,
            "ai_score": ai_score,
            "ai_confidence": ai_confidence,
            "strategy_version_id": strat_version_id,
            "runtime_mode": mode.value,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "decision_id": decision_id,
            "trade_plan_id": trade_plan_id,
        }
        self._decisions.append(decision_record)

        # OBSERVE mode: record only, no execution
        if mode == RuntimeMode.OBSERVE:
            return {
                "mode": "observe",
                "action": "recorded",
                "champion": champion,
                "decision": direction,
                "message": "Observe mode: decision recorded, no execution",
                "strategy_version_id": strat_version_id,
            }

        # SHADOW mode: create virtual trade
        if mode == RuntimeMode.SHADOW:
            if direction not in ("BUY", "SELL"):
                return {
                    "mode": "shadow",
                    "action": "skipped",
                    "reason": f"Direction is {direction}, not BUY or SELL",
                    "strategy_version_id": strat_version_id,
                }

            if data_freshness in ("stale", "disconnected"):
                return {
                    "mode": "shadow",
                    "action": "blocked",
                    "reason": "Market data is stale or disconnected",
                    "strategy_version_id": strat_version_id,
                }

            if not entry_price or entry_price <= 0:
                return {
                    "mode": "shadow",
                    "action": "blocked",
                    "reason": "Invalid entry price",
                    "strategy_version_id": strat_version_id,
                }

            # Validate through RiskEngine (must pass)
            if self._risk_engine:
                side = "BUY" if direction in ("BUY", "LONG") else "SELL"
                intent = TradeIntent(
                    symbol=symbol, side=side, quantity=quantity,
                    price=entry_price, order_type="MARKET", product="MIS",
                    exchange="NSE", strategy="champion_shadow",
                    ai_score=float(ai_score), ai_confidence=float(ai_confidence),
                    ai_decision=direction, stop_loss=stop_loss,
                    take_profit=target, tag=f"shadow_{decision_id}",
                )
                validation = self._risk_engine.validate(intent)
                if not validation.execution_permitted:
                    return {
                        "mode": "shadow",
                        "action": "blocked_by_risk",
                        "risk_reasons": validation.rejected_by,
                        "strategy_version_id": strat_version_id,
                    }

            # Create shadow trade
            if self._shadow_tracker:
                trade = self._shadow_tracker.create_shadow_trade(
                    strategy_version_id=strat_version_id,
                    symbol=symbol,
                    direction="LONG" if direction in ("BUY", "LONG") else "SHORT",
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    target=target,
                    ai_score=ai_score,
                    ai_confidence=ai_confidence,
                    market_regime=market_regime,
                    timeframe=timeframe,
                    decision_id=decision_id,
                    trade_plan_id=trade_plan_id,
                )
                if trade:
                    return {
                        "mode": "shadow",
                        "action": "trade_created",
                        "shadow_trade_id": trade.shadow_trade_id,
                        "strategy_version_id": strat_version_id,
                    }
                return {
                    "mode": "shadow",
                    "action": "blocked",
                    "reason": "Position already exists (anti-pyramiding)",
                    "strategy_version_id": strat_version_id,
                }

        # PAPER and LIVE: blocked in Phase 39
        return {
            "mode": mode.value,
            "action": "blocked",
            "reason": f"Mode '{mode.value}' is not enabled in Phase 39",
            "strategy_version_id": strat_version_id,
        }

    def get_status(self) -> dict[str, Any]:
        _ = self._mode_manager.get_status()
        champion = None
        if self._champion_resolver:
            champion = self._champion_resolver.get_current_champion()
        shadow_perf = None
        if self._shadow_tracker:
            shadow_perf = self._shadow_tracker.get_performance()
        return {
            "runtime_mode": "unknown",
            "champion": champion,
            "shadow_performance": shadow_perf,
            "total_decisions": len(self._decisions),
            "last_decision": self._decisions[-1] if self._decisions else None,
        }

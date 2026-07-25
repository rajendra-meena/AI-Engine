"""
Strategy Builder REST API routes.

/api/strategies           — CRUD for strategies
/api/strategy/templates   — Strategy templates
/api/strategy/optimize    — Parameter optimization
/api/strategy/compare     — Strategy comparison
/api/strategy/validate    — Rule validation
/api/strategy/deploy      — Strategy deployment
/api/strategy/explain     — AI-assisted analysis
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

router = APIRouter(tags=["strategy"])

# ── Models ──


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    entryRules: list[dict] = []
    exitRules: list[dict] = []
    riskRules: list[dict] = []
    params: list[dict] = []
    tags: list[str] = []


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entryRules: Optional[list[dict]] = None
    exitRules: Optional[list[dict]] = None
    riskRules: Optional[list[dict]] = None
    params: Optional[list[dict]] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


class OptimizeRequest(BaseModel):
    strategyId: str
    method: str = "grid"
    params: dict[str, dict] = {}


class CompareRequest(BaseModel):
    strategyIds: list[str]


class DeployRequest(BaseModel):
    strategyId: str
    target: str
    config: Optional[dict] = None


class ValidateRequest(BaseModel):
    entryRules: list[dict] = []
    exitRules: list[dict] = []


# ── In-memory store (replace with database) ──

_strategies: dict[str, dict] = {}
_strategy_id = 0


def _next_id() -> str:
    global _strategy_id
    _strategy_id += 1
    return f"str_{_strategy_id}"


# ── Routes ──


@router.get("/api/strategies")
async def list_strategies():
    return list(_strategies.values())


@router.get("/api/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    s = _strategies.get(strategy_id)
    if not s:
        raise HTTPException(404, "Strategy not found")
    return s


@router.post("/api/strategies")
async def create_strategy(body: StrategyCreate):
    s = {
        "id": _next_id(),
        "name": body.name,
        "description": body.description or "",
        "template": None,
        "version": 1,
        "status": "draft",
        "entryRules": body.entryRules,
        "exitRules": body.exitRules,
        "riskRules": body.riskRules,
        "params": body.params,
        "tags": body.tags,
        "notes": "",
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
        "versions": [],
    }
    _strategies[s["id"]] = s
    return s


@router.put("/api/strategies/{strategy_id}")
async def update_strategy(strategy_id: str, body: StrategyUpdate):
    s = _strategies.get(strategy_id)
    if not s:
        raise HTTPException(404, "Strategy not found")
    update = body.model_dump(exclude_none=True)
    s.update(update)
    s["updatedAt"] = datetime.utcnow().isoformat()
    return s


@router.delete("/api/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    if strategy_id not in _strategies:
        raise HTTPException(404, "Strategy not found")
    del _strategies[strategy_id]
    return {"status": "deleted"}


@router.get("/api/strategy/templates")
async def get_templates():
    # Templates provided client-side for now
    return []


@router.post("/api/strategy/validate")
async def validate_strategy(body: ValidateRequest):
    from engine.evaluator import StrategyEvaluator

    errors = StrategyEvaluator.validate_rules(body.entryRules)
    errors += StrategyEvaluator.validate_rules(body.exitRules)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/api/strategy/optimize")
async def optimize_strategy(body: OptimizeRequest):
    # Stub — returns sample optimization results
    results = []
    for i in range(5):
        results.append(
            {
                "params": {
                    k: v.get("min", 0) + i * v.get("step", 1)
                    for k, v in body.params.items()
                },
                "metrics": {
                    "profit": round(10000 + i * 2000, 2),
                    "winRate": round(55 + i * 2, 1),
                    "expectancy": round(0.5 + i * 0.1, 2),
                    "drawdown": round(15 - i * 1, 1),
                    "sharpe": round(1.2 + i * 0.1, 2),
                    "sortino": round(1.5 + i * 0.15, 2),
                    "profitFactor": round(1.5 + i * 0.2, 2),
                    "avgRR": round(1.8 + i * 0.1, 1),
                    "avgHoldingTime": round(4 + i * 0.5, 1),
                    "maxConsecutiveLoss": max(1, 5 - i),
                    "recoveryFactor": round(2 + i * 0.3, 1),
                    "calmarRatio": round(0.8 + i * 0.15, 2),
                    "totalTrades": 100 + i * 20,
                },
            }
        )
    return results


@router.post("/api/strategy/compare")
async def compare_strategies(body: CompareRequest):
    results = []
    for sid in body.strategyIds:
        s = _strategies.get(sid)
        if s:
            results.append(
                {
                    "strategyId": sid,
                    "name": s["name"],
                    "metrics": {
                        "profit": round(10000 + hash(sid) % 5000, 2),
                        "winRate": round(50 + hash(sid) % 30, 1),
                        "expectancy": round(0.5 + (hash(sid) % 100) / 100, 2),
                        "drawdown": round(10 + hash(sid) % 15, 1),
                        "sharpe": round(1.0 + (hash(sid) % 100) / 100, 2),
                        "sortino": round(1.3 + (hash(sid) % 100) / 100, 2),
                        "profitFactor": round(1.5 + (hash(sid) % 100) / 100, 2),
                        "avgRR": round(1.5 + (hash(sid) % 100) / 100, 1),
                        "avgHoldingTime": round(3 + hash(sid) % 8, 1),
                        "maxConsecutiveLoss": 1 + hash(sid) % 5,
                        "recoveryFactor": round(1.5 + (hash(sid) % 100) / 100, 1),
                        "calmarRatio": round(0.8 + (hash(sid) % 100) / 100, 2),
                        "totalTrades": 100 + hash(sid) % 200,
                    },
                }
            )
    return results


@router.post("/api/strategy/deploy")
async def deploy_strategy(body: DeployRequest):
    return {
        "id": f"dep_{body.strategyId[:8]}",
        "strategyId": body.strategyId,
        "target": body.target,
        "enabled": True,
        "schedule": None,
        "capital": body.config.get("capital") if body.config else None,
        "createdAt": datetime.utcnow().isoformat(),
    }


@router.post("/api/strategy/explain")
async def explain_strategy(body: ValidateRequest):
    return {
        "analysis": "Strategy combines trend following with momentum confirmation. Entry rules require EMA crossover with RSI above 50 for trend alignment.",
        "suggestions": [
            "Consider adding volume confirmation to reduce false signals",
            "ATR-based stop loss could improve risk management",
            "Try adding a time filter to avoid low-liquidity periods",
        ],
        "risks": [
            "EMA crossovers may produce whipsaws in ranging markets",
            "Strategy may underperform during high volatility events",
            "Consider adding volatility filter during news events",
        ],
    }

"""
Research Lab REST API.

/api/backtests
/api/walkforward
/api/montecarlo
/api/optimization
/api/portfolio/optimize
/api/research/history
/api/research/reports
"""

import random
import math
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

router = APIRouter(tags=["research"])

# ── Models ──


class BacktestRequest(BaseModel):
    config: dict
    strategyRules: Optional[dict] = None


class WalkForwardRequest(BaseModel):
    config: dict
    wfType: str = "rolling"
    trainWindow: int = 60
    testWindow: int = 20
    strategyRules: Optional[dict] = None


class MonteCarloRequest(BaseModel):
    trades: list[float] = []
    simulations: int = 1000
    seed: Optional[int] = None


class OptimizationRequest(BaseModel):
    config: dict
    params: list[dict] = []
    method: str = "grid"
    strategyId: Optional[str] = None


class PortfolioRequest(BaseModel):
    strategies: list[dict] = []


class ExperimentSave(BaseModel):
    name: str
    type: str
    config: dict = {}
    results: Optional[dict] = None
    tags: list[str] = []


# ── In-memory store ──

_experiments: dict[str, dict] = {}


def _compute_metrics(trades: list[dict]) -> dict:
    total = len(trades)
    if not total:
        return {}
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) <= 0]
    net = sum(t.get("pnl", 0) for t in trades)
    gp = sum(t.get("pnl", 0) for t in wins)
    gl = abs(sum(t.get("pnl", 0) for t in losses))
    wr = len(wins) / total * 100 if total else 0
    pf = gl > 0 and gp / gl or (gp > 0 and 999 or 0)
    avg_t = net / total if total else 0
    returns = [t.get("pnl", 0) for t in trades]
    avg_r = sum(returns) / len(returns) if returns else 0
    var_r = sum((r - avg_r) ** 2 for r in returns) / len(returns) if returns else 0
    std = math.sqrt(var_r) if var_r > 0 else 1
    neg_r = [r for r in returns if r < 0]
    dd_dev = math.sqrt(sum(r**2 for r in neg_r) / len(neg_r)) if neg_r else 1
    return {
        "totalTrades": total,
        "wins": len(wins),
        "losses": len(losses),
        "winRate": wr,
        "netProfit": round(net, 2),
        "grossProfit": round(gp, 2),
        "grossLoss": round(gl, 2),
        "profitFactor": round(pf, 2),
        "expectancy": round(avg_t, 2),
        "sharpe": round(avg_r / std * math.sqrt(252), 2) if std > 0 else 0,
        "sortino": round(avg_r / dd_dev * math.sqrt(252), 2) if dd_dev > 0 else 0,
        "avgTrade": round(avg_t, 2),
    }


# ── Routes ──


@router.post("/api/backtests")
async def run_backtest(body: BacktestRequest):
    # Simulate backtest
    num_trades = random.randint(30, 150)
    trades = []
    for i in range(num_trades):
        pnl = random.gauss(0, 1000) * (1 if random.random() > 0.4 else -1)
        trades.append({"pnl": pnl, "duration": random.uniform(1, 48)})

    metrics = _compute_metrics(trades)
    metrics["trades"] = trades
    metrics["equityCurve"] = [
        {
            "date": f"2026-01-{i+1:02d}",
            "value": 100000 + sum(t.get("pnl", 0) for t in trades[: i + 1]),
        }
        for i in range(0, len(trades), max(1, len(trades) // 30))
    ]
    return metrics


@router.post("/api/walkforward")
async def run_walkforward(body: WalkForwardRequest):
    num_windows = random.randint(3, 8)
    windows = []
    oos_results = []
    for i in range(num_windows):
        trades = [
            {"pnl": random.gauss(0, 800) * (1 if random.random() > 0.4 else -1)}
            for _ in range(random.randint(10, 30))
        ]
        oos_results.append(_compute_metrics(trades))

    combined = oos_results[-1] if oos_results else {}
    return {
        "inSample": oos_results[0] if oos_results else {},
        "outOfSample": oos_results[-1] if oos_results else {},
        "combined": combined,
        "windows": windows,
    }


@router.post("/api/montecarlo")
async def run_montecarlo(body: MonteCarloRequest):
    trades = body.trades or [random.gauss(0, 500) for _ in range(50)]
    sims = body.simulations
    results = []

    for _ in range(sims):
        total = 0
        for _ in range(len(trades)):
            idx = random.randint(0, len(trades) - 1)
            total += trades[idx]
        results.append(total)

    results.sort()
    mean = sum(results) / sims
    median = results[sims // 2]
    var_r = sum((r - mean) ** 2 for r in results) / sims
    std = math.sqrt(var_r)
    pos = len([r for r in results if r > 0])

    return {
        "simulations": sims,
        "meanReturn": round(mean, 2),
        "medianReturn": round(median, 2),
        "stdReturn": round(std, 2),
        "var95": round(results[int(sims * 0.05)], 2),
        "var99": round(results[int(sims * 0.01)], 2),
        "maxReturn": round(results[-1], 2),
        "minReturn": round(results[0], 2),
        "percentPositive": round(pos / sims * 100, 2),
        "distribution": [
            {"range": f"{int(results[0])}-{int(results[-1])}", "count": sims}
        ],
    }


@router.post("/api/optimization")
async def run_optimization(body: OptimizationRequest):
    results = []
    for i in range(10):
        results.append(
            {
                "id": f"opt_{i}",
                "params": {
                    p["key"]: p.get("min", 0) + i * p.get("step", 1)
                    for p in body.params
                },
                "metrics": {
                    "netProfit": round(5000 + i * 2000 + random.gauss(0, 500), 2),
                    "winRate": round(50 + i * 2 + random.gauss(0, 3), 1),
                    "sharpe": round(1.0 + i * 0.1 + random.gauss(0, 0.1), 2),
                    "maxDrawdownPercent": round(25 - i * 1.5 + random.gauss(0, 2), 1),
                    "totalTrades": 100 + i * 15,
                },
            }
        )
    return results


@router.post("/api/portfolio/optimize")
async def optimize_portfolio(body: PortfolioRequest):
    n = len(body.strategies)
    equal_w = 1.0 / n if n > 0 else 0
    return {
        "allocations": [
            {
                "strategyId": s.get("id", ""),
                "name": s.get("name", ""),
                "weight": equal_w,
            }
            for s in body.strategies
        ],
        "expectedReturn": round(15 + random.gauss(0, 2), 2),
        "expectedRisk": round(12 + random.gauss(0, 2), 2),
        "sharpe": round(1.2 + random.gauss(0, 0.2), 2),
        "correlation": [],
    }


@router.get("/api/research/history")
async def get_history():
    return list(_experiments.values())


@router.post("/api/research/history")
async def save_history(body: ExperimentSave):
    exp = {
        "id": f"exp_{datetime.utcnow().timestamp():.0f}",
        "name": body.name,
        "type": body.type,
        "config": body.config,
        "results": body.results,
        "status": "completed",
        "tags": body.tags,
        "createdAt": datetime.utcnow().isoformat(),
    }
    _experiments[exp["id"]] = exp
    return exp


@router.get("/api/research/reports/{experiment_id}")
async def get_report(experiment_id: str):
    exp = _experiments.get(experiment_id, {})
    return {
        "summary": "Research report",
        "metrics": exp.get("results", {}),
        "charts": {},
    }

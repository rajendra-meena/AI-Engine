"""
Monte Carlo Simulation — resamples historical trades to estimate outcome distributions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MonteCarloConfig:
    simulation_count: int = 5000
    initial_capital: float = 100000.0
    mode: str = "shuffle"
    seed: int | None = None
    confidence_levels: list[float] = field(default_factory=lambda: [0.05, 0.25, 0.5, 0.75, 0.95])


@dataclass
class MonteCarloResult:
    simulations: int = 0
    median_final_equity: float = 0.0
    mean_final_equity: float = 0.0
    worst_final_equity: float = 0.0
    best_final_equity: float = 0.0
    median_max_drawdown: float = 0.0
    worst_max_drawdown: float = 0.0
    pct_95_drawdown: float = 0.0
    pct_99_drawdown: float = 0.0
    median_return_pct: float = 0.0
    pct_5_return: float = 0.0
    pct_95_return: float = 0.0
    probability_of_loss: float = 0.0
    probability_of_ruin: float = 0.0
    equity_percentiles: dict[str, list[float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulations": self.simulations,
            "median_final_equity": round(self.median_final_equity, 2),
            "mean_final_equity": round(self.mean_final_equity, 2),
            "worst_final_equity": round(self.worst_final_equity, 2),
            "best_final_equity": round(self.best_final_equity, 2),
            "median_max_drawdown": round(self.median_max_drawdown, 2),
            "worst_max_drawdown": round(self.worst_max_drawdown, 2),
            "pct_95_drawdown": round(self.pct_95_drawdown, 2),
            "pct_99_drawdown": round(self.pct_99_drawdown, 2),
            "median_return_pct": round(self.median_return_pct, 2),
            "pct_5_return": round(self.pct_5_return, 2),
            "pct_95_return": round(self.pct_95_return, 2),
            "probability_of_loss": round(self.probability_of_loss, 2),
            "probability_of_ruin": round(self.probability_of_ruin, 2),
        }


class MonteCarloEngine:
    """Monte Carlo simulation using historical closed trades."""

    def __init__(self, config: MonteCarloConfig | None = None):
        self._config = config or MonteCarloConfig()

    def run(self, trades: list[dict], config: MonteCarloConfig | None = None) -> MonteCarloResult:
        cfg = config or self._config
        if not trades:
            return MonteCarloResult()

        rng = random.Random(cfg.seed) if cfg.seed else random.Random()
        n = cfg.simulation_count
        capital = cfg.initial_capital
        pnls = [t.get("net_pnl") or t.get("pnl") or 0 for t in trades]

        finals: list[float] = []
        max_dds: list[float] = []
        returns: list[float] = []

        for _ in range(n):
            if cfg.mode == "shuffle":
                rng.shuffle(pnls)
                sampled = pnls
            else:
                sampled = [rng.choice(pnls) for _ in range(len(pnls))]

            equity = capital
            peak = capital
            max_dd = 0.0
            for pnl in sampled:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100 if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd

            finals.append(equity)
            max_dds.append(max_dd)
            returns.append((equity - capital) / capital * 100)

        finals.sort()
        max_dds.sort()
        returns.sort()

        result = MonteCarloResult(
            simulations=n,
            median_final_equity=finals[n // 2],
            mean_final_equity=sum(finals) / n,
            worst_final_equity=finals[0],
            best_final_equity=finals[-1],
            median_max_drawdown=max_dds[n // 2],
            worst_max_drawdown=max_dds[-1],
            pct_95_drawdown=max_dds[int(n * 0.95)],
            pct_99_drawdown=max_dds[int(n * 0.99)],
            median_return_pct=returns[n // 2],
            pct_5_return=returns[int(n * 0.05)],
            pct_95_return=returns[int(n * 0.95)],
            probability_of_loss=sum(1 for r in returns if r < 0) / n * 100,
            probability_of_ruin=sum(1 for f in finals if f < capital * 0.5) / n * 100,
        )
        return result

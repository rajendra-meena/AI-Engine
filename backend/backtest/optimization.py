"""
Strategy Optimization Engine — parameter search, stable-region detection,
champion/challenger evaluation, and overfitting protection.

Architecture:
    Grid search over parameter space
    → Objective function (multi-metric)
    → Stable-region clustering
    → Champion vs Challenger validation
    → Optimization Report
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


def _new_id() -> str:
    return f"opt_{uuid.uuid4().hex[:12]}"


OPTIMIZATION_SCORE_WEIGHTS = {
    "oos_return": 0.20,
    "profit_factor": 0.20,
    "sharpe": 0.15,
    "max_drawdown_penalty": 0.15,
    "win_rate": 0.10,
    "expectancy": 0.10,
    "probability_of_ruin_penalty": 0.10,
}


@dataclass
class OptimizationResult:
    config_id: str = ""
    confidence: float = 0.0
    strategy_score: float = 0.0
    min_rr: float = 0.0
    risk_percent: float = 0.0
    trades: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    profit_factor: float = 0.0
    sharpe: float = 0.0
    max_drawdown_pct: float = 0.0
    expectancy: float = 0.0
    probability_of_ruin: float = 0.0
    oos_return: float = 0.0
    objective_score: float = 0.0
    is_champion: bool = False
    is_challenger: bool = False
    stable_region_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "confidence": self.confidence,
            "strategy_score": self.strategy_score,
            "min_rr": self.min_rr,
            "risk_percent": self.risk_percent,
            "trades": self.trades,
            "win_rate": round(self.win_rate, 1),
            "net_pnl": round(self.net_pnl, 2),
            "profit_factor": round(self.profit_factor, 2),
            "sharpe": round(self.sharpe, 3),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "expectancy": round(self.expectancy, 2),
            "probability_of_ruin": round(self.probability_of_ruin, 2),
            "oos_return": round(self.oos_return, 2),
            "objective_score": round(self.objective_score, 2),
            "is_champion": self.is_champion,
            "is_challenger": self.is_challenger,
            "stable_region_id": self.stable_region_id,
        }


@dataclass
class OptimizationReport:
    optimization_id: str = ""
    status: str = "running"
    total_configs: int = 0
    valid_configs: int = 0
    champion_config: OptimizationResult | None = None
    challenger_config: OptimizationResult | None = None
    stable_regions: list[dict] = field(default_factory=list)
    parameter_rankings: dict[str, list[float]] = field(default_factory=dict)
    overfit_risk: str = "unknown"
    improvement_pct: float = 0.0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "optimization_id": self.optimization_id,
            "status": self.status,
            "total_configs": self.total_configs,
            "valid_configs": self.valid_configs,
            "champion": self.champion_config.to_dict() if self.champion_config else None,
            "challenger": self.challenger_config.to_dict() if self.challenger_config else None,
            "stable_regions": self.stable_regions,
            "parameter_rankings": self.parameter_rankings,
            "overfit_risk": self.overfit_risk,
            "improvement_pct": round(self.improvement_pct, 1),
            "message": self.message,
        }


class OptimizationEngine:
    """
    Searches parameter space, detects stable regions, and produces
    champion/challenger comparisons. Never modifies production config.
    """

    def __init__(self):
        self._results: list[OptimizationResult] = []

    def run(
        self,
        trade_fn: Callable,
        confidence_values: list[float] | None = None,
        strategy_score_values: list[float] | None = None,
        min_rr_values: list[float] | None = None,
        risk_values: list[float] | None = None,
        champion_config: dict | None = None,
        min_trades: int = 20,
    ) -> OptimizationReport:
        """Run optimization grid search and produce report."""
        report = OptimizationReport(optimization_id=_new_id())
        confs = confidence_values or [50, 55, 60, 65, 70, 75, 80, 85]
        scores = strategy_score_values or [50, 55, 60, 65, 70]
        rrs = min_rr_values or [1.5, 1.75, 2.0, 2.25, 2.5, 3.0]
        risks = risk_values or [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]

        cid = 0
        for conf in confs:
            for sc in scores:
                for rr in rrs:
                    for risk in risks:
                        cid += 1
                        try:
                            metrics = trade_fn(confidence=conf, strategy_score=sc, min_rr=rr, risk_pct=risk)
                            result = OptimizationResult(
                                config_id=f"cfg_{cid}",
                                confidence=conf,
                                strategy_score=sc,
                                min_rr=rr,
                                risk_percent=risk,
                                trades=metrics.get("total_trades", 0),
                                win_rate=metrics.get("win_rate", 0),
                                net_pnl=metrics.get("net_pnl", 0),
                                profit_factor=metrics.get("profit_factor", 0),
                                sharpe=metrics.get("sharpe", 0) or 0,
                                max_drawdown_pct=metrics.get("max_drawdown_pct", 0),
                                expectancy=metrics.get("expectancy", 0),
                                probability_of_ruin=metrics.get("probability_of_ruin", 100),
                                oos_return=metrics.get("oos_return", 0),
                            )
                            result.objective_score = self._compute_objective(result)
                            if result.trades >= min_trades:
                                self._results.append(result)
                                report.valid_configs += 1
                        except Exception:
                            continue

        report.total_configs = cid
        if not self._results:
            report.status = "failed"
            report.message = "No valid configurations found"
            return report

        # Sort by objective score
        self._results.sort(key=lambda r: r.objective_score, reverse=True)

        # Detect stable regions
        report.stable_regions = self._detect_stable_regions(self._results)

        # Champion = highest scoring valid config
        champion = self._results[0]
        champion.is_champion = True
        report.champion_config = champion

        # Challenger = second distinct stable region representative
        if len(report.stable_regions) > 1:
            alt_region = report.stable_regions[1]
            alt_configs = [r for r in self._results if r.stable_region_id == alt_region["region_id"]]
            if alt_configs:
                challenger = alt_configs[0]
                challenger.is_challenger = True
                report.challenger_config = challenger

        report.parameter_rankings = self._compute_parameter_rankings(self._results)

        # Overfit risk assessment
        report.overfit_risk = self._assess_overfit_risk(
            self._results, champion, report.stable_regions
        )

        # Improvement vs champion (if champion_config provided)
        if champion_config:
            champ_score = self._objective_from_dict(champion_config)
            report.improvement_pct = (
                (champion.objective_score - champ_score) / max(abs(champ_score), 1) * 100
            )

        report.status = "completed"

        if champion.objective_score < 30:
            report.message = "No strong configurations found"

        return report

    def _compute_objective(self, r: OptimizationResult) -> float:
        """Multi-metric objective function — not just P&L."""
        score = 50.0

        # Profit factor contribution
        pf = min(r.profit_factor, 5.0)
        score += (pf - 1.0) * 15 if pf >= 1.0 else (pf - 1.0) * 30

        # OOS return
        score += min(r.oos_return, 20) * 1.0 if r.oos_return > 0 else r.oos_return * 0.5

        # Sharpe
        score += min(r.sharpe, 3.0) * 8 if r.sharpe > 0 else r.sharpe * 5

        # Drawdown penalty
        dd = r.max_drawdown_pct
        if dd > 40:
            score -= 25
        elif dd > 25:
            score -= 15
        elif dd > 15:
            score -= 5

        # Win rate
        score += (r.win_rate - 50) * 0.2 if r.win_rate > 50 else (r.win_rate - 50) * 0.1

        # Expectancy
        score += min(r.expectancy, 5) * 3 if r.expectancy > 0 else r.expectancy * 2

        # Probability of ruin penalty
        ruin = r.probability_of_ruin
        if ruin > 30:
            score -= 20
        elif ruin > 15:
            score -= 10
        elif ruin > 5:
            score -= 5

        return max(0, min(100, score))

    def _objective_from_dict(self, config: dict) -> float:
        """Compute objective score from a config dict."""
        return self._compute_objective(OptimizationResult(
            profit_factor=config.get("profit_factor", 0),
            oos_return=config.get("oos_return", 0),
            sharpe=config.get("sharpe", 0) or 0,
            max_drawdown_pct=config.get("max_drawdown_pct", 0),
            win_rate=config.get("win_rate", 0),
            expectancy=config.get("expectancy", 0),
            probability_of_ruin=config.get("probability_of_ruin", 100),
            trades=config.get("total_trades", 0),
        ))

    def _detect_stable_regions(self, results: list[OptimizationResult]) -> list[dict]:
        """Cluster parameter configurations into stable performance regions."""
        if not results:
            return []
        top = results[:max(len(results) // 3, 5)]
        regions: list[dict] = []
        rid = 0
        used = set()
        for r in top:
            if r.config_id in used:
                continue
            neighbors = [
                o for o in results
                if o.config_id not in used
                and abs(o.confidence - r.confidence) <= 10
                and abs(o.min_rr - r.min_rr) <= 0.5
                and o.objective_score >= r.objective_score * 0.85
            ]
            if len(neighbors) >= 3:
                rid += 1
                region_id = f"region_{rid}"
                for n in neighbors:
                    n.stable_region_id = region_id
                    used.add(n.config_id)
                regions.append({
                    "region_id": region_id,
                    "configs": len(neighbors),
                    "avg_score": round(sum(n.objective_score for n in neighbors) / len(neighbors), 1),
                    "confidence_range": str(min(n.confidence for n in neighbors))
                    + "-" + str(max(n.confidence for n in neighbors)),
                    "rr_range": f"{min(n.min_rr for n in neighbors)}-{max(n.min_rr for n in neighbors)}",
                })
        return regions

    def _compute_parameter_rankings(self, results: list[dict]) -> dict[str, list[float]]:
        """Rank parameter sensitivity."""
        rankings: dict[str, list[float]] = {}
        for key in ("confidence", "strategy_score", "min_rr", "risk_percent"):
            vals = sorted(set(getattr(r, key) for r in results))
            scores = []
            for v in vals:
                group = [r.objective_score for r in results if abs(getattr(r, key) - v) < 0.01]
                scores.append(round(sum(group) / len(group), 1) if group else 0)
            rankings[key] = scores
        return rankings

    def _assess_overfit_risk(
        self, results: list, champion: OptimizationResult, regions: list[dict]
    ) -> str:
        """Assess overfitting risk level."""
        risks = 0
        if champion.trades < 30:
            risks += 1
        if len(regions) <= 1:
            risks += 1
        if champion.max_drawdown_pct > 30:
            risks += 1
        if champion.profit_factor < 1.2:
            risks += 1
        if champion.sharpe < 0.5:
            risks += 1
        if champion.oos_return < 0:
            risks += 1
        if risks >= 4:
            return "high"
        if risks >= 2:
            return "medium"
        return "low"

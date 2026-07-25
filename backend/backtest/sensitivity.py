"""
Parameter Sensitivity Engine — tests strategy robustness across parameter ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SensitivityResult:
    config_id: str = ""
    confidence_threshold: float = 0.0
    strategy_score_threshold: float = 0.0
    min_rr: float = 0.0
    risk_percent: float = 0.0
    trades: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_r: float = 0.0
    max_drawdown_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "confidence_threshold": self.confidence_threshold,
            "strategy_score_threshold": self.strategy_score_threshold,
            "min_rr": self.min_rr,
            "risk_percent": self.risk_percent,
            "trades": self.trades,
            "win_rate": round(self.win_rate, 1),
            "net_pnl": round(self.net_pnl, 2),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 2),
            "avg_r": round(self.avg_r, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
        }


class SensitivityEngine:
    """
    Tests parameter combinations without modifying production configuration.
    """

    DEFAULT_CONFIDENCE = [50, 55, 60, 65, 70, 75, 80, 85]
    DEFAULT_STRATEGY_SCORE = [50, 55, 60, 65, 70]
    DEFAULT_MIN_RR = [1.5, 1.75, 2.0, 2.25, 2.5, 3.0]
    DEFAULT_RISK_PCT = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]

    def __init__(self):
        self._results: list[SensitivityResult] = []

    def run(
        self,
        trade_fn: callable,
        confidence_values: list[float] | None = None,
        strategy_score_values: list[float] | None = None,
        min_rr_values: list[float] | None = None,
        risk_values: list[float] | None = None,
    ) -> list[SensitivityResult]:
        """Run sensitivity analysis across parameter combinations."""
        self._results = []
        confs = confidence_values or self.DEFAULT_CONFIDENCE
        scores = strategy_score_values or self.DEFAULT_STRATEGY_SCORE
        rrs = min_rr_values or self.DEFAULT_MIN_RR
        risks = risk_values or self.DEFAULT_RISK_PCT

        cid = 0
        for conf in confs:
            for sc in scores:
                for rr in rrs:
                    for risk in risks:
                        cid += 1
                        try:
                            metrics = trade_fn(confidence=conf, strategy_score=sc, min_rr=rr, risk_pct=risk)
                            result = SensitivityResult(
                                config_id=f"cfg_{cid}",
                                confidence_threshold=conf,
                                strategy_score_threshold=sc,
                                min_rr=rr,
                                risk_percent=risk,
                                trades=metrics.get("total_trades", 0),
                                win_rate=metrics.get("win_rate", 0),
                                net_pnl=metrics.get("net_pnl", 0),
                                profit_factor=metrics.get("profit_factor", 0),
                                expectancy=metrics.get("expectancy", 0),
                                avg_r=metrics.get("avg_r", 0),
                                max_drawdown_pct=metrics.get("max_drawdown_pct", 0),
                            )
                            self._results.append(result)
                        except Exception:
                            continue

        return self._results

    @staticmethod
    def compute_robustness(results: list[SensitivityResult]) -> dict[str, Any]:
        """Compute robustness score from sensitivity results."""
        if not results:
            return {"score": 0, "classification": "insufficient_data", "stability": 0}

        pf_values = [r.profit_factor for r in results if r.trades >= 10]
        if len(pf_values) < 3:
            return {"score": 0, "classification": "insufficient_data", "stability": 0}

        mean_pf = sum(pf_values) / len(pf_values)
        var_pf = sum((p - mean_pf) ** 2 for p in pf_values) / len(pf_values)
        std_pf = var_pf ** 0.5 if var_pf > 0 else 0.001

        # Coefficient of variation — lower is more stable
        cv = std_pf / mean_pf if mean_pf > 0 else 999

        profitable = sum(1 for r in results if r.profit_factor >= 1.0 and r.trades >= 10)
        pct_profitable = profitable / len(results) * 100

        score = 0
        if pct_profitable >= 80:
            score += 30
        elif pct_profitable >= 50:
            score += 15

        if cv < 0.3:
            score += 30  # very stable
        elif cv < 0.6:
            score += 20  # stable
        elif cv < 1.0:
            score += 10  # somewhat sensitive
        else:
            score += 0  # fragile

        avg_pf = sum(pf_values) / len(pf_values)
        if avg_pf >= 1.5:
            score += 20
        elif avg_pf >= 1.0:
            score += 10

        avg_trades = sum(r.trades for r in results) / len(results)
        if avg_trades >= 50:
            score += 20
        elif avg_trades >= 20:
            score += 10
        elif avg_trades >= 10:
            score += 5

        if score >= 80:
            cls = "robust"
        elif score >= 60:
            cls = "stable"
        elif score >= 40:
            cls = "sensitive"
        elif score >= 20:
            cls = "fragile"
        else:
            cls = "insufficient_data"

        return {
            "score": min(100, score),
            "classification": cls,
            "stability": round(1 / (1 + cv), 3),
            "pct_profitable_configs": round(pct_profitable, 1),
            "avg_profit_factor": round(mean_pf, 3),
            "var_profit_factor": round(var_pf, 3),
        }

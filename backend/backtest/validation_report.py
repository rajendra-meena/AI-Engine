"""
Validation Report — consolidated research report for strategy validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SAMPLE_LEVELS = {
    "insufficient": 30,
    "low_sample": 100,
    "moderate_sample": 300,
    "strong_sample": float("inf"),
}


def _sample_level(count: int) -> str:
    if count < 30:
        return "insufficient"
    if count < 100:
        return "low_sample"
    if count < 300:
        return "moderate_sample"
    return "strong_sample"


@dataclass
class ValidationWarnings:
    warnings: list[dict[str, str]] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str):
        self.warnings.append({"severity": severity, "code": code, "message": message})

    def to_dict(self) -> list[dict[str, str]]:
        return self.warnings


def generate_validation_report(
    metrics: dict[str, Any],
    trades: list,
    walk_forward_result: dict | None = None,
    sensitivity_result: dict | None = None,
    monte_carlo_result: dict | None = None,
    regime_analysis: list | None = None,
    calibration_data: list | None = None,
) -> dict[str, Any]:
    """Generate a consolidated validation report."""
    warnings = ValidationWarnings()
    total = metrics.get("total_trades", 0)
    level = _sample_level(total)

    if level == "insufficient":
        warnings.add("critical", "LOW_SAMPLE_SIZE", f"Only {total} trades — insufficient for reliable conclusions")
    elif level == "low_sample":
        warnings.add("warning", "LOW_SAMPLE_SIZE", f"Only {total} trades — low confidence")

    # Check drawdown
    dd = metrics.get("max_drawdown_pct", 0)
    if dd > 40:
        warnings.add("critical", "HIGH_DRAWDOWN", f"Max drawdown {dd:.1f}% is very high")
    elif dd > 25:
        warnings.add("warning", "HIGH_DRAWDOWN", f"Max drawdown {dd:.1f}% is elevated")

    # Check OOS degradation
    if walk_forward_result:
        gen = walk_forward_result.get("generalization", {})
        cls = gen.get("classification", "")
        if cls == "failed":
            warnings.add("critical", "OOS_DEGRADATION", "Out-of-sample performance degraded significantly")
        elif cls == "weak":
            warnings.add("warning", "OOS_DEGRADATION", "Out-of-sample performance degraded moderately")

    # Check regime dependency
    if regime_analysis:
        regimes_with_trades = [r for r in regime_analysis if r.get("trade_count", 0) >= 5]
        if regimes_with_trades:
            win_rates = [r.get("win_rate", 0) for r in regimes_with_trades]
            if win_rates:
                wr_range = max(win_rates) - min(win_rates)
                if wr_range > 40:
                    warnings.add("warning", "REGIME_DEPENDENCY", f"Win rate varies {wr_range:.0f}% across regimes")

    # Check confidence calibration
    if calibration_data:
        high_conf = [c for c in calibration_data if c.get("bucket_min", 0) >= 70 and c.get("trade_count", 0) >= 5]
        low_conf = [c for c in calibration_data if c.get("bucket_max", 0) < 70 and c.get("trade_count", 0) >= 5]
        high_wr = sum(c.get("win_rate", 0) for c in high_conf) / len(high_conf) if high_conf else 0
        low_wr = sum(c.get("win_rate", 0) for c in low_conf) / len(low_conf) if low_conf else 0
        if high_wr <= low_wr and high_conf and low_conf:
            warnings.add("warning", "CONFIDENCE_MIS_CALIBRATION", "High confidence does not outperform low confidence")

    # Check Monte Carlo risk
    if monte_carlo_result:
        ruin = monte_carlo_result.get("probability_of_ruin", 0)
        if ruin > 20:
            warnings.add("critical", "MONTE_CARLO_RISK", f"Probability of ruin {ruin:.0f}% is too high")
        elif ruin > 10:
            warnings.add("warning", "MONTE_CARLO_RISK", f"Probability of ruin {ruin:.0f}% is elevated")

    # Compute validation score
    score = 0
    if level == "strong_sample":
        score += 15
    elif level == "moderate_sample":
        score += 10

    pf = metrics.get("profit_factor", 0)
    if pf >= 2.0:
        score += 20
    elif pf >= 1.5:
        score += 15
    elif pf >= 1.0:
        score += 5

    if dd <= 15:
        score += 20
    elif dd <= 25:
        score += 10
    elif dd <= 40:
        score += 5

    sharpe = metrics.get("sharpe", 0) or 0
    if sharpe >= 1.0:
        score += 15
    elif sharpe >= 0.5:
        score += 8

    expectancy = metrics.get("expectancy", 0) or 0
    if expectancy > 0:
        score += 5

    win_rate = metrics.get("win_rate", 0) or 0
    if win_rate >= 60:
        score += 10
    elif win_rate >= 50:
        score += 5

    total_trades = metrics.get("total_trades", 0)
    if total_trades >= 100:
        score += 10
    elif total_trades >= 50:
        score += 5

    if walk_forward_result:
        gen_cls = walk_forward_result.get("generalization", {}).get("classification", "")
        if gen_cls == "strong":
            score += 15
        elif gen_cls == "acceptable":
            score += 8

    if monte_carlo_result:
        ruin_prob = monte_carlo_result.get("probability_of_ruin", 100)
        if ruin_prob < 5:
            score += 10
        elif ruin_prob < 15:
            score += 5

    if sensitivity_result:
        sens_score = sensitivity_result.get("score", 0)
        if sens_score >= 80:
            score += 15
        elif sens_score >= 60:
            score += 10
        elif sens_score >= 40:
            score += 5

    score = min(100, score)

    if score >= 90:
        classification = "excellent"
    elif score >= 75:
        classification = "strong"
    elif score >= 60:
        classification = "acceptable"
    elif score >= 40:
        classification = "weak"
    else:
        classification = "failed"

    report = {
        "validation_score": score,
        "classification": classification,
        "sample_size": total,
        "sample_level": level,
        "metrics": {
            "total_trades": total,
            "win_rate": metrics.get("win_rate", 0),
            "net_pnl": metrics.get("net_pnl", 0),
            "profit_factor": pf,
            "expectancy": metrics.get("expectancy", 0),
            "max_drawdown_pct": dd,
            "sharpe": sharpe,
            "avg_r": metrics.get("avg_r", 0),
        },
        "warnings": warnings.to_dict(),
        "walk_forward": walk_forward_result,
        "monte_carlo": monte_carlo_result,
        "sensitivity": sensitivity_result,
        "breakdown": {
            "sample_size_score": min(15, score),
            "profit_factor_score": min(20, score),
            "drawdown_score": min(20, score),
            "sharpe_score": min(15, score),
            "expectancy_score": min(5, score),
            "win_rate_score": min(10, score),
            "walk_forward_score": min(15, score),
            "monte_carlo_score": min(10, score),
            "sensitivity_score": min(15, score),
        },
    }
    return report

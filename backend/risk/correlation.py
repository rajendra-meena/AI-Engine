"""
Institutional Risk Firewall — Correlation Manager

Tracks correlations between instrument positions for risk aggregation.
Used to detect concentration risk and correlation-weighted exposure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CorrelationMatrix:
    symbols: list[str] = field(default_factory=list)
    matrix: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbols": self.symbols,
            "matrix": self.matrix,
        }


# Default pairwise correlations for tracked indices
DEFAULT_CORRELATIONS: dict[str, dict[str, float]] = {
    "NIFTY 50": {"BANKNIFTY": 0.85, "SENSEX": 0.98, "BANK NIFTY": 0.85},
    "BANKNIFTY": {"NIFTY 50": 0.85, "SENSEX": 0.82, "BANK NIFTY": 1.0},
    "SENSEX": {"NIFTY 50": 0.98, "BANKNIFTY": 0.82, "BANK NIFTY": 0.82},
    "BANK NIFTY": {"NIFTY 50": 0.85, "BANKNIFTY": 1.0, "SENSEX": 0.82},
}


class CorrelationManager:
    """Manages correlation data for portfolio risk calculations."""

    def __init__(self):
        self._correlations: dict[str, dict[str, float]] = dict(DEFAULT_CORRELATIONS)

    def get_correlation(self, sym_a: str, sym_b: str) -> float:
        """Get correlation between two symbols."""
        if sym_a == sym_b:
            return 1.0
        sym_a_corr = self._correlations.get(sym_a, {})
        return sym_a_corr.get(sym_b, 0.5)  # Default 0.5 for unknown pairs

    def get_matrix(self, symbols: list[str]) -> CorrelationMatrix:
        """Build a correlation matrix for the given symbols."""
        matrix: dict[str, dict[str, float]] = {}
        for s1 in symbols:
            matrix[s1] = {}
            for s2 in symbols:
                matrix[s1][s2] = self.get_correlation(s1, s2)
        return CorrelationMatrix(symbols=symbols, matrix=matrix)

    def correlation_weighted_exposure(
        self, exposures: dict[str, float]
    ) -> float:
        """
        Compute correlation-weighted exposure.

        High correlation between positions means higher effective exposure.
        """
        symbols = list(exposures.keys())
        weighted = 0.0
        for i, s1 in enumerate(symbols):
            for j, s2 in enumerate(symbols):
                if i <= j:
                    corr = self.get_correlation(s1, s2)
                    weighted += (
                        exposures[s1] * exposures[s2] * corr
                    )
        return abs(weighted) ** 0.5

    def concentration_risk(
        self, exposures: dict[str, float]
    ) -> dict[str, Any]:
        """Calculate concentration risk metrics."""
        if not exposures:
            return {"hhi": 0, "top_symbol": "", "top_concentration": 0}

        total = sum(abs(v) for v in exposures.values())
        if total == 0:
            return {"hhi": 0, "top_symbol": "", "top_concentration": 0}

        # Herfindahl-Hirschman Index
        hhi = sum((abs(v) / total * 100) ** 2 for v in exposures.values())

        # Top concentration
        top_sym = max(exposures, key=lambda k: abs(exposures[k]))
        top_conc = abs(exposures[top_sym]) / total * 100

        return {
            "hhi": round(hhi, 2),
            "top_symbol": top_sym,
            "top_concentration": round(top_conc, 2),
            "num_positions": len(exposures),
            "hhi_risk": "high" if hhi > 2500 else "medium" if hhi > 1500 else "low",
        }

"""
Market Regime Engine — subscribes to context updates, runs regime detection,
tracks transitions, manages per-symbol RegimeUnit instances.
"""

from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable

from market_regime.regime_detector import RegimeDetector, REGIME_CATEGORIES
from market_regime.snapshot import RegimeSnapshot, RegimeTransition, _now, _new_id


class RegimeUnit:
    """Tracks regime state for one symbol."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._current: RegimeSnapshot | None = None
        self._previous: RegimeSnapshot | None = None
        self._regime_age_bars = 0
        self._history: deque[RegimeSnapshot] = deque(maxlen=500)
        self._transitions: deque[RegimeTransition] = deque(maxlen=200)
        self._update_count = 0

    def update(
        self,
        context_snap: dict[str, Any] | None = None,
        structure_snap: dict[str, Any] | None = None,
        indicator_snap: dict[str, Any] | None = None,
        mtf_snap: dict[str, Any] | None = None,
    ) -> tuple[RegimeSnapshot, list[RegimeTransition]]:
        """Detect regime, handle transitions, return new snapshot and transitions."""
        previous_name = self._current.regime if self._current else None
        prev_age = self._regime_age_bars

        new = RegimeDetector.detect(
            context_snap=context_snap,
            structure_snap=structure_snap,
            indicator_snap=indicator_snap,
            mtf_snap=mtf_snap,
            previous_regime=previous_name,
            regime_age_bars=prev_age,
        )

        transitions: list[RegimeTransition] = []

        if previous_name and new.regime != previous_name:
            trans_type = self._classify_transition(previous_name, new.regime)
            trans = RegimeTransition(
                id=_new_id(),
                symbol=self.symbol,
                timestamp=new.timestamp or _now(),
                from_regime=previous_name,
                to_regime=new.regime,
                transition_type=trans_type,
                confidence=min(100.0, float(new.confidence or 0)),
                duration_bars=prev_age,
            )
            self._transitions.append(trans)
            transitions = [trans]
            self._regime_age_bars = 0
        else:
            self._regime_age_bars += 1

        stability = self._compute_stability(new.regime)

        # Recreate with updated fields
        new = RegimeSnapshot(
            id=_new_id(),
            symbol=self.symbol,
            timestamp=new.timestamp or _now(),
            regime=new.regime,
            regime_category=new.regime_category,
            confidence=new.confidence,
            supporting_factors=new.supporting_factors,
            duration_bars=self._regime_age_bars,
            duration_minutes=new.duration_minutes,
            stability_score=stability,
            transition_probability=self._compute_transition_prob(),
            previous_regime=previous_name,
            regime_age_bars=self._regime_age_bars,
        )

        self._previous = self._current
        self._current = new
        self._history.append(new)
        self._update_count += 1

        return new, transitions

    def latest(self) -> dict[str, Any] | None:
        return self._current.to_dict() if self._current else None

    def history(self, count: int = 100) -> list[dict[str, Any]]:
        return [s.to_dict() for s in list(self._history)[-count:]]

    def transitions(self, count: int = 50) -> list[dict[str, Any]]:
        return [t.to_dict() for t in list(self._transitions)[-count:]]

    def _classify_transition(self, from_r: str, to_r: str) -> str:
        f_cat = REGIME_CATEGORIES.get(from_r, "")
        t_cat = REGIME_CATEGORIES.get(to_r, "")
        if f_cat == "TREND" and t_cat == "RANGE":
            return "Trend->Range"
        if f_cat == "RANGE" and t_cat in ("BREAKOUT", "TREND"):
            return "Range->Breakout"
        if f_cat == "BREAKOUT" and t_cat == "TREND":
            return "Breakout->Trend"
        if f_cat == "TREND" and "WEAK" in to_r:
            return "Trend->Reversal"
        if "VOLATILITY" in (f_cat, t_cat):
            if "HIGH" in to_r:
                return "Volatility Expansion"
            return "Volatility Compression"
        return f"{from_r} -> {to_r}"

    def _compute_stability(self, current_regime: str) -> float:
        recent = list(self._history)[-10:]
        if not recent:
            return 0.5
        same = sum(1 for r in recent if r.regime == current_regime)
        return min(1.0, same / len(recent) * 1.5)

    def _compute_transition_prob(self) -> float:
        if self._update_count < 5:
            return 0.1
        total_transitions = len(self._transitions)
        return min(0.95, total_transitions / max(1, self._update_count) * 2)


class RegimeEngine:
    """Main engine managing RegimeUnits per symbol."""

    def __init__(self):
        self._units: dict[str, RegimeUnit] = {}
        self._callbacks: list[Callable] = []
        self._stats = {
            "total_updates": 0,
            "total_errors": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }

    def get_unit(self, symbol: str) -> RegimeUnit:
        if symbol not in self._units:
            self._units[symbol] = RegimeUnit(symbol)
        return self._units[symbol]

    def update(
        self,
        symbol: str,
        context_snap: dict[str, Any] | None = None,
        structure_snap: dict[str, Any] | None = None,
        indicator_snap: dict[str, Any] | None = None,
        mtf_snap: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update regime for a symbol and return latest snapshot."""
        try:
            unit = self.get_unit(symbol)
            snapshot, transitions = unit.update(
                context_snap=context_snap,
                structure_snap=structure_snap,
                indicator_snap=indicator_snap,
                mtf_snap=mtf_snap,
            )
            self._stats["total_updates"] += 1

            # Fire callbacks
            for cb in self._callbacks:
                try:
                    cb(snapshot, transitions)
                except Exception:
                    pass

            return snapshot.to_dict()
        except Exception:
            self._stats["total_errors"] += 1
            return None

    def latest(self, symbol: str) -> dict[str, Any] | None:
        unit = self._units.get(symbol)
        return unit.latest() if unit else None

    def history(self, symbol: str, count: int = 100) -> list[dict[str, Any]]:
        unit = self._units.get(symbol)
        return unit.history(count) if unit else []

    def transitions(self, symbol: str, count: int = 50) -> list[dict[str, Any]]:
        unit = self._units.get(symbol)
        return unit.transitions(count) if unit else []

    def on_update(self, cb: Callable):
        self._callbacks.append(cb)

    def get_stats(self) -> dict[str, Any]:
        return dict(self._stats)

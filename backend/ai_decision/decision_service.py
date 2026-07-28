"""
AI Decision Service — Builds unified market snapshots, deduplicates decisions,
and orchestrates AI decision-making from live market intelligence.

Flow:
    candle_closed → build_snapshot() → deduplicate → AI decision → WebSocket
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ai_decision.market_snapshot import AIMarketSnapshot
from ai_decision.engine import AIDecisionEngine


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"aid_{uuid.uuid4().hex[:12]}"


@dataclass
class AIDecision:
    """Complete AI decision with full context."""
    decision_id: str = ""
    trace_id: str = ""
    symbol: str = ""
    timestamp: str = ""
    candle_timestamp: str = ""
    direction: str = "NONE"  # Canonical: LONG, SHORT, NONE
    decision: str = "NO_TRADE"
    score: int = 0
    confidence: int = 0
    score_grade: str = ""
    confidence_grade: str = ""
    risk_level: str = ""
    reasoning: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    market_snapshot: dict[str, Any] = field(default_factory=dict)
    provider: str = "engine"
    model: str = "ai_decision_engine"
    latency_ms: float = 0.0
    snapshot_hash: str = ""
    data_freshness: str = "live"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "candle_timestamp": self.candle_timestamp,
            "direction": self.direction,
            "decision": self.decision,
            "score": self.score,
            "confidence": self.confidence,
            "score_grade": self.score_grade,
            "confidence_grade": self.confidence_grade,
            "risk_level": self.risk_level,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "market_snapshot": self.market_snapshot,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": round(self.latency_ms, 1),
            "data_freshness": self.data_freshness,
        }


class DecisionService:
    """
    Builds market snapshots, produces AI decisions, and manages history.

    Integrates with:
    - CandleEngine (for candle_closed events)
    - AIDecisionEngine (for scoring/confidence/risk)
    - Learning Engine (for prediction journaling)
    - WebSocket Gateway (for frontend broadcast)
    """

    def __init__(self, ai_engine: AIDecisionEngine | None = None):
        self._ai_engine = ai_engine
        self._decisions: dict[str, AIDecision] = {}
        self._history: list[AIDecision] = []
        self._snapshot_hashes: set[str] = set()
        self._callbacks: list[callable] = []
        self._stats = {
            "total_decisions": 0,
            "duplicates_skipped": 0,
            "errors": 0,
            "start_time": _now(),
        }

    def set_ai_engine(self, engine: AIDecisionEngine):
        self._ai_engine = engine

    def on_decision(self, cb: callable):
        """Register callback for new decisions (e.g., WebSocket broadcast)."""
        self._callbacks.append(cb)

    # ── Snapshot building ──

    def build_snapshot(
        self,
        symbol: str,
        interval: str = "15m",
        context_snap: dict | None = None,
        indicator_snap: dict | None = None,
        structure_snap: dict | None = None,
        pattern_snap: dict | None = None,
        mtf_snap: dict | None = None,
        sr_snap: dict | None = None,
        stream_state: str = "connected",
        last_price: float | None = None,
    ) -> AIMarketSnapshot:
        """Build a unified AI market snapshot from all engine outputs."""
        snap = AIMarketSnapshot(symbol=symbol, timestamp=_now(), last_price=last_price)
        snap.stream_state = stream_state

        # Market context
        if context_snap:
            snap.trend = context_snap.get("trend")
            snap.momentum = context_snap.get("momentum")
            snap.volatility = context_snap.get("volatility_state")
            snap.market_regime = context_snap.get("market_regime")
            snap.session = context_snap.get("session")
            snap.institutional_bias = context_snap.get("institutional_bias")
            snap.overall_bias = context_snap.get("overall_bias")
            snap.context_confidence = context_snap.get("confidence")
            snap.market_phase = context_snap.get("market_phase")
            snap.trend_strength = context_snap.get("trend_strength")

        # Indicators
        if indicator_snap:
            snap.ema_9 = indicator_snap.get("ema_9")
            snap.ema_20 = indicator_snap.get("ema_20")
            snap.ema_50 = indicator_snap.get("ema_50")
            snap.ema_200 = indicator_snap.get("ema_200")
            snap.sma_20 = indicator_snap.get("sma_20")
            snap.sma_50 = indicator_snap.get("sma_50")
            snap.rsi_14 = indicator_snap.get("rsi_14")
            snap.macd = indicator_snap.get("macd")
            snap.macd_signal = indicator_snap.get("macd_signal")
            snap.macd_histogram = indicator_snap.get("macd_histogram")
            snap.atr_14 = indicator_snap.get("atr_14")
            snap.vwap = indicator_snap.get("vwap")
            snap.adx_14 = indicator_snap.get("adx_14")
            snap.supertrend_trend = indicator_snap.get("supertrend_trend")
            snap.bb_upper = indicator_snap.get("bb_upper")
            snap.bb_lower = indicator_snap.get("bb_lower")
            snap.volume = indicator_snap.get("candle_volume") or indicator_snap.get("volume")

        # Structure
        if structure_snap:
            snap.valid_structure = structure_snap.get("valid_structure")
            snap.bos_count = structure_snap.get("bos_count")
            snap.choch_count = structure_snap.get("choch_count")
            snap.market_phase = structure_snap.get("market_phase") or snap.market_phase
            snap.trend_strength = structure_snap.get("trend_strength") or snap.trend_strength

        # Patterns
        if pattern_snap:
            snap.strongest_pattern = pattern_snap.get("strongest_pattern")
            snap.pattern_direction = pattern_snap.get("pattern_direction")
            snap.pattern_count = pattern_snap.get("pattern_count")
            snap.pattern_bias = pattern_snap.get("pattern_bias")

        # Support/Resistance
        if sr_snap:
            snap.nearest_support = sr_snap.get("nearest_support")
            snap.nearest_resistance = sr_snap.get("nearest_resistance")
            snap.breakout_state = sr_snap.get("breakout_state")
            price = last_price or (context_snap or {}).get("candle_close")
            if snap.nearest_support and price and price > 0:
                snap.support_distance_pct = round(
                    (price - snap.nearest_support) / price * 100, 2
                )
            if snap.nearest_resistance and price and price > 0:
                snap.resistance_distance_pct = round(
                    (snap.nearest_resistance - price) / price * 100, 2
                )

        # MTF
        if mtf_snap:
            snap.mtf_alignment = mtf_snap.get("alignment_level")
            snap.mtf_score = mtf_snap.get("alignment_score")
            snap.mtf_bias = mtf_snap.get("institutional_bias")

        # Data freshness
        snap.data_freshness = "live" if stream_state == "connected" else stream_state

        return snap

    # ── Decision execution ──

    def analyze(
        self,
        symbol: str,
        interval: str = "15m",
        context_snap: dict | None = None,
        indicator_snap: dict | None = None,
        structure_snap: dict | None = None,
        pattern_snap: dict | None = None,
        mtf_snap: dict | None = None,
        sr_snap: dict | None = None,
        stream_state: str = "connected",
        candle_timestamp: str | None = None,
    ) -> AIDecision | None:
        """
        Build snapshot, check freshness, deduplicate, and produce AI decision.

        Returns None if decision is deduplicated (already made for this context).
        """
        start = time.time()

        # 1. Build unified snapshot
        snapshot = self.build_snapshot(
            symbol=symbol,
            interval=interval,
            context_snap=context_snap,
            indicator_snap=indicator_snap,
            structure_snap=structure_snap,
            pattern_snap=pattern_snap,
            mtf_snap=mtf_snap,
            sr_snap=sr_snap,
            stream_state=stream_state,
            last_price=None,
        )

        # 2. Data freshness guard
        if snapshot.data_freshness in ("stale", "disconnected"):
            return self._make_wait_decision(
                symbol=symbol,
                reason="Market data is stale or disconnected",
                snapshot=snapshot,
                candle_timestamp=candle_timestamp,
            )

        # 3. Deduplication — same context hash = skip
        ctx = {
            "symbol": symbol,
            "candle_timestamp": candle_timestamp or _now(),
            "rsi": snapshot.rsi_14,
            "macd_hist": snapshot.macd_histogram,
            "trend": snapshot.trend,
            "mtf_align": snapshot.mtf_alignment,
            "vwap": snapshot.vwap,
        }
        ctx_hash = hashlib.md5(
            json.dumps(ctx, sort_keys=True, default=str).encode()
        ).hexdigest()

        if ctx_hash in self._snapshot_hashes:
            self._stats["duplicates_skipped"] += 1
            return None

        self._snapshot_hashes.add(ctx_hash)
        # Cap hash set size
        if len(self._snapshot_hashes) > 1000:
            self._snapshot_hashes.clear()
            self._snapshot_hashes.add(ctx_hash)

        # 4. Run AI engine
        if self._ai_engine:
            unit = self._ai_engine._get_unit(symbol)
            if context_snap:
                unit.update_context(context_snap)
            if mtf_snap:
                unit.update_mtf(mtf_snap)
            if sr_snap:
                unit.update_sr(sr_snap)

        latest = self._ai_engine.latest(symbol) if self._ai_engine else None

        # 5. Build decision
        direction = "WAIT"
        if latest:
            dec = latest.get("decision", "NO_TRADE")
            trade_plan = latest.get("trade_plan", {})
            plan_dir = trade_plan.get("direction", "NONE")
            if dec in ("HIGH_CONVICTION", "MODERATE") and plan_dir in ("BUY", "SELL"):
                direction = plan_dir
            elif dec == "LOW_CONVICTION" and plan_dir in ("BUY", "SELL"):
                direction = plan_dir

        latency = (time.time() - start) * 1000

        decision = AIDecision(
            decision_id=_new_id(),
            trace_id=f"trace_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            timestamp=_now(),
            candle_timestamp=candle_timestamp or _now(),
            direction=direction,
            decision=latest.get("decision", "NO_TRADE") if latest else "NO_TRADE",
            score=(latest or {}).get("score", 0),
            confidence=(latest or {}).get("confidence", 0),
            score_grade=(latest or {}).get("score_grade", ""),
            confidence_grade=(latest or {}).get("confidence_grade", ""),
            risk_level=(latest or {}).get("risk_level", ""),
            reasoning=(latest or {}).get("reasoning", ["Insufficient data"]),
            evidence=self._build_evidence(snapshot),
            market_snapshot=snapshot.to_dict(),
            snapshot_hash=ctx_hash,
            data_freshness=snapshot.data_freshness,
            latency_ms=latency,
        )

        # 6. Store and notify
        self._decisions[decision.decision_id] = decision
        self._history.append(decision)
        self._stats["total_decisions"] += 1

        for cb in self._callbacks:
            try:
                cb(decision)
            except Exception:
                pass

        return decision

    # ── Helpers ──

    def _make_wait_decision(
        self,
        symbol: str,
        reason: str,
        snapshot: AIMarketSnapshot,
        candle_timestamp: str | None = None,
    ) -> AIDecision:
        """Create a WAIT decision when data is unavailable or stale."""
        decision = AIDecision(
            decision_id=_new_id(),
            symbol=symbol,
            timestamp=_now(),
            candle_timestamp=candle_timestamp or _now(),
            direction="WAIT",
            decision="NO_TRADE",
            reasoning=[reason],
            evidence={},
            market_snapshot=snapshot.to_dict(),
            snapshot_hash="",
            data_freshness=snapshot.data_freshness,
        )
        self._history.append(decision)
        self._stats["total_decisions"] += 1
        return decision

    def _build_evidence(self, snap: AIMarketSnapshot) -> dict[str, Any]:
        """Build structured evidence summary from snapshot."""
        evidence = {}
        if snap.trend:
            evidence["trend"] = snap.trend
        if snap.momentum:
            evidence["momentum"] = snap.momentum
        if snap.volatility:
            evidence["volatility"] = snap.volatility
        if snap.mtf_alignment:
            evidence["mtf_alignment"] = f"{snap.mtf_alignment} (score: {snap.mtf_score})"
        if snap.market_regime:
            evidence["market_regime"] = snap.market_regime
        if snap.nearest_support:
            evidence["nearest_support"] = snap.nearest_support
        if snap.nearest_resistance:
            evidence["nearest_resistance"] = snap.nearest_resistance
        if snap.strongest_pattern:
            evidence["strongest_pattern"] = snap.strongest_pattern
        if snap.institutional_bias:
            evidence["institutional_bias"] = snap.institutional_bias
        if snap.overall_bias:
            evidence["overall_bias"] = snap.overall_bias
        return evidence

    # ── Queries ──

    def get_latest(self, symbol: str) -> AIDecision | None:
        for d in reversed(self._history):
            if d.symbol == symbol:
                return d
        return None

    def get_decision(self, decision_id: str) -> AIDecision | None:
        return self._decisions.get(decision_id)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._history[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return dict(self._stats)

"""
MarketMind AI — Trade Signal Model

A real signal generated after full fresh-data analysis pipeline execution.
Auto-expires when its market context is no longer valid.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _new_id(prefix: str = "sig") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class TradeSignal:
    """
    Complete trade signal generated from fresh Zerodha Kite market analysis.

    A signal is only valid when:
    - Generated from fresh market data (source_provider == "ZERODHA_KITE")
    - All timestamps are recent and verified
    - Indicators are fully initialized
    - Regime detection completed
    - AI decision produced
    - Approval gates passed
    - Risk validation passed

    Auto-expires when any condition invalidates its context.
    """

    # ── Core identifiers ──
    signal_id: str = ""
    decision_id: str = ""
    trade_plan_id: str = ""
    analysis_id: str = ""

    # ── Instrument ──
    symbol: str = ""
    instrument_token: int = 0
    exchange: str = "NSE"
    tradingsymbol: str = ""

    # ── Direction ──
    direction: str = "NONE"  # BUY, SELL

    # ── Timestamps ──
    generated_at: str = ""
    candle_timestamp: str = ""
    tick_timestamp: str = ""
    decision_timestamp: str = ""
    expires_at: str = ""

    # ── Prices and levels ──
    ltp: float = 0.0
    entry: float = 0.0
    entry_zone_high: float = 0.0
    entry_zone_low: float = 0.0
    stop_loss: float = 0.0
    target: float = 0.0
    target2: float = 0.0

    # ── Sizing ──
    quantity: int = 0
    risk_amount: float = 0.0
    expected_reward: float = 0.0
    risk_reward_ratio: float = 0.0
    max_risk_percent: float = 0.0
    notional: float = 0.0

    # ── Market context ──
    timeframe: str = "15m"
    strategy: str = ""
    market_regime: str = ""
    regime_confidence: float = 0.0

    # ── AI / Quality ──
    ai_score: int = 0
    ai_confidence: int = 0
    ai_decision: str = "NO_TRADE"
    trade_grade: str = "NONE"

    # ── Freshness & provider ──
    source_provider: str = "ZERODHA_KITE"
    data_freshness: str = "LIVE"
    data_version: str = ""
    candle_version: str = ""

    # ── Validation results ──
    approval_gates_passed: bool = False
    risk_validation_passed: bool = False
    signal_validated: bool = False
    false_signal_check_passed: bool = False
    quote_reconciliation_passed: bool = False

    # ── Rejection reasons ──
    rejection_reasons: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)

    # ── Supporting evidence ──
    supporting_indicators: dict[str, Any] = field(default_factory=dict)
    structure_evidence: dict[str, Any] = field(default_factory=dict)
    pattern_evidence: dict[str, Any] = field(default_factory=dict)
    sr_evidence: dict[str, Any] = field(default_factory=dict)
    mtf_evidence: dict[str, Any] = field(default_factory=dict)
    regime_evidence: dict[str, Any] = field(default_factory=dict)

    # ── Status ──
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, EXECUTED

    def is_expired(self, current_time: str | None = None) -> bool:
        """Check if the signal has expired based on its expiry timestamp."""
        if not self.expires_at:
            return False
        now = current_time or _now()
        try:
            exp = datetime.fromisoformat(self.expires_at)
            now_dt = datetime.fromisoformat(now)
            if now_dt.tzinfo is None:
                now_dt = now_dt.replace(tzinfo=timezone.utc)
            return now_dt > exp
        except (ValueError, TypeError):
            return False

    def age_ms(self, current_time: str | None = None) -> float:
        """Age of the signal in milliseconds since generation."""
        if not self.generated_at:
            return -1.0
        now = current_time or _now()
        try:
            gen = datetime.fromisoformat(self.generated_at)
            now_dt = datetime.fromisoformat(now)
            if gen.tzinfo is None:
                gen = gen.replace(tzinfo=timezone.utc)
            if now_dt.tzinfo is None:
                now_dt = now_dt.replace(tzinfo=timezone.utc)
            return (now_dt - gen).total_seconds() * 1000
        except (ValueError, TypeError):
            return -1.0

    def is_price_in_entry_zone(self, current_price: float) -> bool:
        """Check if current price is still within the approved entry zone."""
        if self.entry_zone_low <= 0 or self.entry_zone_high <= 0:
            return True  # No zone defined — skip check
        return self.entry_zone_low <= current_price <= self.entry_zone_high

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "decision_id": self.decision_id,
            "trade_plan_id": self.trade_plan_id,
            "analysis_id": self.analysis_id,
            "symbol": self.symbol,
            "instrument_token": self.instrument_token,
            "exchange": self.exchange,
            "tradingsymbol": self.tradingsymbol,
            "direction": self.direction,
            "generated_at": self.generated_at,
            "candle_timestamp": self.candle_timestamp,
            "tick_timestamp": self.tick_timestamp,
            "decision_timestamp": self.decision_timestamp,
            "expires_at": self.expires_at,
            "ltp": self.ltp,
            "entry": self.entry,
            "entry_zone_high": self.entry_zone_high,
            "entry_zone_low": self.entry_zone_low,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "target2": self.target2,
            "quantity": self.quantity,
            "risk_amount": self.risk_amount,
            "expected_reward": self.expected_reward,
            "risk_reward_ratio": self.risk_reward_ratio,
            "max_risk_percent": self.max_risk_percent,
            "notional": self.notional,
            "timeframe": self.timeframe,
            "strategy": self.strategy,
            "market_regime": self.market_regime,
            "regime_confidence": self.regime_confidence,
            "ai_score": self.ai_score,
            "ai_confidence": self.ai_confidence,
            "ai_decision": self.ai_decision,
            "trade_grade": self.trade_grade,
            "source_provider": self.source_provider,
            "data_freshness": self.data_freshness,
            "data_version": self.data_version,
            "candle_version": self.candle_version,
            "approval_gates_passed": self.approval_gates_passed,
            "risk_validation_passed": self.risk_validation_passed,
            "signal_validated": self.signal_validated,
            "false_signal_check_passed": self.false_signal_check_passed,
            "quote_reconciliation_passed": self.quote_reconciliation_passed,
            "status": self.status,
            "rejection_reasons": self.rejection_reasons,
            "blocking_reasons": self.blocking_reasons,
            "supporting_indicators": self.supporting_indicators,
            "structure_evidence": self.structure_evidence,
            "pattern_evidence": self.pattern_evidence,
            "sr_evidence": self.sr_evidence,
            "mtf_evidence": self.mtf_evidence,
            "regime_evidence": self.regime_evidence,
        }


def create_signal(
    symbol: str,
    direction: str,
    ltp: float,
    entry: float,
    stop_loss: float,
    target: float,
    timeframe: str = "15m",
    expires_after_seconds: int = 300,
    **kwargs,
) -> TradeSignal:
    """Factory to create a TradeSignal with auto-generated IDs and timestamps."""
    now = _now()
    sig = TradeSignal(
        signal_id=_new_id("sig"),
        analysis_id=_new_id("anl"),
        symbol=symbol,
        direction=direction,
        ltp=ltp,
        entry=entry,
        stop_loss=stop_loss,
        target=target,
        generated_at=now,
        expires_at=_future_str(expires_after_seconds),
        timeframe=timeframe,
        **kwargs,
    )
    return sig


def _future_str(seconds: int) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="milliseconds")

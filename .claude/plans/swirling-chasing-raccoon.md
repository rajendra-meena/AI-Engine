# Pre-Market Fixes & Live Verification Plan

**Date:** Sunday, 26 July 2026 (for market open Monday 27 July 2026 @ 09:15 IST = 03:45 UTC)
**Mode:** Paper + Shadow only. Controlled Live stays blocked. No real Zerodha orders.

---

## Context

The system has never been verified against live market data end-to-end. Two structural defects must be fixed before market open, then a comprehensive dry-run verification script executes during the active NSE session to capture actual evidence from every pipeline stage.

---

## Fix #1: Complete Pre-Market Warmup Before Waiting for Ticks

**Problem:** `HistoricalWarmupEngine` is instantiated at `main.py:352` but `warmup_all()` is never called. The engine seeding (lines 391-458) uses `market_service.get_intraday()` (Yahoo Finance) which fetches only ~25 candles (5 days of 15m data) — insufficient for EMA(200). The engine sits in `WAITING_FOR_TICKS` until the first exchange tick arrives. Two states (`STATE_LOADING_HISTORY` at line 117, `STATE_WARMING_INDICATORS` at line 120) exist as dead code — clearly intended for this and never used.

**Solution:** Trigger full Kite historical warmup inside `ZerodhaMarketDataEngine.start()` after subscription and Before transitioning to `STATE_WAITING_FOR_TICKS`. Use a **callback pattern**: `ZerodhaMarketDataEngine` fetches warmup data via `HistoricalWarmupEngine`, then calls a callback set by `main.py` to feed candles into downstream engines directly (bypassing CandleEngine since warmup candles are historical, not current-session).

### Why NOT EventBus for warmup feeding:
- Warmup candles represent *past* sessions (yesterday, last week). Publishing them as `CANDLE_CLOSED` via EventBus would cause `CandleEngine` to build active candles for those historical periods — producing wrong active-candle state.
- The existing seeding pattern in `main.py` lines 396-454 (direct engine calls to IndicatorEngine, MarketStructureEngine, PatternEngine, SREngine) is correct.

### Changes:

**A. `backend/services/zerodha_market_data_engine.py`**
- Import `HistoricalWarmupEngine`
- Add `_warmup_engine: HistoricalWarmupEngine | None = None` attribute
- Add `_warmup_feed_callback: Callable | None = None` attribute
- Add setters: `set_warmup_engine()`, `set_warmup_feed_callback()`
- Add new method `_run_warmup_after_subscribe()` that:
  1. Computes `min_candles = IndicatorComputeUnit.compute_max_warmup_needed() + 50`
  2. `self._set_state(STATE_LOADING_HISTORY)` — uses existing dead state enum
  3. `await self._warmup_engine.warmup_all(canonical, ["1m","3m","5m","15m"], min_candles)`
  4. `self._set_state(STATE_WARMING_INDICATORS)` — uses existing dead state enum
  5. If `_warmup_feed_callback`, calls it with results; else fallback to bare transition
  6. `self._set_state(STATE_CONNECTED)` — skip WAITING_FOR_TICKS
- Insert call at line ~239 after `_subscribe_default_universe()`, replacing the line that sets `STATE_WAITING_FOR_TICKS` directly

**B. `backend/main.py`**
- After lines 352-354 (`warmup_engine` created) and zerodha_engine created (342-346), add:
  ```python
  zerodha_engine.set_warmup_engine(warmup_engine)
  zerodha_engine.set_warmup_feed_callback(_feed_warmup_candles)
  ```
- Define `_feed_warmup_candles(results)` that mirrors lines 396-454 (direct engine calls) but reading from `warmup_engine.get_candles()`
- Keep existing seeding block (lines 387-458) wrapped in `if not warmup_engine._kite:` as fallback

**C. `backend/api/auto_trade.py`**
- In `_engine_lifecycle()` (~line 935), modify wait loop:
  ```python
  for _ in range(60):
      if not _engine_running: return
      if _zerodha_engine.state in (STATE_CONNECTED, STATE_SCANNING):
          _engine_state = ENGINE_STATE_SCANNING; break
      if _freshness_tracker and _freshness_tracker.get_status_summary().get("live", 0) > 0:
          _engine_state = ENGINE_STATE_SCANNING; break
      await asyncio.sleep(1)
  ```

---

## Fix #2: Dynamic Warmup Depth From Indicators

**Problem:** Indicator warmup depth defaults to 250 (hardcoded). If indicator configuration changes (EMA periods added/removed), the warmup count won't follow. The value is correct for the current set (EMA 200 → 200 + 50 buffer = 250), but it should be computed dynamically.

**Solution:** Add a classmethod to `IndicatorComputeUnit` that creates a probe instance and aggregates `warmup_needed()` across all its indicator instances.

### Changes:

**A. `backend/indicators/engine.py`** — add to `IndicatorComputeUnit`:
```python
@classmethod
def compute_max_warmup_needed(cls) -> int:
    """Max candles needed across all indicators + safety buffer."""
    unit = cls("_probe_", "_probe_")
    indicators = [
        unit.ema_9, unit.ema_20, unit.ema_50, unit.ema_200,
        unit.sma_20, unit.sma_50, unit.rsi_14, unit.atr_14,
        unit.vwap, unit.macd, unit.adx_14, unit.supertrend,
    ]
    return max(ind.warmup_needed() for ind in indicators)
```
This returns 200 (from EMA 200). The caller adds the 50-candle buffer.

**B. `backend/services/zerodha_market_data_engine.py`**
- Import `IndicatorComputeUnit` from `indicators.engine`
- In `_run_warmup_after_subscribe()`:
  ```python
  min_candles = IndicatorComputeUnit.compute_max_warmup_needed() + 50
  ```
  Returns 250 (200 + 50) — matches the current hardcoded default, but now dynamic.

---

## Verification Script: `backend/verification/live_market_verifier.py`

A standalone async module. Run via: `python -m backend.verification.live_market_verifier --mode shadow --output report.json`

### Architecture (4 files):

```
backend/verification/
  __init__.py          — package marker
  live_market_verifier.py — main entry point
  evidence.py          — evidence collector (thread-safe singleton)
  reporters.py         — JSON + human-readable formatters
```

### Evidence collector (`evidence.py`):

Thread-safe singleton with an `EvidenceItem` dataclass (name, status: PASS/FAIL/WARN/INFO, detail dict, timestamp). Records evidence as it's collected.

### Main entry point structure:

```python
async def run_verification(mode="shadow", output=None):
    collector = EvidenceCollector()
    
    # Phase 1: Pre-market (no ticks expected)
    app = await bootstrap_services()  # replicates main.py startup
    
    # Record warmup & subscription evidence
    tokens = app.zerodha_engine._token_to_symbol
    for t, s in tokens.items():
        collector.record("instrument_tokens", "PASS", token=t, symbol=s)
    
    warmup_status = app.warmup_engine.get_all_status()
    # Record each (symbol, interval) warmup completion
    
    # Phase 2: Market hours (wait for live data)
    # Subscribe to EventBus for evidence capture
    tick_buffer = []
    app.event_bus.subscribe(NEW_TICK, lambda e: tick_buffer.append(e))
    
    # Wait 5-10 seconds for tick accumulation
    await asyncio.sleep(10)
    
    # Record 5+ tick samples
    for i, t in enumerate(tick_buffer[:5]):
        collector.record("live_ticks", "PASS", ...)
    
    # Wait for CANDLE_CLOSED (up to 5 min)
    candle_event = asyncio.Event()
    app.event_bus.subscribe(CANDLE_CLOSED, lambda e: candle_event.set())
    await asyncio.wait_for(candle_event.wait(), timeout=300)
    
    # Record candle, volume, indicator, context, regime, AI decision evidence
    # ... (one block per evidence item)
    
    # Phase 3: Verify safety systems
    # Quote reconciliation, paper/shadow trades, WS recovery, dedup
    
    # Phase 4: Verdict
    report = collector.get_report()
    report["verdict"] = compute_verdict(report)
    return report
```

### 17 Evidence Capture Points:

| # | Item | Method | Pass Criteria |
|---|------|--------|--------------|
| 1 | Instrument tokens | Read `_token_to_symbol` after load | All 3 canonical symbols mapped |
| 2 | Live ticks (5+) | Buffer from tick callback | ≥5 ticks with non-zero price, valid timestamp |
| 3 | Tick freshness | `_freshness.get_status_summary()` | `"live" > 0` |
| 4 | Complete candle | Subscribe `CANDLE_CLOSED` | Event received with valid OHLCV |
| 5 | Volume calculation | `candle["volume"] > 0` | Volume positive |
| 6 | Indicators | `indicator_engine.latest_snapshot()` | `all_ready == True`, EMA(200) not None |
| 7 | Trading context | `trading_context_engine.latest()` | Momentum, volatility, strength present |
| 8 | Regime | `regime_engine.latest()` | Regime string and confidence present |
| 9 | AI decision | `ai_decision_engine.latest()` | Score, confidence, direction present |
| 10 | BUY/SELL scores | Run `_build_opportunity_score()` | Both scores with reasoning |
| 11 | Risk validation | `risk_engine.validate()` | `execution_permitted` checked |
| 12 | Trade plan | `trade_planner.create_plan()` | Direction, entry, SL, target present |
| 13 | Quote reconciliation | `zerodha_engine.reconcile_quote()` | `passed == True` |
| 14 | Paper trade | `paper_broker.execute()` | Only if all safety pass, else blocked reason |
| 15 | Shadow trade | `shadow_tracker.create_shadow_trade()` | Trade created, tracked by ticks |
| 16 | WS disconnect/recovery | Force disconnect, wait reconnect | State transitions correct, tokens restored |
| 17 | Duplicate protection | Same candle_closed event twice | Second analysis skipped (cooldown) |

### Dry-Run Safety:
- Runtime mode set to SHADOW (never LIVE)
- Controlled Live activation gate stays blocked
- `LiveExecutionGate.authorize()` called but result captured — never forwarded to `ExecutionGateway`
- Script never calls `place_order()` — stops at validation
- Safety interlock wraps broker adapter to throw on any real order attempt

### Verdict Thresholds:

| Verdict | Criteria |
|---|---|
| **Not Ready** | Any critical evidence point failed (no ticks, no candles, indicators not ready) |
| **Ready for Paper Trading** | All evidence points pass, Paper broker verified |
| **Ready for Shadow Trading** | All evidence passes except Paper execution (Shadow-only) |
| **Ready for Controlled Live Dry Run** | All evidence passes + Paper + Shadow + gate working |
| **Ready for Controlled Live** | All evidence passes + human confirms after reviewing report |

---

## Implementation Order

1. Fix #2: `backend/indicators/engine.py` — add `compute_max_warmup_needed()`
2. Fix #1: `backend/services/zerodha_market_data_engine.py` — add warmup + callback
3. Fix #1: `backend/main.py` — wire warmup_engine to zerodha_engine with feed callback
4. Fix #1: `backend/api/auto_trade.py` — update lifecycle to accept warmup completion
5. Create `backend/verification/__init__.py` — package marker
6. Create `backend/verification/evidence.py` — evidence collector
7. Create `backend/verification/reporters.py` — report formatters
8. Create `backend/verification/live_market_verifier.py` — main script
9. Test with compilation check + logic review (no live market)
10. Monday 09:15 IST: run verification live

## Files Modified

- `backend/services/zerodha_market_data_engine.py` — warmup integration, callback, dynamic depth
- `backend/main.py` — wire warmup_engine, feed callback, fallback seeding
- `backend/indicators/engine.py` — add `compute_max_warmup_needed()`
- `backend/api/auto_trade.py` — lifecycle wait logic

## Files Created

- `backend/verification/__init__.py`
- `backend/verification/live_market_verifier.py`
- `backend/verification/evidence.py`
- `backend/verification/reporters.py`

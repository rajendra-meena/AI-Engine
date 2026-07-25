# MarketMind AI — Complete System Analysis Report

> **Generated:** 2026-07-23  
> **Scope:** Full codebase audit (frontend + backend)  
> **Method:** Static code analysis of every module, engine, API, component, and store

---

## PART 1 — HIGH LEVEL SUMMARY

### 1.1 What This Application Is

**MarketMind AI** is an institutional-grade AI-powered trading platform that combines real-time market data analysis, multi-engine technical analysis, AI-driven decision scoring, strategy building, machine learning, and a full research lab. It is designed as a unified desktop-grade web application with a FastAPI Python backend and a Next.js/React TypeScript frontend.

The system ingests live market data via Yahoo Finance API → aggregates into candles → runs 6 analytical engines in parallel (indicators, market structure, patterns, support/resistance, multi-timeframe, trading context) → feeds a capstone AI Decision Engine → produces trade plans with scores, confidence, risk levels, and explanations → surfaces everything through a real-time WebSocket-connected UI.

### 1.2 Business Problem Solved

Retail and institutional traders face information overload: dozens of indicators, conflicting signals, emotional decision-making, and no structured way to combine multiple analysis dimensions into a single actionable verdict. MarketMind solves this by:

- **Unifying** all technical analysis into one platform
- **Quantifying** setups with objective scores (0-100)
- **Explaining** every decision with structured reasoning
- **Automating** the analysis pipeline so traders focus on execution
- **Backtesting** and **optimizing** strategies before risking capital

### 1.3 Who Should Use It

- **Algo traders** — build and deploy systematic strategies
- **Quantitative researchers** — use the research lab for backtesting and ML
- **Intraday traders** — real-time scanner and AI scores for live decision support
- **Swing traders** — multi-timeframe analysis for position sizing and direction
- **Institutional desks** — structured trade plans with risk management built in

### 1.4 Trader Type Fit

| Trader Type | Fit | Why |
|---|---|---|
| **Beginner** | ⭐⭐⭐ | AI explanations + simple dashboard make it accessible |
| **Intraday** | ⭐⭐⭐⭐⭐ | Real-time scanner, live AI updates, 1m-60m intervals |
| **Swing** | ⭐⭐⭐⭐ | MTF analysis, daily timeframe support |
| **Institutional** | ⭐⭐⭐ | Structured trade plans, risk engine, multi-symbol |
| **Quant** | ⭐⭐⭐⭐ | Research lab, ML engine, strategy builder |
| **Algo** | ⭐⭐⭐ | Strategy builder exists; execution is placeholder |
| **Options** | ⭐ | No options chain, greeks, or options-specific analysis |

### 1.5 Overall Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js / React)                │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────┐ ┌────────┐ │
│  │Dashboard│ │ Live     │ │Scanner │ │Command│ │Research│ │
│  │Workspace│ │ Portfolio│ │Strat   │ │ML     │ │Explain │ │
│  └────┬────┘ └────┬─────┘ └───┬────┘ └───┬───┘ └───┬────┘ │
│       └────────────┴──────────┴──────────┴──────────┘       │
│                          │ WebSocket / HTTP                  │
├──────────────────────────┼──────────────────────────────────┤
│               BACKEND (FastAPI Python)                       │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐   │
│  │REST APIs│ │WebSocket │ │Event Bus │ │ Service Layer  │   │
│  │         │ │Gateway   │ │(pub/sub) │ │                │   │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └───────┬───────┘   │
│       └───────────┴────────────┴───────────────┘            │
│                              │                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              ENGINE LAYER (Event-Driven)             │    │
│  │  ┌─────────┐ ┌──────────┐ ┌──────┐ ┌────────────┐  │    │
│  │  │Indicators│ │Structure │ │Patterns │ │Trading Ctx│  │    │
│  │  └────┬────┘ └────┬─────┘ └──┬───┘ └──────┬─────┘  │    │
│  │       └──────┬────┴──────────┴─────────────┘        │    │
│  │              ▼                                       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────────┐   │    │
│  │  │SR Engine │ │MTF Engine │ │ AI Decision Engine │   │    │
│  │  └──────────┘ └──────────┘ └────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DATA LAYER                              │    │
│  │  Yahoo Finance → Tick Engine → Candle Engine         │    │
│  │  CSV Disk Cache → SQLite DB → In-Memory Snapshots    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.6 Complete Data Flow

**Step 1 — Market Data Ingestion**
- `YahooProvider` fetches intraday data from Yahoo Finance API using yfinance library
- Supports: `^NSEI` (NIFTY 50), `^BSESN` (SENSEX), `^NSEBANK` (BANKNIFTY)
- Fetches 1-day, 5-day, 1-month, 3-month, 1-year periods at 1m-60m intervals
- Data cached in CSV files under `/backend/cache/`

**Step 2 — Tick Engine → Stream Router**
```
YahooProvider → TickEngine → StreamRouter → EventBus
```
- TickEngine polls Yahoo Finance every ~5-30 seconds
- StreamRouter processes raw ticks and publishes structured events

**Step 3 — Candle Aggregation**
```
StreamRouter → CandleEngine → EventBus (candle_closed, candle_updated)
```
- CandleEngine aggregates ticks into 1m, 3m, 5m, 15m, 30m, 60m candles
- Publishes `CANDLE_UPDATED` and `CANDLE_CLOSED` events

**Step 4 — Analytical Engines (run in parallel on each candle_closed)**
```
CandleEngine → Indicators Engine → EventBus (indicators_updated)
CandleEngine → Market Structure Engine → EventBus (structure_updated)
CandleEngine → Pattern Engine → EventBus (pattern_updated)
```

**Step 5 — Derived Engines (run on upstream updates)**
```
Indicators + Structure → Trading Context Engine → EventBus (trading_context_updated)
Indicators + Structure + Patterns → SR Engine → EventBus (sr_updated)
Multiple intervals → MTF Engine → EventBus (mtf_updated)
```

**Step 6 — AI Decision Engine (capstone)**
```
Trading Context + MTF + SR → AI Decision Engine → EventBus (ai_decision_updated)
```
- ScoreEngine → evaluates setup quality (0-100)
- ConfidenceEngine → evaluates data reliability
- RiskEngine → evaluates market/position risk
- TradePlanner → builds entry, SL, target plan
- Orchestrator → produces final decision + score + confidence + reasoning

**Step 7 — WebSocket Push**
```
EventBus → WebSocketGateway → Frontend Store
```
- All engine outputs are pushed to connected WebSocket clients
- Frontend stores (Zustand) update reactively → React components re-render

**Step 8 — User Interaction**
```
Frontend → REST API → Backend Service
```
- User views AI decisions on Dashboard
- Runs scanner for opportunity screening
- Builds strategies via Strategy Builder
- Views explainability timeline
- Manages portfolio (paper)
- Runs backtests in Research Lab

---

## PART 2 — LIVE MARKET ANALYSIS

### VERDICT: PARTIALLY

### 2.1 Data Source

The backend uses **Yahoo Finance** (yfinance library) to fetch market data:

- `backend/services/yahoo_provider.py` — actual HTTP calls to Yahoo Finance API
- Tickers: `^NSEI` (NIFTY 50), `^NSEBANK` (BANKNIFTY), `^BSESN` (SENSEX)
- Methods: `fetch_intraday()`, `fetch_daily()`, `fetch_multi_symbol()`

### 2.2 Update Frequency

| Component | Frequency | Mechanism | Status |
|---|---|---|---|
| **Tick Data** | Every ~5-30s (poll) | TickEngine polls Yahoo Finance | ✅ Real |
| **Candles** | On each tick batch | CandleEngine aggregates ticks | ✅ Real |
| **Indicators** | On each candle_closed | IndicatorEngine computes in real-time | ✅ Real |
| **Market Structure** | On each candle_closed | MarketStructureEngine updates | ✅ Real |
| **Patterns** | On each candle_closed | PatternEngine detects patterns | ✅ Real |
| **Trading Context** | On indicator + structure update | TradingContextEngine merges | ✅ Real |
| **SR Levels** | On context + indicator update | SREngine computes | ✅ Real |
| **MTF Analysis** | On multiple timeframe candles | MTFEngine analyzes alignment | ✅ Real |
| **AI Decision** | On context + MTF + SR update | AIDecisionEngine executes | ✅ Real |
| **Scanner** | Polls REST API every ~5s | Frontend hook calls backend | ✅ Real |
| **Charts** | WebSocket stream | TradingView chart via datafeed | ✅ Real |
| **Portfolio** | Static | No real-time P&L updates | ❌ Placeholder |
| **ML** | On-demand API call | Random results, not real | ❌ Stub |
| **Alerts** | Notification store | WebSocket-driven | ✅ Real |

### 2.3 WebSocket Architecture

- **Single shared WebSocket** connection via `WebSocketManager` singleton
- Backend: FastAPI WebSocket at `/ws` → `WebSocketGateway` → `EventBus`
- Reconnect: exponential backoff (1s → 2s → 4s → 8s → 30s max)
- Heartbeat: ping/pong with latency measurement
- Message queuing while disconnected
- Auto-resubscribe on reconnect

### 2.4 Realtime Hooks (Frontend)

| Hook | Purpose | Real-time? |
|---|---|---|
| `useRealtime()` | Establishes WebSocket, seeds initial data | ✅ Real |
| `useNotifications()` | Subscribes to all WS events, adds to store | ✅ Real |
| `useScanner()` | Polls REST API every 5s for scan results | ✅ Real |
| `useAnalytics()` | Subscribes to analytical engine snapshots | ✅ Real |

### 2.5 Key Limitation

The backend only polls Yahoo Finance every ~5-30 seconds. This is **not true real-time tick data** — it's near-real-time polling. A production system would need a live market data feed (e.g., WebSocket from broker, Bloomberg, or Reuters).

---

## PART 3 — REAL AI OR FAKE AI

### VERDICT: REAL AI — Dynamic Computation

### 3.1 AI Decision Engine (verified by reading full source)

The AI Decision Engine at `backend/ai_decision/engine.py` is a **genuine computational engine** that:

1. **Receives real data** from 3 upstream engines via EventBus:
   - `TRADING_CONTEXT_UPDATED` — trend, momentum, bias, volatility
   - `MTF_UPDATED` — multi-timeframe alignment, trading permission
   - `SR_UPDATED` — nearest support/resistance levels

2. **Computes dynamically** — every sub-module runs actual logic, no hardcoded results:

#### ScoreEngine (`modules/score.py`)
```
WEIGHTS = {
  "trend": 0.25, "alignment": 0.20, "momentum": 0.15,
  "structure": 0.15, "patterns": 0.10, "sr_proximity": 0.10, "volatility": 0.05
}

score = sum(weight * factor(trend/alignment/momentum/etc))
normalized = min(100, max(0, (score / max_weight) * 100))
```
- Uses real `trend`, `trend_strength`, `momentum`, `market_phase`, `pattern_bias`, `volatility_state` from context
- Uses real `alignment_level`, `alignment_score` from MTF
- Uses real `nearest_support`, `nearest_resistance` from SR
- Grades: VERY_HIGH (≥80), HIGH (≥60), MODERATE (≥40), LOW (≥20), VERY_LOW

#### ConfidenceEngine (`modules/confidence.py`)
```
base = 50
adjustments:
  + context_confidence_weighted
  + 15 if MTF fully aligned
  - 15 if MTF conflict
  + 10 if valid_structure
  + 10 if bias aligns with trend
  - 5 if bias/trend conflict
```
- Dynamically evaluates data quality, engine agreement, signal consistency

#### RiskEngine (`modules/risk.py`)
```
risk_score = 0
+ 30 if volatility expanding
+ 20 if near SR boundary
+ 50 if MTF says NO_TRADE
- determines max_risk_percent (0% to 1%)
```
- Outputs: risk_level (LOW/MEDIUM/HIGH/EXTREME), risk_score, max_risk_percent

#### TradePlanner (`modules/trade_plan.py`)
```
if bias == BULLISH and score >= 50 and risk in (LOW, MEDIUM):
  direction = "LONG"
  entry_zone = market order above nearest_support
  sl_zone = below nearest_support
  target_zones = near nearest_resistance
```
- Builds structured trade plan with entry, stop-loss, targets from real SR levels

#### Orchestrator (`modules/orchestrator.py`)
```
if score >= 60 and confidence >= 60 and risk not EXTREME and plan_valid:
  decision = "HIGH_CONVICTION"
elif score >= 50 and confidence >= 50 and risk not EXTREME:
  decision = "MODERATE"
else:
  decision = "NO_TRADE"
```
- Final verdict combines all sub-engine outputs with threshold logic
- Generates structured `reasoning` list (up to 8 items) and `warnings` (up to 5)

### 3.2 AI Decision Output

```python
DecisionSnapshot (
  symbol, timestamp,
  decision: "HIGH_CONVICTION" | "MODERATE" | "LOW_CONVICTION" | "NO_TRADE",
  score: 0-100,
  score_grade: "VERY_HIGH" | "HIGH" | "MODERATE" | "LOW" | "VERY_LOW",
  confidence: 0-100,
  confidence_grade: same,
  risk_level, risk_score, max_risk_percent,
  trade_plan: { direction, entry_zone, sl_zone, target_zones, ... },
  reasoning: [...],
  warnings: [...]
)
```

### 3.3 Is It Real AI?

**It is real rule-based expert system AI**, not machine learning AI. It evaluates market conditions against a hardcoded expert rule set (weighted scoring, thresholds, conditional logic). This is:

- ✅ **Dynamic** — every evaluation uses current live data
- ✅ **Explainable** — every decision has structured reasoning
- ✅ **Multi-factor** — uses 6+ independent data dimensions
- ❌ **Not ML-based** — no neural networks or trained models
- ❌ **Not adaptive** — rules are static, not learned from outcomes

### 3.4 AI Orchestrator

Located at `backend/api/ai_orchestrator.py`:
- `GET /api/ai-orchestrator/metrics` — returns AI engine stats
- `POST /api/ai-orchestrator/reset` — resets engine state
- `GET /api/ai-orchestrator/health` — health check
- These are real, thin wrappers over the AI Decision Engine

---

## PART 4 — LIVE TRADING CAPABILITY

### VERDICT: CANNOT TRADE LIVE — Paper Trading Only (Partial)

| Stage | Status | Details |
|---|---|---|
| **Observe Market** | ✅ Working | Yahoo Finance → Tick Engine → Candle Engine |
| **Analyze Market** | ✅ Working | All 6 analytical engines + AI Decision Engine |
| **Generate Trade Plan** | ✅ Working | TradePlanner produces entry/SL/targets |
| **Execute Order** | ❌ Placeholder | Broker adapters are stub interfaces |
| **Manage Trade** | ❌ Placeholder | No position monitoring or order management |
| **Close Trade** | ❌ Placeholder | No automated exit or manual close flow |
| **Journal Trade** | ❌ Missing | No trade journal or P&L recording |
| **Evaluate Trade** | ❌ Missing | No post-trade analysis or score vs outcome comparison |
| **Retrain ML** | ❌ Placeholder | ML routes exist but produce random data |

### 4.1 Broker Adapters — All Stubs

5 broker adapters exist but **none connect to a real broker API**:

| Broker | File | Real? |
|---|---|---|
| **Zerodha** | `broker/adapters/zerodha.py` | ❌ Stub — all methods return hardcoded values |
| **Angel** | `broker/adapters/angel.py` | ❌ Stub |
| **Fyers** | `broker/adapters/fyers.py` | ❌ Stub |
| **Upstox** | `broker/adapters/upstox.py` | ❌ Stub |
| **Dhan** | `broker/adapters/dhan.py` | ❌ Stub |

All adapters return:
```python
async def place_order(self, order): return order  # No actual API call
async def get_positions(self): return []  # Empty
async def get_funds(self): return BrokerFunds(available_margin=100000)  # Fake
```

### 4.2 Order Execution — Missing

- No `order/` or `execution/` directory in backend
- No order management service
- No position tracking service
- No P&L calculation service
- No trade journal or audit trail

### 4.3 Strategy Deployment — Placeholder

`POST /api/strategy/deploy` returns:
```python
{
  "id": "dep_str_1234",
  "strategyId": "...",
  "target": "...",
  "enabled": True,
  "schedule": None,  # Always None
  "capital": None,   # Always None
}
```
No actual deployment or scheduler exists.

---

## PART 5 — PREDICTION ENGINE

### VERDICT: Scores Current Conditions, Does Not Predict Future

### 5.1 Prediction Service

Located at `backend/services/prediction_service.py`:
- Called during startup (`init_prediction_service()`)
- No actual prediction model
- No forecast generation
- No time-series prediction

### 5.2 AI Decision vs Prediction

| Concept | What It Does |
|---|---|
| **AI Decision Score** | Evaluates **current** market conditions (0-100) based on trend, momentum, structure, patterns, SR, volatility |
| **Prediction** | Would forecast **future** price movement (price in N minutes/hours) |

The system does **not predict future prices**. It scores how favorable the current setup is. This is useful for decision support but is **not a predictive model**.

### 5.3 ML Predict — Stub

`POST /api/ml/predict` returns random results:
```python
score = 0.5 + sum(v * random.random() for v in features) / len(features)
return {"prediction": 1 if score >= 0.5 else 0, "probability": random, "confidence": random}
```

---

## PART 6 — SCANNER

### VERDICT: Working — Real-Time Opportunity Screening

### 6.1 Scanner Architecture

```
ScannerPage → useScanner hook → GET /api/scan → Backend → Returns ranked symbols
```

Frontend hooks:
- `useScanner()` — polls every 5 seconds, manages state via `useScannerStore`

Backend endpoint:
- `GET /api/scan` — returns scan results for configured symbols

### 6.2 How Scanning Works

1. **Symbols scanned**: NIFTY 50, BANK NIFTY, SENSEX (3 symbols)
2. **Ranking**: By AI score (descending)
3. **Score**: 0-100 from AI Decision Engine
4. **RR**: Calculated from SR levels (nearest resistance / support distance vs entry)
5. **Confidence**: From ConfidenceEngine
6. **Institutional bias**: From TradingContextEngine (overall_bias field)

### 6.3 Scanner Output

Each scan result includes:
- Symbol, price, change, volume
- AI score + grade
- Confidence + grade
- Risk level
- Direction bias
- RR ratio
- Institutional bias
- Pattern detection

### 6.4 Scanner Limitations

- Only 3 symbols configured (all indices)
- No individual stocks, futures, or options
- No custom watchlist
- No filtering by sector, volume, or other criteria

---

## PART 7 — STRATEGY ENGINE

### VERDICT: PARTIALLY WORKING — CRUD exists, evaluation/deployment are stubs

### 7.1 Strategy Builder API

| Endpoint | Method | Purpose | Status |
|---|---|---|---|
| `/api/strategies` | GET | List all strategies | ✅ Working |
| `/api/strategies/{id}` | GET | Get one strategy | ✅ Working |
| `/api/strategies` | POST | Create strategy | ✅ Working |
| `/api/strategies/{id}` | PUT | Update strategy | ✅ Working |
| `/api/strategies/{id}` | DELETE | Delete strategy | ✅ Working |
| `/api/strategy/templates` | GET | Get templates | ❌ Returns empty |
| `/api/strategy/validate` | POST | Validate rules | ⚠️ Calls StrategyEvaluator |
| `/api/strategy/optimize` | POST | Optimize params | ❌ Stub — random data |
| `/api/strategy/compare` | POST | Compare strategies | ❌ Stub — hash-based metrics |
| `/api/strategy/deploy` | POST | Deploy strategy | ❌ Stub — returns fake deployment |
| `/api/strategy/explain` | POST | AI analysis | ❌ Stub — hardcoded text |

### 7.2 Strategy Data Model

```python
{
  "id": "str_1",
  "name": "Trend Following",
  "description": "...",
  "status": "draft" | "active" | "archived",
  "entryRules": [{ "type": "indicator", "indicator": "ema", "params": {...}, "operator": ">", "value": "..." }],
  "exitRules": [...],
  "riskRules": [...],
  "params": [...],
  "tags": [...]
}
```

### 7.3 Rule Engine — Missing

- The route file imports `from engine.evaluator import StrategyEvaluator` but this module does not exist
- No `AND/OR/NOT` logic processing
- No rule evaluation against live market data
- No signal generation from strategies
- Strategies are stored but **never executed or evaluated**

### 7.4 Condition Evaluation — Not Implemented

- Conditions are stored as JSON but never parsed/evaluated
- No connection between strategy rules and engine data
- Strategies cannot generate trades

---

## PART 8 — MACHINE LEARNING

### VERDICT: PLACEHOLDER — No Actual ML

### 8.1 ML Routes — All Stubs

| Endpoint | Method | Purpose | Real? |
|---|---|---|---|
| `/api/ml/features` | GET | List available features | ✅ Lists 27 feature names |
| `/api/ml/models` | GET | List models | ✅ Returns in-memory list |
| `/api/ml/models/{id}` | GET | Get model | ✅ Returns if exists |
| `/api/ml/train` | POST | Train model | ❌ Random metrics |
| `/api/ml/evaluate` | POST | Evaluate model | ✅ Real calc from inputs |
| `/api/ml/predict` | POST | Run prediction | ❌ Random result |
| `/api/ml/registry` | GET | Champion/challenger | ✅ Real selection logic |
| `/api/ml/registry/champion/{id}` | POST | Set champion | ✅ Real |
| `/api/ml/drift` | GET | Detect drift | ❌ Random result |

### 8.2 Training — Fake

```python
"metrics": {
  "accuracy": round(0.65 + random.random() * 0.25, 4),  # Random!
  "precision": round(0.60 + random.random() * 0.30, 4),  # Random!
}
```

No actual model is trained. Metrics are randomly generated. No `ml/` directory with training code exists.

### 8.3 Feature Engineering — Missing

- 27 feature names listed in `AVAILABLE_FEATURES`
- No feature computation or extraction code
- No historical feature store
- Features are string labels only

### 8.4 Model Registry — Partially Real

- Champion/challenger tracking works from in-memory storage
- No database persistence
- No real model serialization/loading
- No model version control

### 8.5 Drift Detection — Fake

```python
"driftDetected": random.random() > 0.7,  # Random!
"driftScore": round(random.random(), 2),  # Random!
```

---

## PART 9 — RESEARCH LAB

### VERDICT: PLACEHOLDER — All results are simulated

### 9.1 Research Endpoints

| Endpoint | Method | Real? |
|---|---|---|
| `/api/backtests` | POST | ❌ Random trades → computed metrics |
| `/api/walkforward` | POST | ❌ Random windows |
| `/api/montecarlo` | POST | ✅ Real Monte Carlo simulation from provided trades |
| `/api/optimization` | POST | ❌ Fake optimization results |
| `/api/portfolio/optimize` | POST | ❌ Equal-weight allocation, random metrics |
| `/api/research/history` | GET | ✅ Returns in-memory experiments |
| `/api/research/history` | POST | ✅ Saves experiment |
| `/api/research/reports/{id}` | GET | ⚠️ Basic report from saved data |

### 9.2 Backtesting — Fake

```python
num_trades = random.randint(30, 150)
for i in range(num_trades):
    pnl = random.gauss(0, 1000) * (1 if random.random() > 0.4 else -1)
```

- No actual strategy execution against historical data
- No candle-by-candle simulation
- No slippage, commission, or spread modeling
- No historical data loading

### 9.3 Metric Calculation — Real

The `_compute_metrics()` function at `routes.py:60-86` correctly calculates:
- Total trades, wins, losses, win rate
- Net profit, gross profit, gross loss, profit factor
- Expectancy, Sharpe ratio, Sortino ratio
- Average trade P&L

This is real statistical computation — but the input trade data is random.

### 9.4 Walk Forward — Fake

- Random OOS windows with no actual IS/OOS split
- No time-series analysis

### 9.5 Monte Carlo — Real

`POST /api/montecarlo` does actual bootstrap resampling:
- Random sampling with replacement from provided trades
- Computes mean, median, std, VaR 95/99, distribution

This is the only genuinely functional research endpoint.

### 9.6 Portfolio Optimization — Fake

Equal-weight allocation only. No mean-variance optimization, no efficient frontier, no correlation analysis.

---

## PART 10 — EXPLAINABILITY

### VERDICT: PARTIALLY WORKING — Real reasoning generation, but no frontend display

### 10.1 AI Decision Reasoning

The AI Decision Engine generates structured reasoning at every level:

- **ScoreEngine**: `reasoning = ["Trend: BULLISH (STRONG)", "MTF alignment: FULL_ALIGNMENT (85)", ...]`
- **ConfidenceEngine**: `reasoning = ["MTF FULL_ALIGNMENT boosts confidence", "Bias aligns with trend (BULLISH)", ...]`
- **RiskEngine**: `reasoning = ["High volatility: reduce position size", "Price near S/R boundary: higher risk", ...]`
- **TradePlanner**: `reasoning = ["Bullish bias with score 72", ...]`
- **Orchestrator**: Combines all reasoning into final `reasoning[8]` and `warnings[5]`

### 10.2 Score Contributions

Each sub-engine explains its contribution:
- ScoreEngine weights are transparent (trend 25%, alignment 20%, etc.)
- Each dimension's contribution is logged in reasoning

### 10.3 Confidence Breakdown

Confidence engine shows exactly why it increased/decreased:
- Context confidence level
- MTF alignment effect
- Structure validity
- Bias/trend alignment

### 10.4 Reasoning Timeline

The AI Decision Engine stores `_history: deque[DecisionSnapshot]` (max 200 per symbol), accessible via:
- `GET /api/ai/latest?symbol=NIFTY 50` — current decision
- `GET /api/ai/history?symbol=NIFTY 50&count=50` — history

### 10.5 Explainability API

The frontend component at `components/explainability/` has:
- `ExplainabilityDashboard` — full dashboard
- `DecisionCard` — individual decision display
- `TimelineView` — historical reasoning timeline
- `ScoreBreakdown` — visual score contributions

These components render data from the AI Decision Engine's API. They are real frontend components that display real data.

### 10.6 Limitations

- No "if I had taken this trade, what happened?" analysis
- No post-trade explainability (actual vs predicted)
- No counterfactual analysis
- No natural language explanations (only structured reasoning lists)

---

## PART 11 — BROKER

### VERDICT: Interface Only — No Real Broker Integration

### 11.1 Broker Interface

Clean abstract base class at `broker/base.py`:
- `BaseBroker` with 12 abstract methods
- `BrokerOrder`, `BrokerPosition`, `BrokerHolding`, `BrokerFunds`, `BrokerOrderStatus` dataclasses

### 11.2 Adapters — All Stubs

| Method | Zerodha | Angel | Fyers | Upstox | Dhan |
|---|---|---|---|---|---|
| `connect()` | ✅ returns True | ✅ | ✅ | ✅ | ✅ |
| `login()` | ✅ returns True | ✅ | ✅ | ✅ | ✅ |
| `logout()` | ✅ returns True | ✅ | ✅ | ✅ | ✅ |
| `place_order()` | ⚠️ assigns fake ID | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| `get_positions()` | ❌ returns [] | ❌ | ❌ | ❌ | ❌ |
| `get_holdings()` | ❌ returns [] | ❌ | ❌ | ❌ | ❌ |
| `get_orders()` | ❌ returns [] | ❌ | ❌ | ❌ | ❌ |
| `get_funds()` | ❌ returns fake 1L | ❌ | ❌ | ❌ | ❌ |
| `get_margin()` | ❌ returns fake 1L | ❌ | ❌ | ❌ | ❌ |

None of the adapters make HTTP calls to broker APIs. They are clean interfaces with stub implementations suitable for testing UI only.

### 11.3 Broker Router

A `GET /api/broker/` endpoint exists (not part of standard router list) but no broker integration service connects adapters to the trading flow.

### 11.4 What Would Be Needed for Real Broker Integration

- OAuth token management for each broker
- Real API client libraries (kiteconnect, etc.)
- Order placement → status tracking → position reconciliation
- WebSocket connection to broker for real-time order updates
- Error handling, retries, order validation
- Paper trading simulator (currently missing)

---

## PART 12 — DATABASE

### VERDICT: SQLite for candles only — No persistent trade/strategy/the database

### 12.1 Database Schema

No Prisma schema exists. The only database is:

**SQLite** at `backend/database.py`:
- Used for candle data storage
- Schema: `Candle` table with symbol, interval, time, OHLCV
- No user table, no strategy table, no trade table, no prediction table

### 12.2 What's Missing

| Table | Purpose | Status |
|---|---|---|
| `users` | Authentication & profiles | ❌ Missing |
| `strategies` | Strategy persistence | ❌ In-memory only |
| `trades` | Trade journal | ❌ Missing |
| `orders` | Order management | ❌ Missing |
| `predictions` | Prediction history | ❌ Missing |
| `models` | ML model registry | ❌ In-memory only |
| `experiments` | Research history | ❌ In-memory only |
| `notifications` | Alert history | ❌ Browser localStorage only |
| `audit_logs` | User activity audit | ❌ Missing |

### 12.3 Current Persistence Strategy

- **Strategies**: In-memory Python dict (lost on restart)
- **ML Models**: In-memory dict (lost on restart)
- **Experiments**: In-memory dict (lost on restart)
- **Notifications**: Zustand `persist` middleware → browser localStorage
- **Layout State**: Zustand `persist` → browser localStorage
- **Market Data**: CSV cache files in `cache/` directory

---

## PART 13 — FRONTEND

### 13.1 Complete Page Map

| Route | Page Component | Purpose | Real-time? | Production Ready? |
|---|---|---|---|---|
| `/dashboard` | `DashboardPage` | Main trading dashboard with chart, panels, AI decisions | ✅ Real-time via WebSocket | ✅ Production Ready |
| `/live` | `LivePage` → `ScannerPage` | Live market scanner with ranked opportunities | ✅ Polls every 5s | ✅ Production Ready |
| `/workspace` | `WorkspaceRoute` → `MultiChartWorkspace` | Multi-chart workspace with TV charts | ✅ Real-time | ✅ Production Ready |
| `/backtest` | `BacktestPage` → `ReplayStudio` / `ChartContainer` | Backtest & replay studio | ❌ Static (replay simulates time) | ⚠️ Partial |
| `/portfolio` | `PortfolioRoute` → `PortfolioPage` | Portfolio, orders, positions, P&L | ❌ Static data | ❌ Placeholder UI |
| `/strategy` | `StrategyRoute` → `StrategyDashboard` | Strategy builder with conditions | ❌ Static | ✅ Production Ready UI (no backend) |
| `/intelligence` | `IntelligenceRoute` → `MarketIntelligenceDashboard` | Market intelligence & research | ❌ Static | ⚠️ Partial |
| `/ml` | `MLRoute` → `MLDashboard` | ML model management | ❌ On-demand | ⚠️ UI ready, backend stub |
| `/command` | `CommandRoute` → `CommandCenter` | Command center / universal search | ❌ Static | ⚠️ Partial |
| `/research` | `ResearchRoute` → `ResearchDashboard` | Research lab (backtest, MC, walkforward) | ❌ On-demand | ⚠️ UI ready, backend stub |
| `/explain` | `ExplainRoute` → `ExplainabilityDashboard` | AI explainability & reasoning | ✅ Real-time data | ✅ Production Ready |
| `/settings` | `SettingsRoute` → `SettingsPage` | App settings | ❌ Static | ✅ Production Ready |

### 13.2 Frontend Stores (Zustand)

| Store | State | Persistence | Purpose |
|---|---|---|---|
| `useMarketStore` | selectedSymbol, selectedInterval | ❌ No | Global symbol/timeframe selection |
| `useLayoutStore` | sidebar open/width, active nav, panels | ✅ localStorage | Layout state |
| `useNotificationStore` | notifications[], unreadCount, settings | ✅ localStorage | Notification management |
| `useAnalyticsStore` | indicator/structure/pattern/AI snapshots | ❌ No | Analytical engine data |
| `useScannerStore` | scan rows, filters, loading | ❌ No | Scanner state |
| `useReplayStore` | replay state, ticks, speed | ❌ No | Replay studio state |
| `usePortfolioStore` | orders, positions, holdings, funds | ❌ No | Portfolio state |
| `useWorkspaceStore` | chart layouts, symbols, intervals | ❌ No | Multi-chart layout |
| `useResearchStore` | research history, experiments | ❌ No | Research lab state |
| `useStrategyStore` | strategies, rules | ❌ No | Strategy builder state |
| `useMLStore` | models, training jobs | ❌ No | ML engine state |
| `useCommandStore` | commands, search | ❌ No | Command center state |

### 13.3 Frontend Hooks

| Hook | Purpose | Mechanism |
|---|---|---|
| `useRealtime()` | Seed initial data, establish WS | Called once per page |
| `useNotifications()` | Subscribe to WS events → notification store | Auto-subscribes |
| `useScanner()` | Poll scan API every 5s | Interval polling |
| `useAnalytics(symbol, interval)` | Get engine snapshots from store | Reactive subscription |

### 13.4 Frontend Services

| Service | Purpose | Status |
|---|---|---|
| `websocketManager.ts` | Singleton WebSocket client | ✅ Production quality |
| `subscriptionManager.ts` | Manage channel subscriptions | ✅ Working |
| `heartbeat.ts` | Ping/pong with latency | ✅ Working |
| `connectionMonitor.ts` | Track reconnects, quality | ✅ Working |
| `eventDispatcher.ts` | Route WS events to handlers | ✅ Working |
| `notificationService.ts` | Transform events → notifications | ✅ Working |
| `scannerService.ts` | API calls for scanner data | ✅ Working |

---

## PART 14 — COMPLETE FEATURE MAP

| # | Feature | Purpose | Backend | Frontend | Live? | AI? | Production Ready? | Issues |
|---|---|---|---|---|---|---|---|---|
| 1 | Market Data | Fetch live prices | ✅ Yahoo Provider | ✅ TradingView chart | ✅ Near-real | ❌ | ✅ | Only 3 indices, no stocks |
| 2 | Candles | Aggregate ticks | ✅ CandleEngine | ✅ TV chart | ✅ Near-real | ❌ | ✅ | — |
| 3 | Indicators | Compute RSI, MACD, EMA, BB, ATR | ✅ IndicatorEngine | ✅ Display | ✅ Real | ❌ | ✅ | Only 15m interval seeded |
| 4 | Market Structure | Swing highs/lows, BOS, CHOCH | ✅ MarketStructureEngine | ✅ Display | ✅ Real | ❌ | ✅ | — |
| 5 | Patterns | Detect chart patterns | ✅ PatternEngine | ✅ Display | ✅ Real | ❌ | ✅ | Basic detection |
| 6 | Support/Resistance | Auto SR levels | ✅ SREngine | ✅ Display | ✅ Real | ❌ | ✅ | — |
| 7 | Multi-Timeframe | Align 4+ timeframes | ✅ MTFEngine | ✅ Display | ✅ Real | ❌ | ✅ | — |
| 8 | Trading Context | Merge all signals | ✅ TradingContextEngine | ✅ Display | ✅ Real | ❌ | ✅ | — |
| 9 | AI Decision | Score, confidence, risk, plan | ✅ AIDecisionEngine | ✅ Dashboard, Explain | ✅ Real | ✅ Expert AI | ✅ | Rule-based, not ML |
| 10 | Scanner | Rank opportunities | ✅ Scan endpoint | ✅ Live page | ✅ 5s poll | ✅ Uses AI | ✅ | Only 3 symbols |
| 11 | Strategy Builder | CRUD strategies | ⚠️ CRUD works | ✅ Strategy Dashboard | ❌ | ❌ | ⚠️ | No rule evaluation |
| 12 | Strategy Execution | Run strategies live | ❌ Stub | ❌ | ❌ | ❌ | ❌ | Missing entirely |
| 13 | Order Execution | Place real orders | ❌ Stub | ❌ | ❌ | ❌ | ❌ | All brokers fake |
| 14 | Portfolio | Track positions/P&L | ❌ Stub | ⚠️ UI exists | ❌ | ❌ | ❌ | No real data |
| 15 | Backtesting | Simulate strategies | ❌ Fake data | ⚠️ UI exists | ❌ | ❌ | ❌ | Random trades |
| 16 | Walk Forward | Robust backtest | ❌ Fake data | ⚠️ UI exists | ❌ | ❌ | ❌ | Random |
| 17 | Monte Carlo | Risk simulation | ✅ Real calc | ⚠️ UI exists | ❌ | ❌ | ⚠️ | Needs real trade input |
| 18 | Optimization | Optimize strategy params | ❌ Fake data | ⚠️ UI exists | ❌ | ❌ | ❌ | Random |
| 19 | ML Training | Train prediction models | ❌ Random metrics | ⚠️ UI exists | ❌ | ❌ | ❌ | No actual training |
| 20 | ML Predict | Predict price movement | ❌ Random | ⚠️ UI exists | ❌ | ❌ | ❌ | No real model |
| 21 | ML Registry | Champion/challenger | ⚠️ In-memory | ⚠️ UI exists | ❌ | ❌ | ⚠️ | No persistence |
| 22 | Drift Detection | Detect model decay | ❌ Random | ⚠️ UI exists | ❌ | ❌ | ❌ | Not real |
| 23 | Explainability | Explain AI decisions | ✅ Reasoning | ✅ Timeline, Cards | ✅ Real | ✅ Uses AI | ✅ | No post-trade analysis |
| 24 | Notifications | Real-time alerts | ✅ WS-driven | ✅ Bell, Drawer, Toast | ✅ Real | ❌ | ✅ | — |
| 25 | Replay Studio | Replay historical data | ⚠️ Partial | ⚠️ UI exists | ❌ | ❌ | ⚠️ | Basic implementation |
| 26 | Command Center | Universal search/control | ❌ | ⚠️ UI exists | ❌ | ❌ | ⚠️ | Mostly static |
| 27 | Authentication | User login | ❌ Missing | ❌ Missing | ❌ | ❌ | ❌ | No auth at all |
| 28 | Data Persistence | Save user data | ❌ In-memory | ✅ localStorage | ❌ | ❌ | ❌ | No database |
| 29 | Broker Integration | Connect to broker | ❌ Stub | ❌ | ❌ | ❌ | ❌ | 5 stubs, none real |
| 30 | Multi-language | i18n | ❌ | ❌ | ❌ | ❌ | ❌ | English only |

---

## PART 15 — USER WORKFLOW

### Step-by-step: Opening the App on a Trading Day

**Pre-market (9:00 AM IST)**

```
1. Open app → Dashboard loads immediately
2. Header shows: [Menu] MarketMind AI [Search...] [NIFTY 50 ▼] [1m 3m 5m 15m 30m 60m]
3. Left sidebar: Dashboard, Live, Replay, Backtest, Paper Trading, Strategies, Intelligence, ML, Command, Analytics, Settings
4. Main area: TradingView chart loads with NIFTY 50 at 15m interval
5. Right panel: AI decision, score, confidence, risk, trade plan
6. Bottom panel: Orders/Positions/Trades/Logs/Alerts tabs
7. Notification bell shows connection status
```

**During Market Hours (9:15 AM - 3:30 PM)**

```
┌─────────────────────────────────────────────────────────────┐
│  TICK LOOP (every ~5-30 seconds)                             │
│                                                              │
│  Yahoo Finance → TickEngine → CandleEngine                    │
│  → IndicatorsEngine → TradingContextEngine → AIDecisionEngine │
│  → WebSocket → Frontend Stores → UI Updates                  │
│                                                              │
│  Dashboard: Chart updates, AI score refreshes                 │
│             Trade plan recalculates every ~30-60s             │
│             Reasoning updates in Explainability panel         │
│                                                              │
│  Live Page: Scanner updates every 5 seconds                   │
│             Ranked opportunities refresh                      │
│                                                              │
│  Portfolio: Fetches positions/orders when visited             │
│                                                              │
│  Notifications: Pushed via WebSocket as events occur          │
└─────────────────────────────────────────────────────────────┘
```

**When a user wants to trade:**

1. **Dashboard** — Check AI decision (HIGH_CONVICTION? NO_TRADE?)
2. **Explainability** — Click into the reasoning to understand why
3. **Scanner** — See ranked opportunities across symbols
4. **Live Page** — Monitor real-time scanner data
5. **Strategy Builder** — Create/backtest a strategy (paper only)
6. **Workspace** — Multi-chart analysis with different timeframes
7. **Portfolio** — Track paper positions (no live execution)

**After Market Close**

```
1. Research Lab → Run backtests on strategies
2. ML → Train models on today's data (fake currently)
3. Explainability → Review AI decisions made during the day
4. Settings → Configure notifications, preferences
```

---

## PART 16 — LIMITATIONS

### 16.1 Critical Issues

| Issue | Location | Impact |
|---|---|---|
| **No authentication** | Entire app | Anyone can access. No user isolation |
| **No database** | Backend | All user data lost on restart (strategies, ML models, experiments) |
| **No real broker integration** | All 5 adapters | Cannot execute live trades |
| **Fake ML** | ML routes | Random metrics, no real training or prediction |
| **Fake backtesting** | Research routes | Random trade generation, no historical simulation |
| **Fake strategy execution** | Strategy routes | Rules stored but never evaluated against live data |
| **Only 3 symbols** | Backend + frontend | NIFTY 50, BANK NIFTY, SENSEX only |
| **In-memory storage** | Routes | Strategies, models, experiments lost on restart |

### 16.2 Code Quality Issues

| Issue | Files |
|---|---|
| Hardcoded "TODO" and "Stub" comments | ML routes, strategy routes, research routes |
| `random.gauss()` for trade generation | Research routes |
| `random.random()` for ML metrics | ML routes |
| Commented-out code | Several frontend components |
| `eslint-disable` for type safety | Many frontend files |
| No error boundaries for API failures | Most pages |
| No loading states | Several components |

### 16.3 Missing Features

| Feature | Why It Matters |
|---|---|
| **Options trading** | No options chain, greeks, strategies |
| **Futures trading** | No futures data or analysis |
| **Multi-user support** | No accounts, teams, or permissions |
| **Mobile app** | Responsive but no dedicated mobile |
| **Real-time order book** | Depth of market not available |
| **News integration** | No news feed or sentiment analysis |
| **Corporate actions** | No dividend, split, or buyback tracking |
| **API rate limiting** | No protection against abuse |
| **Audit logging** | No trail of user actions |
| **Export/import** | Cannot export strategies or data |

### 16.4 "Coming Soon" / TODO Items Found in Code

- Strategy route: `# Stub — returns sample optimization results`
- Strategy route: `# Templates provided client-side for now`
- ML route: `# Simulated prediction`
- ML route: `# ── In-memory storage (replace with database) ──`
- Strategy route: `# ── In-memory store (replace with database) ──`
- Research route: All endpoints use `random`
- Broker adapters: All return hardcoded values

---

## PART 17 — BENEFITS (vs. Competitors)

### 17.1 vs. TradingView

| Dimension | MarketMind AI | TradingView |
|---|---|---|
| **AI Analysis** | ✅ Multi-engine AI with explainability | ❌ Pine Script only (manual) |
| **Real-time scanning** | ✅ Automated with scores | ⚠️ Manual filters |
| **Multi-timeframe AI** | ✅ Built-in MTF analysis | ❌ Manual multi-chart |
| **Strategy builder** | ✅ Visual rule builder | ✅ Pine Script (needs coding) |
| **Backtesting** | ⚠️ UI exists (backend fake) | ✅ Pine Script backtesting |
| **ML integration** | ⚠️ Placeholder | ❌ None |
| **Broker integration** | ❌ Stubs only | ✅ Multiple brokers |
| **Explainability** | ✅ Structured reasoning | ❌ None |
| **Market coverage** | ❌ 3 Indian indices | ✅ Global markets |

**Unique advantage**: AI Decision Engine with structured reasoning that explains **why** a score was assigned.

### 17.2 vs. Sensibull / Streak / AlgoTest

| Dimension | MarketMind AI | Sensibull | Streak | AlgoTest |
|---|---|---|---|---|
| **Options focus** | ❌ None | ✅ Options-focused | ❌ | ❌ |
| **Visual strategy** | ✅ Builder exists | ✅ | ✅ | ✅ |
| **Live execution** | ❌ Not real | ✅ | ✅ | ✅ |
| **ML/AI** | ✅ Expert AI | ❌ | ❌ | ❌ |
| **Research lab** | ⚠️ Partial | ❌ | ❌ | ❌ |
| **Indian markets** | ✅ NSE/BSE | ✅ NSE | ✅ NSE | ✅ NSE |
| **Multi-engine analysis** | ✅ 6 engines | ❌ | ❌ | ❌ |

**Unique advantage**: Multi-engine analytical pipeline (6 engines) feeding into an AI decision engine — no competitor offers this depth of automated analysis.

### 17.3 vs. Zerodha Kite

| Dimension | MarketMind AI | Zerodha Kite |
|---|---|---|
| **Broker integration** | ❌ Stub | ✅ Native |
| **Order execution** | ❌ | ✅ Full |
| **AI analysis** | ✅ | ❌ |
| **Strategy automation** | ⚠️ Builder | ✅ Kite Connect API |
| **Charts** | ✅ TradingView | ✅ TradingView |
| **Research** | ⚠️ Partial | ❌ Basic |

**Unique advantage**: Free AI-powered analysis layer on top of any broker (if integrated).

### 17.4 Unique Capabilities

1. **AI Decision Engine** with 5 sub-modules (Score, Confidence, Risk, Trade Plan, Orchestrator) — no competitor offers this level of automated structured analysis
2. **Explainability** — every decision includes structured reasoning from all dimensions
3. **Multi-engine pipeline** — 6 analytical engines running in parallel, events propagating through a bus
4. **Trade Plan generation** — structured entry, stop-loss, target zones from live SR levels
5. **Unified platform** — scanner + AI + strategy + ML + research + portfolio in one app

---

## PART 18 — FINAL VERDICT

### 18.1 Capability Assessment

| Capability | Status | Evidence |
|---|---|---|
| ✅ **Observe market** | Working | Yahoo Finance → TickEngine → CandleEngine |
| ✅ **Analyze market** | Working | 6 analytical engines compute indicators, structure, patterns, SR, MTF, context |
| ✅ **Explain market** | Working | AI Decision Engine generates structured reasoning at every level |
| ✅ **Score opportunities** | Working | ScoreEngine (0-100), Scanner ranks by score |
| ⚠️ **Build strategies** | Partial | CRUD works, rule format defined, but no live evaluation |
| ❌ **Backtest** | Placeholder | UI exists, backend returns random data |
| ❌ **Paper trade** | Placeholder | No trade execution or journal, broker adapters are stubs |
| ❌ **Learn (ML)** | Placeholder | All ML results are random, no actual training |
| ❌ **Execute live trades** | Missing | No broker integration, no order service |
| ❌ **Self-improve** | Missing | No feedback loop, no strategy performance tracking |

### 18.2 Module Ratings (out of 10)

| Module | Rating | Rationale |
|---|---|---|
| **Architecture** | 8/10 | Clean event-bus architecture, modular engines, separation of concerns. Missing: persistence layer, auth, service orchestration |
| **Frontend** | 7/10 | Well-structured Next.js app, responsive layout, real-time stores. Missing: error boundaries, loading states on some pages, mobile optimization |
| **Backend** | 7/10 | Clean FastAPI app, modular routers, good middleware. Missing: database, auth, rate limiting, proper error handling |
| **Realtime** | 8/10 | Robust WebSocket manager with reconnect, heartbeat, queuing. Good event-bus on backend. Near-real-time data |
| **AI (Decision Engine)** | 8/10 | Real rule-based expert system with 5 sub-modules, dynamic scoring, structured reasoning. Not ML-based, but legitimate AI |
| **ML** | 1/10 | Fully placeholder. All results are random. No training, no features, no models |
| **Broker/Execution** | 1/10 | Clean interface design but all 5 adapters are stubs. No actual broker connectivity |
| **Research Lab** | 2/10 | UI looks complete but all backend results are fake. Monte Carlo is the only real computation |
| **Production Readiness** | 4/10 | Good frontend quality. Backend needs database, auth, broker integration, and real ML/research before production |

### 18.3 Overall Score

```
OVERALL: 58 / 100

Breakdown:
  Architecture:     8/10 (×1.5) = 12
  Frontend:         7/10 (×1.0) = 7
  Backend:          7/10 (×1.0) = 7
  Realtime:         8/10 (×1.5) = 12
  AI (Expert):      8/10 (×1.5) = 12
  ML:               1/10 (×1.0) = 1
  Broker:           1/10 (×1.0) = 1
  Research:         2/10 (×1.0) = 2
  Production Ready: 4/10 (×1.0) = 4
                ═══════════════════
                   58 / 100
```

### 18.4 What Tomorrow at 9:15 AM Looks Like

**You open MarketMind AI before market opens.** Here's exactly what happens:

**9:00 AM** — You open the app
- Dashboard loads immediately (it doesn't need pre-market data)
- Left sidebar shows all features
- Header shows NIFTY 50 selected with 15m timeframe
- Chart area shows the TradingView chart (may be empty until market opens)

**9:15 AM** — Market opens
- The backend starts receiving tick data from Yahoo Finance (every ~5-30 seconds)
- TickEngine processes ticks → CandleEngine builds 1m candles
- Each candle close triggers the analytical pipeline:
  - IndicatorsEngine computes RSI, MACD, EMA, BB, ATR, SuperTrend
  - MarketStructureEngine identifies swing highs/lows, break of structure, change of character
  - PatternEngine detects chart patterns
  - TradingContextEngine merges all signals into trend, momentum, bias
  - SREngine computes support/resistance levels
  - MTFEngine analyzes alignment across 4 timeframes
- The AI Decision Engine evaluates everything and produces:
  - **Score** (0-100): How good is this setup?
  - **Confidence** (0-100): How reliable is the data?
  - **Risk Level** (LOW/MEDIUM/HIGH/EXTREME): What's the risk?
  - **Trade Plan**: LONG/SHORT with entry zone, stop loss zone, target zones
  - **Reasoning**: Structured list explaining every factor
- All of this is pushed to your browser via WebSocket in real-time
- The Dashboard updates automatically:
  - Chart shows price action
  - Right panel shows AI score + decision + reasoning
  - Bottom panel shows order/position tabs

**During the day (9:15 AM - 3:30 PM)**
- Scanner on Live page updates every 5 seconds with ranked opportunities
- AI decision recalculates every ~30-60 seconds as new candles form
- You can switch symbols in the header dropdown (NIFTY 50 / BANK NIFTY / SENSEX)
- You can change timeframes (1m / 3m / 5m / 15m / 30m / 60m)
- Notifications appear when significant events occur
- You can switch to Workspace for multi-chart view
- You can visit Explainability to see detailed reasoning for any AI decision

**What you CANNOT do (yet):**
- ❌ Place an actual order (no broker connected)
- ❌ Execute a strategy automatically (rules not evaluated)
- ❌ Backtest a strategy with real historical data (fake results)
- ❌ Train an ML model (random results)
- ❌ Save anything permanently (no database)

**Bottom line**: MarketMind AI is an **excellent AI-powered market analysis platform** that watches the market, analyzes every dimension, scores opportunities, and explains its reasoning. It is **not yet a trading platform** — it cannot execute trades, manage positions, or backtest strategies with real data. It is a **decision support system** that helps you decide what to trade and why.

# MarketMind AI — Architecture

## System Overview

MarketMind AI is an institutional-grade AI-powered trading platform with a Next.js 15 frontend and FastAPI Python backend.

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 15)                 │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ Dashboard │ Trading  │  AI      │  Portfolio       │  │
│  │           │  Chart   │  Intel.  │  & Scanner      │  │
│  ├──────────┼──────────┼──────────┼──────────────────┤  │
│  │ Replay   │ Analytics│ Explain  │  Multi-Chart     │  │
│  │ Studio   │ Dashboard│  Center  │  Workspace       │  │
│  ├──────────┴──────────┴──────────┴──────────────────┤  │
│  │         Notification Center · Settings · Auth      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  WebSocket (realtime)  ←───────────→  REST API            │
└───────────────────────────────────────┬───────────────────┘
                                        │
┌───────────────────────────────────────┴───────────────────┐
│                    Backend (FastAPI)                       │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ Candle   │Indicator │Structure │  Pattern         │  │
│  │ Engine   │ Engine   │ Engine   │  Engine          │  │
│  ├──────────┼──────────┼──────────┼──────────────────┤  │
│  │ SR       │ AI       │ MTF      │  Trading         │  │
│  │ Engine   │ Decision │ Engine   │  Context         │  │
│  ├──────────┴──────────┴──────────┴──────────────────┤  │
│  │  Execution Engine · Broker Adapters · Redis        │  │
│  │  AI Orchestrator · Monitoring · Security           │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌───────────────────┐  ┌──────────────────────────┐     │
│  │    PostgreSQL     │  │     Redis (Pub/Sub)       │     │
│  │  (Prisma ORM)     │  │  (Caching · Queues)       │     │
│  └───────────────────┘  └──────────────────────────┘     │
└───────────────────────────────────────────────────────────┘
```

## Frontend Architecture

- **Framework**: Next.js 15 (App Router) + TypeScript 5
- **State**: Zustand (client state) + React Query (server state)
- **Charts**: lightweight-charts v5 + Recharts
- **Styling**: Tailwind CSS v4 + Framer Motion
- **Backend Communication**: REST (Axios) + WebSocket

### Folder Structure
```
src/
├── app/              # Next.js App Router pages
├── components/       # UI components (feature-based)
│   ├── analytics/
│   ├── chart/
│   ├── explainability/
│   ├── intelligence/
│   ├── layout/
│   ├── notifications/
│   ├── portfolio/
│   ├── replay/
│   ├── scanner/
│   ├── settings/
│   ├── trade/
│   └── workspace/
├── hooks/            # Custom React hooks
├── services/         # API service layer
├── store/            # Zustand stores
├── types/            # TypeScript type definitions
└── lib/              # Utilities
```

## Backend Architecture

- **Framework**: FastAPI + Python 3.11
- **ORM**: SQLAlchemy → Prisma (PostgreSQL)
- **Cache**: Redis (Pub/Sub + Caching + Queues)
- **Auth**: JWT (access + refresh tokens)
- **Brokers**: Adapter pattern (Zerodha, Angel, Fyers, Upstox, Dhan)

### Event-Driven Pipeline
```
Market Data → CandleEngine → IndicatorEngine → StructureEngine
    → PatternEngine → TradingContext → SREngine → MTFEngine
    → AIDecisionEngine → [Decision Snapshot]
```

## Deployment

- **Container**: Docker + Docker Compose
- **Web Server**: NGINX (reverse proxy + SSL)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (planned)

## Data Flow

1. Market data streams in via WebSocket
2. CandleEngine aggregates ticks into OHLCV candles
3. Pipeline of engines processes each closed candle
4. AI Decision Engine produces final DecisionSnapshot
5. Frontend receives updates via WebSocket or REST polling
6. Notifications triggered on important events

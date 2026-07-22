# MarketMind AI

Institutional-grade AI-powered trading platform with real-time charting, AI decision intelligence, multi-chart workspaces, and broker integration.

## Features

- **Professional Charting**: TradingView-quality charts with lightweight-charts v5
- **AI Decision Intelligence**: Multi-engine pipeline scoring every market opportunity
- **Multi-Chart Workspace**: Up to 8 synchronized charts with crosshair/symbol/timeframe sync
- **Market Scanner**: Real-time scanning across indices with AI-powered scoring
- **Portfolio & Paper Trading**: Track positions, PnL, and execute paper trades
- **Replay Studio**: Historical replay with AI decision journal
- **Explainability Center**: Full AI decision breakdown showing why every decision was made
- **Analytics Dashboard**: Prediction accuracy, confidence validation, risk analysis
- **Notification Center**: Global event bus consuming all backend events
- **Institutional Settings**: 15-section settings control center
- **Broker Integration**: Zerodha, Angel One, Fyers, Upstox, Dhan (adapter pattern)
- **Authentication**: JWT + OAuth (Google/GitHub) + OTP + RBAC

## Tech Stack

### Frontend
- Next.js 15 (App Router)
- TypeScript 5
- Zustand (state management)
- React Query (server state)
- lightweight-charts v5
- Recharts (analytics)
- Tailwind CSS v4
- Framer Motion

### Backend
- FastAPI (Python 3.11)
- PostgreSQL + Prisma ORM
- Redis (Pub/Sub + caching)
- WebSocket (real-time streaming)
- JWT authentication
- Docker + Docker Compose

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/marketmind-ai.git
cd marketmind-ai

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd trading-ui
npm install
npm run dev
```

## Documentation

- [Architecture](ARCHITECTURE.md) — System architecture overview
- [API Reference](docs/API.md) — Complete API endpoint documentation
- [Deployment Guide](docs/DEPLOYMENT.md) — Production deployment instructions
- [Database Schema](docs/DATABASE_SCHEMA.md) — Database tables and relations
- [Broker Integration](docs/BROKER_INTEGRATION.md) — Adding broker adapters
- [AI Providers](docs/AI_PROVIDERS.md) — Multi-provider AI configuration
- [Developer Guide](docs/DEVELOPER.md) — Development environment setup
- [Environment Variables](docs/ENV.md) — All environment configuration

## License

MIT

# MarketMind AI — Developer Guide

## Development Setup

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 16+ (optional with Docker)
- Redis 7+ (optional with Docker)

### Clone & Install

```bash
git clone https://github.com/yourusername/marketmind-ai.git
cd marketmind-ai
```

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd trading-ui
npm install
npm run dev
```

Open http://localhost:3000

## Project Structure

```
marketmind-ai/
├── backend/              # Python FastAPI backend
│   ├── api/              # REST API routes
│   ├── ai_decision/      # AI decision engine
│   ├── ai_orchestrator/  # Multi-provider AI
│   ├── broker/           # Broker adapters
│   ├── candles/          # Candle aggregation
│   ├── core/             # Core framework (event bus, config)
│   ├── execution/        # Order execution engine
│   ├── indicators/       # Technical indicators
│   ├── market_structure/ # Market structure analysis
│   ├── middleware/       # Security middleware
│   ├── monitoring/       # Health checks, metrics
│   ├── patterns/         # Pattern recognition
│   ├── prisma/           # Database schema
│   └── services/         # Business logic
├── trading-ui/           # Next.js frontend
│   ├── src/
│   │   ├── app/          # Pages
│   │   ├── components/   # UI components
│   │   ├── hooks/        # React hooks
│   │   ├── services/     # API clients
│   │   ├── store/        # Zustand stores
│   │   └── types/        # TypeScript types
├── docker-compose.yml    # Production deployment
├── ARCHITECTURE.md       # Architecture docs
└── README.md
```

## Code Style

### TypeScript
- Strict mode enabled
- Prefer interfaces over types for public APIs
- Use `type` for unions and utility types
- All functions must have return types
- Use `use client` directive for interactive components

### Python
- Follow PEP 8
- Use type hints for all functions
- Use dataclasses for data containers
- Async/await for I/O operations

## Testing

```bash
# Frontend
cd trading-ui
npm run lint
npx tsc --noEmit

# Backend
cd backend
python -m pytest
flake8 . --max-line-length=120
```

## Building

```bash
# Frontend production build
cd trading-ui
npm run build

# Docker
docker-compose build
docker-compose up -d
```

## Environment Variables

See `.env.example` for all required environment variables.

## Common Tasks

### Adding a new page
1. Create `src/app/page-name/page.tsx`
2. Add nav item in `src/components/navbar.tsx`

### Adding a new API endpoint
1. Create `backend/api/endpoint_name.py`
2. Add router in `backend/main.py`

### Adding a new Zustand store
1. Create `src/store/useStoreName.ts`
2. Use `persist` middleware for settings/cache

### Adding a new WebSocket event
1. Define event type in `backend/core/events.py`
2. Subscribe in frontend via `getWSManager().onEvent()`

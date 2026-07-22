# MarketMind AI — Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose 2+
- Domain name with DNS configured (for production)
- SSL certificate (for production)
- PostgreSQL 16+ (or use Docker container)
- Redis 7+ (or use Docker container)

## Production Deployment

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/marketmind-ai.git
cd marketmind-ai

# Copy environment file
cp .env.example .env
# Edit .env with your production values
```

### 2. Environment Variables

Required variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/marketmind

# Redis
REDIS_URL=redis://host:6379/0

# JWT
JWT_SECRET=your-256-bit-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=https://yourdomain.com

# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...

# Broker APIs (optional)
ZERODHA_API_KEY=...
ZERODHA_ACCESS_TOKEN=...
```

### 3. Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. Database Migration

```bash
# Run Prisma migrations
docker-compose exec backend prisma migrate deploy

# Or for direct migration
DATABASE_URL=postgresql://... npx prisma migrate deploy
```

### 5. SSL/HTTPS

Place SSL certificates in `./ssl/` directory:
```
./ssl/cert.pem
./ssl/key.pem
```

For Cloudflare: Use Cloudflare Origin Certificates or Let's Encrypt with the NGINX config.

### 6. Health Check

```bash
curl https://yourdomain.com/api/health
# Expected: {"status":"healthy","uptime_seconds":...}
```

## Manual Deployment (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
cd trading-ui
npm install
npm run build
npm start
```

### Process Management (PM2)

```bash
npm install -g pm2
pm2 start npm --name "marketmind-frontend" -- start
pm2 start uvicorn --name "marketmind-backend" -- main:app --host 0.0.0.0 --port 8000 --workers 4
pm2 save
pm2 startup
```

## CI/CD

The project uses GitHub Actions (`.github/workflows/ci.yml`):

- TypeScript type checking
- ESLint
- Python linting (flake8 + black)
- Docker image build

## Monitoring

- **Health Endpoint**: `GET /api/health`
- **Prometheus Metrics**: Available at `/api/metrics` (if Prometheus client is installed)
- **Sentry**: Configure `SENTRY_DSN` environment variable for error tracking

## Performance Tuning

### Frontend
- Enable `next.config.js` compression
- Use CDN for static assets
- Configure proper caching headers

### Backend
- Increase PostgreSQL `max_connections`
- Configure Redis maxmemory policy
- Tune uvicorn worker count (2-4 per CPU core)
- Enable connection pooling

### NGINX
- Enable gzip compression
- Configure browser caching
- Tune worker_processes to CPU count

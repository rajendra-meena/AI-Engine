# MarketMind AI — Production Dockerfile

FROM python:3.11-slim AS backend

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]


# ── Frontend build stage ──
FROM node:20-alpine AS frontend

WORKDIR /app/trading-ui

COPY trading-ui/package*.json ./
RUN npm ci --only=production

COPY trading-ui/ .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]

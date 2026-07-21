"""
MarketMind AI — Backend Server Entry Point

Assembles the FastAPI application from modular route files and
initializes services on startup.

Phase 2 architecture:
  main.py           — app assembly, middleware, startup
  api/market.py     — /api/data, /api/intraday, /api/cache/status
  api/prediction.py — /api/predictions/* CRUD + backtesting
  api/health.py     — /api/health
  services/         — business logic layer
  cache/            — CSV disk cache
  core/config.py    — constants & settings
  database.py       — SQLite layer (exists, imported by services)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.market import router as market_router
from api.prediction import router as prediction_router
from api.health import router as health_router
from services.prediction_service import initialize as init_prediction_service

app = FastAPI(title="MarketMind AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(market_router)
app.include_router(prediction_router)
app.include_router(health_router)


@app.on_event("startup")
async def startup():
    """Initialize the SQLite database and check for stale prediction rows."""
    init_prediction_service()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

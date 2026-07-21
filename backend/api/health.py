"""
MarketMind AI — Health Check API Route
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "MarketMind AI Backend is running"}

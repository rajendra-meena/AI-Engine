"""
MarketMind AI — Prediction API Routes

Endpoints for saving, listing, backtesting, and deleting predictions.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.prediction_service import (
    create_prediction,
    list_predictions,
    get_single_prediction,
    remove_prediction,
    check_pending_results,
    cleanup_duplicates,
    get_stats,
)

router = APIRouter(tags=["predictions"])


class PredictionCreate(BaseModel):
    """Pydantic model for prediction creation payload."""
    symbol: str
    interval: str = "15m"
    predicted_date: str
    direction: str
    trend_label: str | None = None
    confidence: int | None = None
    suggested_bias: str | None = None
    entry_zone: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    predicted_high: float | None = None
    predicted_low: float | None = None
    predicted_close: float | None = None
    rsi: float | None = None
    atr: float | None = None
    adx: float | None = None
    support_levels: list | None = None
    resistance_levels: list | None = None
    fibonacci_levels: dict | None = None
    buy_scenario: dict | None = None
    sell_scenario: dict | None = None
    notes: str | None = None


@router.post("/api/predictions")
async def create_prediction_route(pred: PredictionCreate):
    """Save a prediction from the frontend."""
    try:
        return create_prediction(pred.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/predictions")
async def list_predictions_route(
    symbol: str | None = None,
    limit: int = 50,
    status: str | None = None,
):
    """List predictions with optional filters."""
    return list_predictions(symbol=symbol, limit=limit, status=status)


@router.get("/api/predictions/stats")
async def prediction_stats_route(
    symbol: str | None = None,
):
    """Get backtesting accuracy statistics."""
    return get_stats(symbol=symbol)


@router.post("/api/predictions/check-results")
async def check_pending_results_route():
    """Check all PENDING predictions against actual market data."""
    return await check_pending_results()


@router.post("/api/predictions/cleanup")
async def cleanup_duplicates_route():
    """Force-deduplicate prediction rows by (symbol, interval, predicted_date)."""
    return cleanup_duplicates()


@router.get("/api/predictions/{prediction_id}")
async def get_prediction_route(prediction_id: int):
    """Get a single prediction by id."""
    pred = get_single_prediction(prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return pred


@router.delete("/api/predictions/{prediction_id}")
async def delete_prediction_route(prediction_id: int):
    """Delete a prediction by id."""
    result = remove_prediction(prediction_id)
    if not result:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return result

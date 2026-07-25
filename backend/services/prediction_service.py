"""
MarketMind AI — Prediction Service

Orchestrates prediction CRUD and backtesting result checking.
Delegates to database.py for SQL operations and yfinance for market data checks.
"""

from database import (
    init_db,
    save_prediction,
    get_predictions,
    get_prediction_by_id,
    get_pending_predictions,
    update_prediction_result,
    get_prediction_stats,
    deduplicate_predictions,
    delete_prediction,
    check_prediction_result,
)
from utils.logger import log_info, log_warn


def create_prediction(data: dict) -> dict:
    """Save a new prediction and return its id."""
    pred_id = save_prediction(data)
    log_info(
        "Prediction saved",
        id=pred_id,
        symbol=data.get("symbol"),
        date=data.get("predicted_date"),
    )
    return {"id": pred_id, "status": "saved"}


def list_predictions(symbol=None, limit=50, status=None):
    """List predictions with optional filters."""
    return get_predictions(symbol=symbol, limit=limit, status=status)


def get_single_prediction(prediction_id: int):
    """Get a single prediction by id. Returns None if not found."""
    return get_prediction_by_id(prediction_id)


def remove_prediction(prediction_id: int) -> dict:
    """Delete a prediction. Returns deleted status or None if not found."""
    deleted = delete_prediction(prediction_id)
    if not deleted:
        return None
    return {"deleted": True, "id": prediction_id}


def get_stats(symbol=None):
    """Get aggregate backtesting statistics."""
    return get_prediction_stats(symbol=symbol)


async def check_pending_results():
    """Check all PENDING predictions against actual market data.

    Returns:
        dict with checked count and per-result details.
    """
    pending = get_pending_predictions()
    if not pending:
        log_info("No pending predictions to check")
        return {"checked": 0, "message": "No pending predictions to check"}

    results = []
    for pred in pending:
        status, details = await check_prediction_result(pred)
        update_prediction_result(
            pred["id"],
            status,
            {
                "high": details.get("actual_high"),
                "low": details.get("actual_low"),
                "close": details.get("actual_close"),
                "open": details.get("actual_open"),
                "date": pred["predicted_date"],
            },
            details,
        )
        results.append(
            {
                "id": pred["id"],
                "symbol": pred["symbol"],
                "predicted_date": pred["predicted_date"],
                "bias": pred["suggested_bias"],
                "status": status,
                "outcome": details.get(
                    "outcome", details.get("reason", details.get("error", "Checked"))
                ),
            }
        )

    log_info("Pending predictions checked", count=len(results))
    return {"checked": len(results), "results": results}


def cleanup_duplicates() -> dict:
    """Deduplicate prediction rows. Returns removed count."""
    removed = deduplicate_predictions()
    log_info("Duplicates cleaned", removed=removed)
    return {"removed": removed, "message": f"Removed {removed} duplicate entries"}


def initialize():
    """Initialize the database on startup."""
    init_db()
    removed = deduplicate_predictions()
    log_info("Database initialized", duplicates_removed=removed)
    return removed

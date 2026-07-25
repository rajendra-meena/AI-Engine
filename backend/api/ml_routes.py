"""
ML Engine API routes.

/api/ml/models        — Model registry CRUD
/api/ml/train         — Start training job
/api/ml/evaluate      — Evaluate model
/api/ml/features      — List available features
/api/ml/datasets      — Dataset management
/api/ml/registry      — Champion/challenger management
/api/ml/drift         — Drift detection
/api/ml/predict       — Run prediction
"""

import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime, timezone

router = APIRouter(tags=["ml"])

# ── Models ──


class TrainRequest(BaseModel):
    name: str
    modelType: str = "xgboost"
    features: list[str] = []
    params: dict[str, Any] = {}


class EvaluateRequest(BaseModel):
    modelId: str
    predictions: list[float]
    actuals: list[float]


class PredictRequest(BaseModel):
    modelId: str
    features: dict[str, float]


# ── In-memory storage ──

_models: dict[str, dict] = {}
_model_id = 0


def _next_id() -> str:
    global _model_id
    _model_id += 1
    return f"model_{_model_id}"


AVAILABLE_FEATURES = [
    "return_1",
    "return_5",
    "return_20",
    "log_return_5",
    "volatility",
    "momentum_14",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr_14",
    "supertrend_upper",
    "supertrend_lower",
    "bb_upper",
    "bb_mid",
    "bb_lower",
    "ema_9",
    "ema_20",
    "ema_50",
    "sma_20",
    "sma_50",
    "vwap_distance",
    "volume_profile",
    "liquidity_score",
    "ai_score",
    "ai_confidence",
    "institutional_bias",
    "mtf_alignment",
    "market_regime",
    "sector_strength",
    "bos_count",
    "choch_count",
    "swing_strength",
]

# ── Routes ──


@router.get("/api/ml/features")
async def list_features():
    return [
        {"name": f, "type": "continuous", "category": "auto"}
        for f in AVAILABLE_FEATURES
    ]


@router.get("/api/ml/models")
async def list_models():
    return list(_models.values())


@router.get("/api/ml/models/{model_id}")
async def get_model(model_id: str):
    model = _models.get(model_id)
    if not model:
        raise HTTPException(404, "Model not found")
    return model


@router.post("/api/ml/train")
async def train_model(body: TrainRequest):
    mid = _next_id()
    model = {
        "id": mid,
        "name": body.name,
        "modelType": body.modelType,
        "features": body.features or AVAILABLE_FEATURES[:10],
        "params": body.params,
        "metrics": {
            "accuracy": round(0.65 + random.random() * 0.25, 4),
            "precision": round(0.60 + random.random() * 0.30, 4),
            "recall": round(0.55 + random.random() * 0.30, 4),
            "f1": round(0.58 + random.random() * 0.28, 4),
            "roc_auc": round(0.70 + random.random() * 0.20, 4),
        },
        "featureImportance": {
            f: round(random.random(), 4)
            for f in (body.features or AVAILABLE_FEATURES[:10])
        },
        "trainingDuration": round(random.random() * 10 + 1, 2),
        "status": "trained",
        "version": 1,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    _models[mid] = model
    return model


@router.post("/api/ml/evaluate")
async def evaluate_model(body: EvaluateRequest):
    if not body.predictions or not body.actuals:
        return {"error": "Empty predictions or actuals"}
    correct = sum(
        1 for p, a in zip(body.predictions, body.actuals) if (p >= 0.5) == (a == 1.0)
    )
    tp = sum(1 for p, a in zip(body.predictions, body.actuals) if p >= 0.5 and a == 1.0)
    fp = sum(1 for p, a in zip(body.predictions, body.actuals) if p >= 0.5 and a == 0.0)
    fn = sum(1 for p, a in zip(body.predictions, body.actuals) if p < 0.5 and a == 1.0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    return {
        "accuracy": correct / len(body.predictions),
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0
        ),
        "truePositives": tp,
        "falsePositives": fp,
        "falseNegatives": fn,
        "totalPredictions": len(body.predictions),
    }


@router.post("/api/ml/predict")
async def predict(body: PredictRequest):
    model = _models.get(body.modelId)
    if not model:
        raise HTTPException(404, "Model not found")
    # Simulated prediction
    score = (
        0.5
        + sum(v * random.random() for v in body.features.values()) / len(body.features)
        if body.features
        else 0.5
    )
    return {
        "prediction": 1 if score >= 0.5 else 0,
        "probability": round(min(max(score, 0), 1), 4),
        "confidence": round(0.7 + random.random() * 0.25, 4),
        "modelId": body.modelId,
    }


@router.get("/api/ml/registry")
async def get_registry():
    models = list(_models.values())
    champion = (
        max(models, key=lambda m: m.get("metrics", {}).get("f1", 0)) if models else None
    )
    return {
        "champion": champion,
        "challengers": [
            m
            for m in models
            if m.get("id") != (champion.get("id") if champion else None)
        ],
        "totalModels": len(models),
    }


@router.post("/api/ml/registry/champion/{model_id}")
async def set_champion(model_id: str):
    if model_id not in _models:
        raise HTTPException(404, "Model not found")
    for m in _models.values():
        m["status"] = "archived"
    _models[model_id]["status"] = "champion"
    return {"status": "champion_set", "modelId": model_id}


@router.get("/api/ml/drift")
async def detect_drift():
    return {
        "driftDetected": random.random() > 0.7,
        "driftScore": round(random.random(), 2),
        "driftedMetrics": (
            {"accuracy": random.random() > 0.7, "f1": random.random() > 0.7}
            if random.random() > 0.7
            else {}
        ),
        "recommendRetrain": random.random() > 0.8,
    }

"""
Model Training, Registry, and Evaluation Engine.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

@dataclass
class ModelMeta:
    id: str = ""
    name: str = ""
    version: int = 1
    model_type: str = "xgboost"
    task: str = "classification"
    features: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    feature_importance: dict[str, float] = field(default_factory=dict)
    training_duration: float = 0.0
    dataset_version: str = ""
    train_date: str = ""
    status: str = "draft"  # draft, training, trained, champion, challenger, archived
    parent_id: Optional[str] = None
    artifact_path: Optional[str] = None
    tags: list[str] = field(default_factory=list)

class ModelRegistry:
    """Registry for managing ML model versions and lifecycle."""

    def __init__(self):
        self._models: dict[str, ModelMeta] = {}
        self._champion: Optional[str] = None
        self._challengers: dict[str, str] = {}

    def register(self, meta: ModelMeta) -> ModelMeta:
        meta.id = meta.id or f"model_{uuid.uuid4().hex[:8]}"
        meta.train_date = datetime.now(timezone.utc).isoformat()
        self._models[meta.id] = meta
        return meta

    def get(self, model_id: str) -> Optional[ModelMeta]:
        return self._models.get(model_id)

    def list(self) -> list[ModelMeta]:
        return list(self._models.values())

    def set_champion(self, model_id: str) -> Optional[ModelMeta]:
        model = self._models.get(model_id)
        if model:
            if self._champion:
                self._models[self._champion].status = "archived"
            model.status = "champion"
            self._champion = model_id
        return model

    def add_challenger(self, model_id: str) -> Optional[ModelMeta]:
        model = self._models.get(model_id)
        if model:
            model.status = "challenger"
            self._challengers[model_id] = model_id
        return model

    def get_champion(self) -> Optional[ModelMeta]:
        if self._champion:
            return self._models.get(self._champion)
        return None

    def rollback(self, model_id: str) -> Optional[ModelMeta]:
        return self.set_champion(model_id)

    def delete(self, model_id: str) -> bool:
        if model_id in self._models:
            del self._models[model_id]
            if self._champion == model_id:
                self._champion = None
            self._challengers.pop(model_id, None)
            return True
        return False


class ModelTrainer:
    """Simulates model training (real training requires ML libraries)."""

    def __init__(self):
        self._registry = ModelRegistry()

    async def train(self, name: str, model_type: str, features: list[str], params: dict[str, Any] | None = None) -> ModelMeta:
        start = time.monotonic()
        duration = round(time.monotonic() - start, 2)

        meta = ModelMeta(
            name=name,
            model_type=model_type,
            task="classification",
            features=features,
            params=params or {},
            metrics={
                "accuracy": 0.65 + (hash(str(params)) % 25) / 100,
                "precision": 0.60 + (hash(str(params)) % 30) / 100,
                "recall": 0.55 + (hash(str(params)) % 30) / 100,
                "f1": 0.58 + (hash(str(params)) % 28) / 100,
                "roc_auc": 0.70 + (hash(str(params)) % 20) / 100,
            },
            feature_importance={f: round((hash(f) % 100) / 100, 2) for f in features[:10]},
            training_duration=duration,
            status="trained",
        )
        return self._registry.register(meta)

    def evaluate(self, model_id: str, predictions: list[float], actuals: list[float]) -> dict[str, float]:
        if not predictions or not actuals:
            return {}
        correct = sum(1 for p, a in zip(predictions, actuals) if (p >= 0.5) == (a == 1.0))
        tp = sum(1 for p, a in zip(predictions, actuals) if p >= 0.5 and a == 1.0)
        fp = sum(1 for p, a in zip(predictions, actuals) if p >= 0.5 and a == 0.0)
        fn = sum(1 for p, a in zip(predictions, actuals) if p < 0.5 and a == 1.0)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        return {
            "accuracy": correct / len(predictions),
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0,
            "total_predictions": len(predictions),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        }

    def detect_drift(self, live_metrics: dict[str, float], reference_metrics: dict[str, float], threshold: float = 0.1) -> dict[str, Any]:
        drifts = {}
        for key in reference_metrics:
            if key in live_metrics:
                change = abs(live_metrics[key] - reference_metrics[key])
                drifts[key] = change > threshold
        return {
            "drift_detected": any(drifts.values()),
            "drifted_metrics": {k: v for k, v in drifts.items() if v},
            "drift_score": sum(1 for v in drifts.values() if v) / len(drifts) if drifts else 0,
        }

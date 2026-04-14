"""Thin adapter: form-based prediction via shared `prediction_core` service."""

from __future__ import annotations

from typing import Any

from score_predictor.prediction_core.model_io import load_model_artifacts
from score_predictor.prediction_core.service import predict_form_match


def load_model(model_path: str) -> dict[str, Any]:
    """Load trained model and its artifacts (used by PredictAPI warmup)."""
    model_artifacts = load_model_artifacts(model_path)
    feature_columns = model_artifacts.get("feature_columns")
    print("✓ Model loaded successfully")
    print(f"✓ Model type: {type(model_artifacts.get('model')).__name__}")
    print(f"✓ Model name: {model_artifacts.get('model_name', 'unknown')}")
    print(f"✓ Number of features: {len(feature_columns) if feature_columns else 'not specified'}")
    print(f"✓ Scaler: {'loaded' if model_artifacts.get('scaler') else 'not used'}")
    print(f"✓ Label encoder: {'loaded' if model_artifacts.get('label_encoder') else 'not used'}")
    return model_artifacts


def predict(model_path: str, matches_history_path: str, match_params: dict[str, Any]) -> dict[str, float]:
    return predict_form_match(model_path, matches_history_path, match_params)

from __future__ import annotations

from typing import Any

import joblib


def load_model_artifacts(model_path: str | Any) -> dict[str, Any]:
    """Load trained model bundle (model, scaler, feature_columns, label_encoder, ...)."""
    model_path = str(model_path)
    model_artifacts: dict[str, Any] = joblib.load(model_path)

    model = model_artifacts.get("model")
    if model is None:
        raise ValueError("Model not found in artifacts!")

    return model_artifacts

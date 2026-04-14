from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from score_predictor.prediction_core.features_form import (
    build_form_feature_row,
    prepare_history_dataframe,
)
from score_predictor.prediction_core.model_io import load_model_artifacts
from score_predictor.prediction_core.schemas import normalize_match_params


def predict_form_match(
    model_path: str,
    matches_history_path: str,
    match_params: dict[str, Any],
) -> dict[str, float]:
    """
    Form + history based prediction (used by Flask `/predict`).
    Returns home_win / draw / away_win probabilities.
    """
    params = normalize_match_params(match_params)
    home_team = params["home_team"]
    away_team = params["away_team"]
    match_date = pd.to_datetime(params["date"], format="%d/%m/%Y")

    model_artifacts = load_model_artifacts(model_path)
    model = model_artifacts["model"]
    scaler = model_artifacts["scaler"]

    df = prepare_history_dataframe(matches_history_path)
    row = build_form_feature_row(
        df,
        home_team,
        away_team,
        match_date,
        float(params.get("psch", np.nan)),
        float(params.get("pscd", np.nan)),
        float(params.get("psca", np.nan)),
    )
    features_df = pd.DataFrame([row])
    features_scaled = scaler.transform(features_df)

    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features_scaled)[0]
    else:
        probabilities = np.array([0.0, 0.0, 0.0])

    return {
        "home_win": float(probabilities[0]),
        "draw": float(probabilities[1]),
        "away_win": float(probabilities[2]),
    }

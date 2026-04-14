from __future__ import annotations

from typing import Any, Protocol

import numpy as np
import pandas as pd


class MatchLike(Protocol):
    psch: float | None
    pscd: float | None
    psca: float | None
    glicko_home_rating: float | None
    glicko_home_rd: float | None
    glicko_home_vol: float | None
    glicko_away_rating: float | None
    glicko_away_rd: float | None
    glicko_away_vol: float | None


def glicko_feature_row_from_match(match: MatchLike, home_advantage: float = 10.0) -> dict[str, float]:
    """Same engineered features as `Utils/background_score_predictor` production path."""
    psch = float(match.psch) if match.psch is not None else np.nan
    pscd = float(match.pscd) if match.pscd is not None else np.nan
    psca = float(match.psca) if match.psca is not None else np.nan
    gh = float(match.glicko_home_rating or 0.0) + home_advantage
    ga = float(match.glicko_away_rating or 0.0)
    ghr = float(match.glicko_home_rd or 0.0)
    gar = float(match.glicko_away_rd or 0.0)
    expected_home = 1 / (1 + 10 ** ((ga - gh) / 400))
    return {
        "psch": psch,
        "pscd": pscd,
        "psca": psca,
        "glicko_home_rating": gh,
        "glicko_home_rd": float(match.glicko_home_rd or 0.0),
        "glicko_home_vol": float(match.glicko_home_vol or 0.0),
        "glicko_away_rating": ga,
        "glicko_away_rd": gar,
        "glicko_away_vol": float(match.glicko_away_vol or 0.0),
        "rating_diff": gh - ga,
        "rating_sum": gh + ga,
        "rating_ratio": gh / (ga + 1e-6),
        "home_rd_inv": 1 / (ghr + 1e-6),
        "away_rd_inv": 1 / (gar + 1e-6),
        "rd_diff": ghr - gar,
        "rating_vs_bookie": (float(match.psch) if match.psch is not None else 0.0) - expected_home,
    }


def glicko_features_dataframe(match: MatchLike, home_advantage: float = 10.0) -> pd.DataFrame:
    return pd.DataFrame([glicko_feature_row_from_match(match, home_advantage=home_advantage)])

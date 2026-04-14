"""
Central settings loaded from environment (and optional `.env` at repo root).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

from score_predictor.bootstrap import repo_root


def _load_dotenv() -> Path:
    root = repo_root()
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
    else:
        load_dotenv()
    return root


@dataclass(frozen=True)
class Settings:
    repo_root: Path

    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str

    sstats_base_url: str

    # Form-based API model (CSV history + sklearn artifacts)
    form_model_path: Path
    form_matches_history_csv: Path

    # Worker: Glicko + threshold RF artifacts (under repo root by default)
    glicko_rf_model_path: Path
    rf_thresholds_model_path: Path
    glicko_home_advantage: float

    # ML training scripts
    ml_train_cutoff_date: str
    default_dataset_csv: Path

    @property
    def sqlalchemy_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return f"postgresql+psycopg2://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache
def get_settings() -> Settings:
    root = _load_dotenv()

    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    if not db_password and db_host not in ("localhost", "127.0.0.1"):
        # Allow local dev without .env; require explicit empty only for non-local
        pass

    return Settings(
        repo_root=root,
        db_user=os.getenv("DB_USER", "postgres"),
        db_password=db_password,
        db_host=db_host,
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "DbScore"),
        sstats_base_url=os.getenv("SSTATS_BASE_URL", "https://api.sstats.net").rstrip("/"),
        form_model_path=root / os.getenv("FORM_MODEL_PATH", "Trained models/random_forest_20260226_134721.pkl"),
        form_matches_history_csv=root
        / os.getenv("FORM_MATCHES_HISTORY_CSV", "Datasets/RUS_default.csv"),
        glicko_rf_model_path=root
        / os.getenv(
            "GLICKO_RF_MODEL_PATH",
            # NOTE: current repo artifact has a missing path separator in the filename.
            "Utils/Trained modelsrandom_forest_20260304_201754.pkl",
        ),
        rf_thresholds_model_path=root
        / os.getenv(
            "RF_THRESHOLDS_MODEL_PATH",
            "Utils/random_forest_with_thresholds_20260314_113048.pkl",
        ),
        glicko_home_advantage=float(os.getenv("GLICKO_HOME_ADVANTAGE", "10")),
        ml_train_cutoff_date=os.getenv("ML_TRAIN_CUTOFF_DATE", "2099-12-31"),
        default_dataset_csv=root / os.getenv("DEFAULT_DATASET_CSV", "Datasets/RUS_default.csv"),
    )


def training_sql_glicko(cutoff_date: str | None = None) -> str:
    """SQL used by ML Core Glicko scripts; cutoff limits rows for temporal validity."""
    settings = get_settings()
    cutoff = cutoff_date or settings.ml_train_cutoff_date
    return (
        "select t_h.team_name as home, t_a.team_name as away, "
        "start_match ::timestamp::date as date, home_goals as hg, away_goals as ag, "
        "psch, pscd, psca, winner, "
        "glicko_home_rating, glicko_home_rd, glicko_home_vol, "
        "glicko_away_rating, glicko_away_rd, glicko_away_vol "
        "from matches join teams as t_h on home_team = t_h.team_id "
        "join teams as t_a on away_team=t_a.team_id "
        f"where glicko_home_rd > 0 and start_match < '{cutoff}' "
        "order by start_match asc"
    )

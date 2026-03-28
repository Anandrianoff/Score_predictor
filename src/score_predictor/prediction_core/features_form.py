from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from Utils import utils


def prepare_history_dataframe(matches_history_path: str | Any) -> pd.DataFrame:
    """
    Load CSV used for form/stats features (RUS_default-style).
    Expects columns: Date, Season, Home, Away, HG, AG — normalized internally.
    """
    path = str(matches_history_path)
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
    df = df.sort_values(["Season", "Date"]).reset_index(drop=True)
    # Lowercase names for shared utils.calculate_team_form (home, away, date, hg, ag)
    df = df.rename(
        columns={
            "Home": "home",
            "Away": "away",
            "Date": "date",
            "HG": "hg",
            "AG": "ag",
        }
    )
    return df


def build_form_feature_row(
    df: pd.DataFrame,
    home_team: str,
    away_team: str,
    match_date: pd.Timestamp,
    psch: float,
    pscd: float,
    psca: float,
) -> dict[str, float]:
    home_form = utils.calculate_team_form(home_team, match_date, df)
    away_form = utils.calculate_team_form(away_team, match_date, df)
    home_stats = utils.calculate_team_stats(home_team, match_date, df)
    away_stats = utils.calculate_team_stats(away_team, match_date, df)

    home_advantage = 1 if home_stats["avg_points_per_match"] > away_stats["avg_points_per_match"] else 0

    return {
        "home_form_points": float(home_form["form_points"]),
        "away_form_points": float(away_form["form_points"]),
        "home_form_goals_scored": float(home_form["form_goals_scored"]),
        "away_form_goals_scored": float(away_form["form_goals_scored"]),
        "home_form_goals_conceded": float(home_form["form_goals_conceded"]),
        "away_form_goals_conceded": float(away_form["form_goals_conceded"]),
        "home_form_matches": float(home_form["form_matches_played"]),
        "away_form_matches": float(away_form["form_matches_played"]),
        "home_avg_form_points": float(home_form["avg_form_points"]),
        "away_avg_form_points": float(away_form["avg_form_points"]),
        "home_total_points": float(home_stats["total_points"]),
        "away_total_points": float(away_stats["total_points"]),
        "home_total_goals_scored": float(home_stats["total_goals_scored"]),
        "away_total_goals_scored": float(away_stats["total_goals_scored"]),
        "home_total_goals_conceded": float(home_stats["total_goals_conceded"]),
        "away_total_goals_conceded": float(away_stats["total_goals_conceded"]),
        "home_matches_played": float(home_stats["total_matches"]),
        "away_matches_played": float(away_stats["total_matches"]),
        "home_avg_points": float(home_stats["avg_points_per_match"]),
        "away_avg_points": float(away_stats["avg_points_per_match"]),
        "form_points_diff": float(home_form["form_points"] - away_form["form_points"]),
        "avg_points_diff": float(
            home_stats["avg_points_per_match"] - away_stats["avg_points_per_match"]
        ),
        "goals_scored_diff": float(
            home_stats["total_goals_scored"] / max(1, home_stats["total_matches"])
            - away_stats["total_goals_scored"] / max(1, away_stats["total_matches"])
        ),
        "goals_conceded_diff": float(
            home_stats["total_goals_conceded"] / max(1, home_stats["total_matches"])
            - away_stats["total_goals_conceded"] / max(1, away_stats["total_matches"])
        ),
        "home_advantage": float(home_advantage),
        "psch": float(psch),
        "pscd": float(pscd),
        "psca": float(psca),
    }

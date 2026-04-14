from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from score_predictor.bootstrap import ensure_project_import_paths

ensure_project_import_paths()

from DataManager import get_matches_by_date, make_bet, update_bet_result_by_match_id  # type: ignore[reportMissingImports]
import DataModels  # type: ignore[reportMissingImports]


logger = logging.getLogger(__name__)


def _format_result(result: Optional[DataModels.MatchResult]) -> str:
    if result is None:
        return "None"
    if result == DataModels.MatchResult.home:
        return "home"
    if result == DataModels.MatchResult.draw:
        return "draw"
    return "away"


def make_bets_for_date(match_date: date, bet_size: float) -> int:
    """Create bets for all matches in `match_date`."""
    matches = get_matches_by_date(match_date).matches
    created = 0

    for m in matches:
        if m.winner_predict is None or m.odd is None:
            continue
        make_bet(m.match_id, bet_size, m.winner_predict, float(m.odd))
        created += 1

    logger.info(f"Created {created} bets for {match_date}")
    return created


def update_bet_results_for_date(match_date: date) -> int:
    """Update bet_result for all matches in `match_date` (yesterday facts)."""
    matches = get_matches_by_date(match_date).matches
    updated = 0

    for m in matches:
        if m.winner_fact is None:
            continue
        update_bet_result_by_match_id(m.match_id, m.winner_fact)
        updated += 1

    logger.info(f"Updated {updated} bet results for {match_date}")
    return updated


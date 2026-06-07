from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from score_predictor.bootstrap import ensure_project_import_paths

ensure_project_import_paths()

import DataManager  # type: ignore[reportMissingImports]
from DataManager import update_bet_result_by_match_id  # type: ignore[reportMissingImports]
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
    """Create bets for all matches in `match_date` using Kelly criterion and transactions bankroll."""
    created = 0

    start_dt = datetime.combine(match_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    with DataManager.Session() as session:
        last_tx = (
            session.query(DataModels.Transaction)
            .order_by(DataModels.Transaction.date_time.desc(), DataModels.Transaction.id.desc())
            .first()
        )
        bankroll = float(last_tx.bankroll) if last_tx is not None else 0.0

        matches = DataModels.get_matches_by_date(session, start_dt, end_dt)
        for match in matches:
            if match.predicted_score is None or match.predict_proba is None:
                continue

            if match.predicted_score == DataModels.MatchResult.home:
                odd = match.psch
            elif match.predicted_score == DataModels.MatchResult.draw:
                odd = match.pscd
            else:
                odd = match.psca

            if odd is None:
                continue

            odd_f = float(odd)
            proba_f = float(match.predict_proba)
            if odd_f <= 1:
                continue

            kelly_criterion = (odd_f * proba_f - 1.0) / (odd_f - 1.0)
            bet_amount = bankroll * (kelly_criterion / 4.0)
            if bet_amount < 0:
                bet_amount = 0.0

            bet = DataModels.Bet(
                match_id=match.match_id,
                bet_amount=float(bet_amount),
                bet_type=match.predicted_score,
                bet_odds=float(odd_f),
                kelly_criterion=float(kelly_criterion),
            )
            session.add(bet)
            session.flush()

            bankroll = bankroll - float(bet_amount)
            tx = DataModels.Transaction(
                date_time=datetime.now(),
                bankroll=float(bankroll),
                amount=-float(bet_amount),
                bet_id=int(bet.bet_id),
            )
            session.add(tx)

            session.commit()
            created += 1

    logger.info(f"Created {created} bets for {match_date}")
    return created


def update_bet_results_for_date(match_date: date) -> int:
    """Update bet_result for all matches in `match_date` (yesterday facts)."""
    updated = 0

    start_dt = datetime.combine(match_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    with DataManager.Session() as session:
        matches = DataModels.get_matches_by_date(session, start_dt, end_dt)
        for m in matches:
            if m.winner is None:
                continue
            update_bet_result_by_match_id(m.match_id, m.winner)
            updated += 1

    logger.info(f"Updated {updated} bet results for {match_date}")
    return updated


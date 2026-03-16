from typing import List
from datetime import datetime
from DataModels import MatchResult

class MatchDTO():
    match_id: int
    home_team_id: int
    home_team_name_rus: str
    away_team_id: int
    away_team_name_rus: str
    winner_predict: str
    odd: float
    winner_fact: MatchResult | None = None


class MatchesResponse():
    date: datetime
    matches: List[MatchDTO]

class BetResultsDTO():
    matches_count: int
    guess_matches: int
    not_guess_matches: int
    bet_amount: float
    bet_profit: float
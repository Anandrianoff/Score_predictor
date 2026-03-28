from typing import List, Optional
from datetime import datetime
from DataModels import MatchResult

class MatchDTO():
    match_id: int
    home_team_id: int
    home_team_name_rus: str
    away_team_id: int
    away_team_name_rus: str
    start_match: Optional[datetime]
    home_goals: Optional[int]
    away_goals: Optional[int]
    winner_predict: Optional[MatchResult]
    odd: Optional[float]
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
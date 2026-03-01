from typing import List
from datetime import datetime

class Match():
    match_id: int
    home_team_id: int
    home_team_name_rus: str
    away_team_id: int
    away_team_name_rus: str
    winner_predict: str
    odd: float
    winner_fact: str | None = None


class MatchesResponse():
    date: datetime
    matches: List[Match]
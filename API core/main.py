from datetime import date
import sys
sys.path.append(r'D:\Programming\Score_predictor')
from DataManager.DataManager import get_matches_by_date

matches = get_matches_by_date(date.today())
for match in matches.matches:
    print(f"Матч ID: {match.match_id}, Домашняя команда: {match.home_team_name_rus}, Гостевая команда: {match.away_team_name_rus}")
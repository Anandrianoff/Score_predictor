import sys
import time
from sqlalchemy import create_engine, text
import api_models
from api_models import MatchesResponse
import DataModels
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime, timedelta 
import requests
from dotenv import load_dotenv
import os

load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD')

db_path = f'postgresql+psycopg2://postgres:{DB_PASSWORD}@localhost:5432/DbScore'
Base_url = "https://api.sstats.net"

engine = create_engine(db_path)
Session = sessionmaker(engine)

def create_tables():
    Base.metadata.create_all(engine)
    
def add_all_teams():
    request_url = Base_url + "/games/list?leagueid=235&year=2025"
    response = requests.get(request_url)
    data = response.json()
    teams = set()
    if data.get('status') == 'OK':
        for match in data['data']:
            # Добавляем домашнюю команду
            home = match['homeTeam']
            teams.add((home['id'], home['name']))
            
            # Добавляем гостевую команду
            away = match['awayTeam']
            teams.add((away['id'], away['name']))
    
    # Сортируем по названию
    sorted_teams = sorted(teams, key=lambda x: x[1])
    for team_id, team_name in sorted_teams:
        print(f"team_id: {team_id}, team_name: '{team_name}'")
        with Session() as session:
            DataModels.add_team(session, team_name, team_id)
    return ""

def add_matches(from_date, to_date):
    # request_matches_url = Base_url + f"/games/list?leagueid=235&from={from_date}&to={to_date}"
    request_matches_url = Base_url + f"/games/list?leagueid=235&year=2025"
    response = requests.get(request_matches_url)
    data = response.json()
    if data.get('status') == 'OK':
        with Session() as session:
            for match in data['data']:
                match_api_id = match['id']
                home_team = DataModels.get_team_by_api_id(session, match['homeTeam']['id'])
                if home_team is None:
                    home_team = DataModels.add_team(session, match['homeTeam']['name'], team_api_id=match['homeTeam']['id'])
                home_team_id = home_team.team_id
                away_team = DataModels.get_team_by_api_id(session, match['awayTeam']['id'])
                if away_team is None:
                    away_team = DataModels.add_team(session, match['awayTeam']['name'], team_api_id=match['awayTeam']['id'])
                away_team_id = away_team.team_id
                season = match['season']['year']
                start_match = datetime.fromisoformat(match['date'].replace('Z', '+00:00'))
                psch = 0
                pscd = 0
                psca = 0
                homegoals = match.get('homeFTResult')
                awaygoals = match.get('awayFTResult')
                if (match.get('odds')):
                    for odd in match['odds']:
                        if odd['marketId'] == 1:  # Рынок 1 - это обычно исход матча
                            if (odd.get('odds')):
                                for odd_outcome in odd['odds']:
                                    if odd_outcome['name'].lower() == "home":  # Победа домашней команды
                                        psch = odd_outcome['value']
                                    elif odd_outcome['name'].lower() == "draw":  # Ничья
                                        pscd = odd_outcome['value']
                                    elif odd_outcome['name'].lower() == "away":  # Победа гостевой команды
                                        psca = odd_outcome['value']
                request_glicko_url = Base_url + f"/Games/glicko/{match_api_id}"
                print(f"Запрос к Glicko API: {request_glicko_url}")
                response_glicko = requests.get(request_glicko_url)
                glicko_json = response_glicko.json()
                print(f"Ответ от Glicko API: {response_glicko.status_code} - {response_glicko.text}")
                home_rating = 0
                home_rd = 0
                home_vol = 0
                away_rating = 0
                away_rd = 0
                away_vol = 0
                if glicko_json.get('status') == 'OK':
                    glicko_data = glicko_json['data']['glicko']
                    home_rating = glicko_data['homeRating']
                    home_rd = glicko_data['homeRd']
                    home_vol = glicko_data['homeVolatility']
                    away_rating = glicko_data['awayRating']
                    away_rd = glicko_data['awayRd']
                    away_vol = glicko_data['awayVolatility']

                print(f"home_team_id: {home_team_id}, away_team_id: {away_team_id}, season: {season}, start_match: {start_match}, psch: {psch}, pscd: {pscd}, psca: {psca}")
                DataModels.add_match(session=session, 
                                     home_team_id=home_team_id, 
                                     away_team_id=away_team_id, 
                                     start_match=start_match, 
                                     season=season, 
                                     home_goals=homegoals, 
                                     away_goals=awaygoals, 
                                     psch=psch, 
                                     pscd=pscd, 
                                     psca=psca, 
                                     home_rating=home_rating, 
                                     home_rd=home_rd, 
                                     home_vol=home_vol, 
                                     away_rating=away_rating, 
                                     away_rd=away_rd, 
                                     away_vol=away_vol,
                                     match_api_id=match_api_id)
                time.sleep(1.5)  # Небольшая задержка между запросами, чтобы не перегружать API
    return 

def make_bet(
    match_id: int,
    bet_amount: float,
    bet_type: DataModels.MatchResult,
    bet_odds: float):
        with Session() as session:
            return DataModels.add_bet(session, match_id, bet_amount, bet_type, bet_odds)

def update_bet_result_by_match_id(match_id: int, winner_fact: DataModels.MatchResult):
    with Session() as session:
        bets = DataModels.get_bets_by_match_id(session, match_id)
        for bet in bets:
            DataModels.update_bet_result(session, bet.bet_id, winner_fact)
        return bets

def get_matches_by_date(date):
    matches_response = MatchesResponse()
    matches_response.date = date
    matches_response.matches = []
    with Session() as session:
        matches = DataModels.get_matches_by_date(session, date)
        if matches:
            for match in matches:
                filled_match = api_models.MatchDTO()
                filled_match.match_id = match.match_id
                filled_match.home_team_id = match.home_team
                filled_match.home_team_name_rus = DataModels.get_team_by_id(session, match.home_team).team_name_rus
                filled_match.away_team_id = match.away_team
                filled_match.away_team_name_rus = DataModels.get_team_by_id(session, match.away_team).team_name_rus
                filled_match.winner_predict = match.predicted_score
                filled_match.winner_fact = match.winner
                if match.predicted_score == DataModels.MatchResult.home:
                    filled_match.odd = match.psch
                elif match.predicted_score == DataModels.MatchResult.draw:
                    filled_match.odd = match.pscd
                elif match.predicted_score == DataModels.MatchResult.away:
                    filled_match.odd = match.psca
                print(f"filled_match: {filled_match.__dict__}")
                matches_response.matches.append(filled_match)
    return matches_response


# Заполнение базы данных командами и будущими матчами            
# add_all_teams()           
# add_matches("2022-05-25", datetime.now().strftime("%Y-%m-%d"))
# add_matches("2022-05-25", "2022-07-01")
    

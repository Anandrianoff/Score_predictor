import sys
from sqlalchemy import create_engine, text
sys.path.append(r'D:\Programming\Score_predictor')
from DataModels import Base, Team, Match, add_match, add_team, get_team_by_api_id
from sqlalchemy.orm import Session, sessionmaker
import psycopg2
from datetime import datetime 
import requests

db_path = 'postgresql+psycopg2://postgres:1234@localhost:5432/DbScore'
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
            add_team(session, team_name, team_id)
    return ""

def add_future_matches():
    request_url = Base_url + "/games/list?leagueid=235&year=2025&from=2026-02-27"
    response = requests.get(request_url)
    data = response.json()
    if data.get('status') == 'OK':
        with Session() as session:
            for match in data['data']:
                home_team_id = get_team_by_api_id(session, match['homeTeam']['id']).team_id
                away_team_id = get_team_by_api_id(session, match['awayTeam']['id']).team_id
                season = "2025/2026"
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
                            
                print(f"home_team_id: {home_team_id}, away_team_id: {away_team_id}, season: {season}, start_match: {start_match}, psch: {psch}, pscd: {pscd}, psca: {psca}")
                add_match(session, home_team_id, away_team_id, start_match, season, homegoals, awaygoals, psch, pscd, psca)

# Заполнение базы данных командами и будущими матчами            
# add_all_teams()           
# add_future_matches()

    

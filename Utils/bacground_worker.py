import os
import sys
import joblib
import numpy as np
from sqlalchemy import create_engine, text

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
data_manager_path = os.path.join(root_dir, 'DataManager')
sys.path.append(data_manager_path)
import api_models
from api_models import MatchesResponse
import DataModels
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime 
import requests
from datetime import timedelta
import logging
from dotenv import load_dotenv

load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

db_path = f'postgresql+psycopg2://postgres:{DB_PASSWORD}@{DB_HOST}:5432/DbScore'
Base_url = "https://api.sstats.net"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
engine = create_engine(db_path)
Session = sessionmaker(engine)

def update_games_info(date_from=None, date_to=None):
    date_from = date_from or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_to = date_to or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    request_url = Base_url + f"/games/list?leagueid=235&from={date_from}&to={date_to}"
    response = requests.get(request_url)
    data = response.json()
    logger.info(f"Матчей для обновления: {data.get('count')} (запрос: {request_url})")
    if data.get('status') == 'OK':
        with Session() as session:
            for match_response in data['data']:
                logger.info(f"Обновление информации для матча: {match_response['homeTeam']['name']} vs {match_response['awayTeam']['name']} ({match_response['date']})")
                match_to_update = DataModels.get_match_by_api_id(session, match_response['id'])
                season = match_response['season']['year']
                start_match = datetime.fromisoformat(match_response['date'].replace('Z', '+00:00'))
                match_to_update.home_goals = match_response.get('homeFTResult')
                match_to_update.away_goals = match_response.get('awayFTResult')
                if (match_response.get('odds')):
                    for odd in match_response['odds']:
                        if odd['marketId'] == 1:  # Рынок 1 - это обычно исход матча
                            if (odd.get('odds')):
                                for odd_outcome in odd['odds']:
                                    if odd_outcome['name'].lower() == "home":  # Победа домашней команды
                                        match_to_update.psch = odd_outcome['value']
                                    elif odd_outcome['name'].lower() == "draw":  # Ничья
                                        match_to_update.pscd = odd_outcome['value']
                                    elif odd_outcome['name'].lower() == "away":  # Победа гостевой команды
                                        match_to_update.psca = odd_outcome['value']
                
                # Обновим глико рейтинги для обеих команд, чтобы модель могла использовать их при предсказании
                if (start_match.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d")):
                    request_glicko_url = Base_url + f"/Games/glicko/{match_to_update.match_api_id}"
                    print(f"Запрос к Glicko API: {request_glicko_url}")
                    response_glicko = requests.get(request_glicko_url)
                    glicko_json = response_glicko.json()
                    print(f"Ответ от Glicko API: {response_glicko.status_code}")
                    if glicko_json.get('status') == 'OK':
                        glicko_data = glicko_json['data']['glicko']
                        match_to_update.glicko_home_rating = glicko_data['homeRating']
                        match_to_update.glicko_home_rd = glicko_data['homeRd']
                        match_to_update.glicko_home_vol = glicko_data['homeVolatility']
                        match_to_update.glicko_away_rating = glicko_data['awayRating']
                        match_to_update.glicko_away_rd = glicko_data['awayRd']
                        match_to_update.glicko_away_vol = glicko_data['awayVolatility']

                if (match_to_update.home_goals is not None and match_to_update.away_goals is not None and match_response['statusName'] == 'Finished'):
                    if (match_to_update.away_goals > match_to_update.home_goals):
                        match_to_update.winner = DataModels.MatchResult.away
                    elif (match_to_update.home_goals > match_to_update.away_goals):
                        match_to_update.winner = DataModels.MatchResult.home
                    else:
                        match_to_update.winner = DataModels.MatchResult.draw
                print(f"match: {match_to_update.match_id}, season: {season}, start_match: {start_match}, psch: {match_to_update.psch}, pscd: {match_to_update.pscd}, psca: {match_to_update.psca}, homegoals: {match_to_update.home_goals}, awaygoals: {match_to_update.away_goals}, winner: {match_to_update.winner}")
                session.commit()
    return 


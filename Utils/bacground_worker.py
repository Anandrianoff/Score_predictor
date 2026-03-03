import sys
import joblib
import numpy as np
from sqlalchemy import create_engine, text
sys.path.append(r'D:\Programming\Score_predictor')
sys.path.append(r'D:\Programming\Score_predictor\DataManager')
import api_models
from api_models import MatchesResponse
import DataModels
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime 
import requests
from datetime import timedelta
import logging
import pandas as pd
from Utils import utils


db_path = 'postgresql+psycopg2://postgres:1234@localhost:5432/DbScore'
Base_url = "https://api.sstats.net"
model_path = rf"D:\Programming\Score_predictor\Trained models\random_forest_20260226_134721.pkl"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
engine = create_engine(db_path)
Session = sessionmaker(engine)

def load_model(model_path):
    """Load trained model and its artifacts."""
    model_artifacts = joblib.load(model_path)
    
    model = model_artifacts.get("model")
    scaler = model_artifacts.get("scaler")
    feature_columns = model_artifacts.get("feature_columns")
    label_encoder = model_artifacts.get("label_encoder")
    model_name = model_artifacts.get("model_name", 'unknown')
    
    if model is None:
        raise ValueError("Model not found in artifacts!")
    
    print("✓ Model loaded successfully")
    print(f"✓ Model type: {type(model).__name__}")
    print(f"✓ Model name: {model_name}")
    print(f"✓ Number of features: {len(feature_columns) if feature_columns else 'not specified'}")
    print(f"✓ Scaler: {'loaded' if scaler else 'not used'}")
    print(f"✓ Label encoder: {'loaded' if label_encoder else 'not used'}")
    
    return model_artifacts

def update_games_info():
    # today = datetime.now().strftime("%Y-%m-%d")
    today = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=0)).strftime("%Y-%m-%d")
    request_url = Base_url + f"/games/list?leagueid=235&from={today}&to={tomorrow}"
    response = requests.get(request_url)
    data = response.json()
    logger.info(f"Матчей для обновления: {data.get('count')} (запрос: {request_url})")
    if data.get('status') == 'OK':
        with Session() as session:
            for match_response in data['data']:
                logger.info(f"Обновление информации для матча: {match_response['homeTeam']['name']} vs {match_response['awayTeam']['name']} ({match_response['date']})")
                home_team_id = DataModels.get_team_by_api_id(session, match_response['homeTeam']['id']).team_id
                away_team_id = DataModels.get_team_by_api_id(session, match_response['awayTeam']['id']).team_id
                match_to_update = session.query(DataModels.Match).filter(
                    DataModels.Match.home_team == home_team_id,
                    DataModels.Match.away_team == away_team_id,
                    DataModels.Match.start_match.between(datetime.fromisoformat(today), datetime.fromisoformat(tomorrow))
                ).first()
                season = "2025/2026"
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
                
                if (match_to_update.home_goals is not None and match_to_update.away_goals is not None):
                    if (match_to_update.away_goals > match_to_update.home_goals):
                        match_to_update.winner = DataModels.MatchResult.away
                    elif (match_to_update.home_goals > match_to_update.away_goals):
                        match_to_update.winner = DataModels.MatchResult.home
                    else:
                        match_to_update.winner = DataModels.MatchResult.draw
                print(f"home_team_id: {home_team_id}, away_team_id: {away_team_id}, season: {season}, start_match: {start_match}, psch: {match_to_update.psch}, pscd: {match_to_update.pscd}, psca: {match_to_update.psca}, homegoals: {match_to_update.home_goals}, awaygoals: {match_to_update.away_goals}, winner: {match_to_update.winner}")
                session.commit()
    return

def update_prediction():
    today = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    # today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() - timedelta(days=0)).strftime("%Y-%m-%d")
    last_year = (datetime.now() - timedelta(days=185)).strftime("%Y-%m-%d")
    model_artifacts = load_model(model_path)
    model = model_artifacts.get("model")
    scaler = model_artifacts.get("scaler")
    query = f"select t_h.team_name_model as Home, t_a.team_name_model as Away, start_match as date, home_goals as HG, away_goals as AG, psch as PSCH,pscd as PSCD,psca as PSCA from matches join teams as t_h on home_team = t_h.team_id join teams as t_a on away_team=t_a.team_id where start_match >= '{last_year}' order by start_match asc"
    df = pd.read_sql_query(query, engine)
    with Session() as session:
        today_matches = session.query(DataModels.Match).filter(
            DataModels.Match.start_match.between(datetime.fromisoformat(today), datetime.fromisoformat(tomorrow)))
        for match in today_matches:
            home_team = session.query(DataModels.Team).filter(DataModels.Team.team_id == match.home_team).first().team_name_model
            away_team = session.query(DataModels.Team).filter(DataModels.Team.team_id == match.away_team).first().team_name_model

            # Форма команд (последние 5 матчей с весами)
            home_form = utils.calculate_team_form(home_team, today, df)
            away_form = utils.calculate_team_form(away_team, today, df)
        
            # Общая статистика команд
            home_stats = utils.calculate_team_stats(home_team, today, df)
            away_stats = utils.calculate_team_stats(away_team, today, df)

            # Коэффициенты букмекеров (нормализованные)
            psch = float(match.psch) if match.psch is not None else np.nan
            pscd = float(match.pscd) if match.pscd is not None else np.nan
            psca = float(match.psca) if match.psca is not None else np.nan

            # Преимущество домашней команды
            home_advantage = 1 if home_stats['avg_points_per_match'] > away_stats['avg_points_per_match'] else 0

            match_parameters_prepared = {
                # Форма команд
                'home_form_points': float(home_form['form_points']),
                'away_form_points': float(away_form['form_points']),
                'home_form_goals_scored': float(home_form['form_goals_scored']),
                'away_form_goals_scored': float(away_form['form_goals_scored']),
                'home_form_goals_conceded': float(home_form['form_goals_conceded']),
                'away_form_goals_conceded': float(away_form['form_goals_conceded']),
                'home_form_matches': float(home_form['form_matches_played']),
                'away_form_matches': float(away_form['form_matches_played']),
                'home_avg_form_points': float(home_form['avg_form_points']),
                'away_avg_form_points': float(away_form['avg_form_points']),

                # Общая статистика
                'home_total_points': float(home_stats['total_points']),
                'away_total_points': float(away_stats['total_points']),
                'home_total_goals_scored': float(home_stats['total_goals_scored']),
                'away_total_goals_scored': float(away_stats['total_goals_scored']),
                'home_total_goals_conceded': float(home_stats['total_goals_conceded']),
                'away_total_goals_conceded': float(away_stats['total_goals_conceded']),
                'home_matches_played': float(home_stats['total_matches']),
                'away_matches_played': float(away_stats['total_matches']),
                'home_avg_points': float(home_stats['avg_points_per_match']),
                'away_avg_points': float(away_stats['avg_points_per_match']),

                # Разница в форме и статистике
                'form_points_diff': float(home_form['form_points'] - away_form['form_points']),
                'avg_points_diff': float(home_stats['avg_points_per_match'] - away_stats['avg_points_per_match']),
                'goals_scored_diff': float(home_stats['total_goals_scored']/max(1, home_stats['total_matches']) - 
                                    away_stats['total_goals_scored']/max(1, away_stats['total_matches'])),
                'goals_conceded_diff': float(home_stats['total_goals_conceded']/max(1, home_stats['total_matches']) - 
                                      away_stats['total_goals_conceded']/max(1, away_stats['total_matches'])),

                # Преимущество домашней команды
                'home_advantage': float(home_advantage),

                # Букмекерские коэффициенты (если есть)
                'psch': psch,
                'pscd': pscd,
                'psca': psca,
            }

            features_df = pd.DataFrame([match_parameters_prepared])
            features_scaled = scaler.transform(features_df)
            prediction = model.predict(features_scaled)[0]
            logger.info(f"Предсказание для матча {home_team} vs {away_team} ({match.start_match}): {prediction}")   

            # Получаем вероятности
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(features_scaled)[0]
            else:
                probabilities = [0, 0, 0]

            if probabilities[0] > probabilities[1] and probabilities[0] > probabilities[2]:
                match.predicted_score = DataModels.MatchResult.home
            elif probabilities[1] > probabilities[0] and probabilities[1] > probabilities[2]:
                match.predicted_score = DataModels.MatchResult.draw        
            else:
                match.predicted_score = DataModels.MatchResult.away
            session.commit()
            logger.info(f"Обновлено предсказание для матча {home_team} vs {away_team} ({match.start_match}): {match.predicted_score}, вероятности - Home: {probabilities[0]:.2f}, Draw: {probabilities[1]:.2f}, Away: {probabilities[2]:.2f}")
    return 

update_games_info()
update_prediction()

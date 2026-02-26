import pickle
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime
import warnings
import joblib

import sys
sys.path.append(r'D:\Programming\Score_predictor')
from Utils import utils


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

def predict (model_path, matches_history_path, match_params):
    model_artifacts = joblib.load(model_path)
    model = model_artifacts.get("model")
    scaler = model_artifacts.get("scaler")
    feature_columns = model_artifacts.get("feature_columns")
    label_encoder = model_artifacts.get("label_encoder")

    df= pd.read_csv(matches_history_path)
    # Преобразование даты
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    df = df.sort_values(['Season', 'Date']).reset_index(drop=True)
    
    home_team = match_params['home_team']
    away_team = match_params['away_team']
    match_date = pd.to_datetime(match_params['date'], format='%d/%m/%Y')
        
    # Форма команд (последние 5 матчей с весами)
    home_form = utils.calculate_team_form(home_team, match_date, df)
    away_form = utils.calculate_team_form(away_team, match_date, df)
        
    # Общая статистика команд
    home_stats = utils.calculate_team_stats(home_team, match_date, df)
    away_stats = utils.calculate_team_stats(away_team, match_date, df)

     # Коэффициенты букмекеров (нормализованные)
    psch = float(match_params.get('psch', np.nan))
    pscd = float(match_params.get('pscd', np.nan))
    psca = float(match_params.get('psca', np.nan))

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

    # Получаем вероятности
    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(features_scaled)[0]
    else:
        probabilities = [0, 0, 0]
        
    # Маппинг результатов
    # if label_encoder is not None:
    #     prediction_label = label_encoder.inverse_transform([prediction])[0]
    # else:
    #     result_map = {0: "H", 1: "D", 2: "A"}
    #     prediction_label = result_map.get(prediction, str(prediction))
        
    response = {
            "home_win": float(probabilities[0]),
            "draw": float(probabilities[1]),
            "away_win": float(probabilities[2])
        }
    
    return response


import pandas as pd
import numpy as np

# Функция для расчета формы команды
def calculate_team_form(team, date, df, num_matches=5):
    """
    Расчет формы команды на основе последних num_matches матчей
    Последние матчи имеют больший вес
    """
    # Все матчи команды до указанной даты
    team_matches = df[
        ((df['Home'] == team) | (df['Away'] == team)) & 
        (df['Date'] < date)
    ].sort_values('Date', ascending=False).head(num_matches)
    
    if len(team_matches) == 0:
        return {
            'form_points': 0,
            'form_goals_scored': 0,
            'form_goals_conceded': 0,
            'form_matches_played': 0,
            'avg_form_points': 0
        }
    
    # Веса для матчей (более поздние - больший вес)
    weights = np.linspace(1, 0.5, len(team_matches))
    weights = weights / weights.sum()  # Нормализация
    
    form_points = 0
    total_goals_scored = 0
    total_goals_conceded = 0
    
    for idx, (_, match) in enumerate(team_matches.iterrows()):
        weight = weights[idx]
        
        if match['Home'] == team:
            goals_scored = match['HG']
            goals_conceded = match['AG']
            if match['HG'] > match['AG']:  # Победа
                points = 3
            elif match['HG'] == match['AG']:  # Ничья
                points = 1
            else:  # Поражение
                points = 0
        else:  # Команда в гостях
            goals_scored = match['AG']
            goals_conceded = match['HG']
            if match['AG'] > match['HG']:
                points = 3
            elif match['AG'] == match['HG']:
                points = 1
            else:
                points = 0
        
        form_points += points * weight
        total_goals_scored += goals_scored * weight
        total_goals_conceded += goals_conceded * weight
    
    return {
        'form_points': form_points,
        'form_goals_scored': total_goals_scored,
        'form_goals_conceded': total_goals_conceded,
        'form_matches_played': len(team_matches),
        'avg_form_points': form_points / len(team_matches) if len(team_matches) > 0 else 0
    }

# Расчет общей статистики команды
def calculate_team_stats(team, date, df):
    """Расчет общей статистики команды"""
    team_matches = df[
        ((df['Home'] == team) | (df['Away'] == team)) & 
        (df['Date'] < date)
    ]
    
    if len(team_matches) == 0:
        return {
            'total_matches': 0,
            'total_points': 0,
            'total_goals_scored': 0,
            'total_goals_conceded': 0,
            'avg_points_per_match': 0
        }
    
    total_points = 0
    total_goals_scored = 0
    total_goals_conceded = 0
    
    for _, match in team_matches.iterrows():
        if match['Home'] == team:
            total_goals_scored += match['HG']
            total_goals_conceded += match['AG']
            if match['HG'] > match['AG']:
                total_points += 3
            elif match['HG'] == match['AG']:
                total_points += 1
        else:
            total_goals_scored += match['AG']
            total_goals_conceded += match['HG']
            if match['AG'] > match['HG']:
                total_points += 3
            elif match['AG'] == match['HG']:
                total_points += 1
    
    return {
        'total_matches': len(team_matches),
        'total_points': total_points,
        'total_goals_scored': total_goals_scored,
        'total_goals_conceded': total_goals_conceded,
        'avg_points_per_match': total_points / len(team_matches) if len(team_matches) > 0 else 0
    }
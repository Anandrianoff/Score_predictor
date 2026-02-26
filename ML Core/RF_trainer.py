import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime
import warnings
import joblib
import Utils.utils as utils
warnings.filterwarnings('ignore')

# Загрузка данных
df = pd.read_csv(r'D:\Programming\Score_predictor\Datasets\RUS_default.csv')

# Преобразование даты
df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
df = df.sort_values(['Season', 'Date']).reset_index(drop=True)

# Кодирование результата (H=0, D=1, A=2)
label_encoder = LabelEncoder()
df['Result_encoded'] = label_encoder.fit_transform(df['Res'])

print(f"Всего матчей: {len(df)}")
print(f"Сезоны: {df['Season'].unique()}")
print(f"Команды: {df['Home'].nunique()}")

# def calculate_team_form(team, date, df, num_matches=5):
#     """
#     Расчет формы команды на основе последних num_matches матчей
#     Последние матчи имеют больший вес
#     """
#     # Все матчи команды до указанной даты
#     team_matches = df[
#         ((df['Home'] == team) | (df['Away'] == team)) & 
#         (df['Date'] < date)
#     ].sort_values('Date', ascending=False).head(num_matches)
    
#     if len(team_matches) == 0:
#         return {
#             'form_points': 0,
#             'form_goals_scored': 0,
#             'form_goals_conceded': 0,
#             'form_matches_played': 0,
#             'avg_form_points': 0
#         }
    
#     # Веса для матчей (более поздние - больший вес)
#     weights = np.linspace(1, 0.5, len(team_matches))
#     weights = weights / weights.sum()  # Нормализация
    
#     form_points = 0
#     total_goals_scored = 0
#     total_goals_conceded = 0
    
#     for idx, (_, match) in enumerate(team_matches.iterrows()):
#         weight = weights[idx]
        
#         if match['Home'] == team:
#             goals_scored = match['HG']
#             goals_conceded = match['AG']
#             if match['HG'] > match['AG']:  # Победа
#                 points = 3
#             elif match['HG'] == match['AG']:  # Ничья
#                 points = 1
#             else:  # Поражение
#                 points = 0
#         else:  # Команда в гостях
#             goals_scored = match['AG']
#             goals_conceded = match['HG']
#             if match['AG'] > match['HG']:
#                 points = 3
#             elif match['AG'] == match['HG']:
#                 points = 1
#             else:
#                 points = 0
        
#         form_points += points * weight
#         total_goals_scored += goals_scored * weight
#         total_goals_conceded += goals_conceded * weight
    
#     return {
#         'form_points': form_points,
#         'form_goals_scored': total_goals_scored,
#         'form_goals_conceded': total_goals_conceded,
#         'form_matches_played': len(team_matches),
#         'avg_form_points': form_points / len(team_matches) if len(team_matches) > 0 else 0
#     }

# def calculate_team_stats(team, date, df):
#     """Расчет общей статистики команды"""
#     team_matches = df[
#         ((df['Home'] == team) | (df['Away'] == team)) & 
#         (df['Date'] < date)
#     ]
    
#     if len(team_matches) == 0:
#         return {
#             'total_matches': 0,
#             'total_points': 0,
#             'total_goals_scored': 0,
#             'total_goals_conceded': 0,
#             'avg_points_per_match': 0
#         }
    
#     total_points = 0
#     total_goals_scored = 0
#     total_goals_conceded = 0
    
#     for _, match in team_matches.iterrows():
#         if match['Home'] == team:
#             total_goals_scored += match['HG']
#             total_goals_conceded += match['AG']
#             if match['HG'] > match['AG']:
#                 total_points += 3
#             elif match['HG'] == match['AG']:
#                 total_points += 1
#         else:
#             total_goals_scored += match['AG']
#             total_goals_conceded += match['HG']
#             if match['AG'] > match['HG']:
#                 total_points += 3
#             elif match['AG'] == match['HG']:
#                 total_points += 1
    
#     return {
#         'total_matches': len(team_matches),
#         'total_points': total_points,
#         'total_goals_scored': total_goals_scored,
#         'total_goals_conceded': total_goals_conceded,
#         'avg_points_per_match': total_points / len(team_matches) if len(team_matches) > 0 else 0
#     }

def create_features(df):
    """Создание признаков для всех матчей"""
    features = []
    
    for idx, row in df.iterrows():
        home_team = row['Home']
        away_team = row['Away']
        match_date = row['Date']
        
        # Форма команд (последние 5 матчей с весами)
        home_form = utils.calculate_team_form(home_team, match_date, df)
        away_form = utils.calculate_team_form(away_team, match_date, df)
        
        # Общая статистика команд
        home_stats = utils.calculate_team_stats(home_team, match_date, df)
        away_stats = utils.calculate_team_stats(away_team, match_date, df)
        
        # Коэффициенты букмекеров (нормализованные)
        psch = row.get('PSCH', np.nan)
        pscd = row.get('PSCD', np.nan)
        psca = row.get('PSCA', np.nan)
        
        # Преимущество домашней команды
        home_advantage = 1 if home_stats['avg_points_per_match'] > away_stats['avg_points_per_match'] else 0
        
        feature_row = {
            # Форма команд
            'home_form_points': home_form['form_points'],
            'away_form_points': away_form['form_points'],
            'home_form_goals_scored': home_form['form_goals_scored'],
            'away_form_goals_scored': away_form['form_goals_scored'],
            'home_form_goals_conceded': home_form['form_goals_conceded'],
            'away_form_goals_conceded': away_form['form_goals_conceded'],
            'home_form_matches': home_form['form_matches_played'],
            'away_form_matches': away_form['form_matches_played'],
            'home_avg_form_points': home_form['avg_form_points'],
            'away_avg_form_points': away_form['avg_form_points'],
            
            # Общая статистика
            'home_total_points': home_stats['total_points'],
            'away_total_points': away_stats['total_points'],
            'home_total_goals_scored': home_stats['total_goals_scored'],
            'away_total_goals_scored': away_stats['total_goals_scored'],
            'home_total_goals_conceded': home_stats['total_goals_conceded'],
            'away_total_goals_conceded': away_stats['total_goals_conceded'],
            'home_matches_played': home_stats['total_matches'],
            'away_matches_played': away_stats['total_matches'],
            'home_avg_points': home_stats['avg_points_per_match'],
            'away_avg_points': away_stats['avg_points_per_match'],
            
            # Разница в форме и статистике
            'form_points_diff': home_form['form_points'] - away_form['form_points'],
            'avg_points_diff': home_stats['avg_points_per_match'] - away_stats['avg_points_per_match'],
            'goals_scored_diff': home_stats['total_goals_scored']/max(1, home_stats['total_matches']) - 
                                away_stats['total_goals_scored']/max(1, away_stats['total_matches']),
            'goals_conceded_diff': home_stats['total_goals_conceded']/max(1, home_stats['total_matches']) - 
                                  away_stats['total_goals_conceded']/max(1, away_stats['total_matches']),
            
            # Преимущество домашней команды
            'home_advantage': home_advantage,
            
            # Букмекерские коэффициенты (если есть)
            'psch': psch,
            'pscd': pscd,
            'psca': psca,
            
            # Целевая переменная
            'target': row['Result_encoded']
        }
        
        features.append(feature_row)
    
    return pd.DataFrame(features)

# Создание признаков
print("Создание признаков...")
features_df = create_features(df)

# Удаление строк с NaN (первые матчи сезона без истории)
features_df = features_df.dropna().reset_index(drop=True)

print(f"Размер датасета с признаками: {features_df.shape}")
print(f"Распределение классов:\n{features_df['target'].value_counts()}")

# Разделение на признаки и целевую переменную
X = features_df.drop('target', axis=1)
y = features_df['target']

# Масштабирование признаков
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Разделение на обучающую и тестовую выборки с учетом временного порядка
# Используем последние 20% данных для тестирования
split_idx = int(len(X_scaled) * 0.8)
X_train = X_scaled
y_train = y

print(f"Обучающая выборка: {X_train.shape}")

# Обучение random forest
print("\n" + "="*50)
print("Обучение Random Forest...")
rf_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)

# Запаковываем в модель
model_artifacts = {
    'model': rf_model,
    'scaler': scaler,
    'feature_columns': X.columns.tolist(),
    'label_encoder': label_encoder,
    'model_name': "random_forest",
}
# сохраняем артефакты с отметкой времени
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filepath = rf"D:\Programming\Score_predictor\Trained modelsrandom_forest_{timestamp}.pkl"
joblib.dump(model_artifacts, filepath)
print(f"Model trained and saved {filepath}")
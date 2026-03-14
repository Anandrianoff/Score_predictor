# Вторая версия случайного леса. 
# Список признаков: 'glicko_home_rating', 'glicko_home_rd', 'glicko_home_vol', 'glicko_away_rating', 'glicko_away_rd', 
# 'glicko_away_vol', 'psch', 'pscd', 'psca', 'rating_diff', 'rating_sum', 'rating_ratio', 'home_rd_inv', 'away_rd_inv', 
# 'rd_diff', 'rating_vs_bookie'
# Accuracy: 0.4885
# F1 macro: 0.4380
# F1 weighted: 0.4727

# Матрица ошибок:
# [[15 13 21]
#  [ 7 14 24]
#  [11 13 56]]

# Classification Report:
#               precision    recall  f1-score   support

#        Гости       0.45      0.31      0.37        49
#        Ничья       0.35      0.31      0.33        45
#      Хозяева       0.55      0.70      0.62        80

#     accuracy                           0.49       174
#    macro avg       0.45      0.44      0.44       174
# weighted avg       0.47      0.49      0.47       174

from posixpath import join

import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score
from sklearn.dummy import DummyClassifier
from sqlalchemy import asc
import xgboost as xgb
from datetime import datetime
import warnings
from sqlalchemy import create_engine
warnings.filterwarnings('ignore')
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_validate, GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report, log_loss
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

db_path = 'postgresql+psycopg2://postgres:1234@localhost:5432/DbScore'
sql = "select t_h.team_name as Home, t_a.team_name as Away, start_match ::timestamp::date as date, home_goals as HG, away_goals as AG, psch as PSCH, pscd as PSCD,psca as PSCA,winner,glicko_home_rating,glicko_home_rd,glicko_home_vol,glicko_away_rating,glicko_away_rd,glicko_away_vol from matches join teams as t_h on home_team = t_h.team_id join teams as t_a on away_team=t_a.team_id where glicko_home_rd > 0 and start_match < '2026-03-03' order by start_match asc"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
engine = create_engine(db_path)
df = pd.read_sql(sql, con=engine)

# Преобразование даты
df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
df = df.sort_values(['date']).reset_index(drop=True)

# Кодирование результата (H=0, D=1, A=2)
label_encoder = LabelEncoder()
df['result_encoded'] = label_encoder.fit_transform(df['winner'])

logger.info(f"Всего матчей: {len(df)}")
logger.info(f"Команды: {df['home'].nunique()}")

def create_features(df):
    """Создание признаков для всех матчей"""
    features = []
    
    for idx, row in df.iterrows():
        home_team = row['home']
        away_team = row['away']
        match_date = row['date']
        
        # # Форма команд (последние 5 матчей с весами)
        # home_form = calculate_team_form(home_team, match_date, df)
        # away_form = calculate_team_form(away_team, match_date, df)
        
        # # Общая статистика команд
        # home_stats = calculate_team_stats(home_team, match_date, df)
        # away_stats = calculate_team_stats(away_team, match_date, df)
        
        # Коэффициенты букмекеров (нормализованные)
        psch = row.get('psch', np.nan)
        pscd = row.get('pscd', np.nan)
        psca = row.get('psca', np.nan)
        
        # Преимущество домашней команды будем добавлять к рейтингу домашней команды при расчете признаков, чтобы модель могла его учитывать
        home_advantage = 10  # Можно экспериментировать с этим значением
        
        feature_row = {
            # Форма команд
            # 'home_form_points': home_form['form_points'],
            # 'away_form_points': away_form['form_points'],
            # 'home_form_goals_scored': home_form['form_goals_scored'],
            # 'away_form_goals_scored': away_form['form_goals_scored'],
            # 'home_form_goals_conceded': home_form['form_goals_conceded'],
            # 'away_form_goals_conceded': away_form['form_goals_conceded'],
            # 'home_form_matches': home_form['form_matches_played'],
            # 'away_form_matches': away_form['form_matches_played'],
            # 'home_avg_form_points': home_form['avg_form_points'],
            # 'away_avg_form_points': away_form['avg_form_points'],
            
            # Общая статистика
            # 'home_total_points': home_stats['total_points'],
            # 'away_total_points': away_stats['total_points'],
            # 'home_total_goals_scored': home_stats['total_goals_scored'],
            # 'away_total_goals_scored': away_stats['total_goals_scored'],
            # 'home_total_goals_conceded': home_stats['total_goals_conceded'],
            # 'away_total_goals_conceded': away_stats['total_goals_conceded'],
            # 'home_matches_played': home_stats['total_matches'],
            # 'away_matches_played': away_stats['total_matches'],
            # 'home_avg_points': home_stats['avg_points_per_match'],
            # 'away_avg_points': away_stats['avg_points_per_match'],
            
            # Разница в форме и статистике
            # 'form_points_diff': home_form['form_points'] - away_form['form_points'],
            # 'avg_points_diff': home_stats['avg_points_per_match'] - away_stats['avg_points_per_match'],
            # 'goals_scored_diff': home_stats['total_goals_scored']/max(1, home_stats['total_matches']) - 
            #                     away_stats['total_goals_scored']/max(1, away_stats['total_matches']),
            # 'goals_conceded_diff': home_stats['total_goals_conceded']/max(1, home_stats['total_matches']) - 
            #                       away_stats['total_goals_conceded']/max(1, away_stats['total_matches']),
            
            # Преимущество домашней команды
            'glicko_home_rating': row['glicko_home_rating'] + home_advantage,
            'glicko_home_rd': row['glicko_home_rd'],
            'glicko_home_vol': row['glicko_home_vol'],
            'glicko_away_rating': row['glicko_away_rating'],
            'glicko_away_rd': row['glicko_away_rd'],
            'glicko_away_vol': row['glicko_away_vol'],
            
            # Букмекерские коэффициенты (если есть)
            'psch': psch,
            'pscd': pscd,
            'psca': psca,
            
            # Целевая переменная
            'target': row['result_encoded']
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


# # Разделение на признаки и целевую переменную
# X = features_df.drop('target', axis=1)
# y = features_df['target']

# # Масштабирование признаков
# scaler = StandardScaler()
# X_scaled = scaler.fit_transform(X)

def prepare_features(df):
    """
    Преобразует сырые данные в матрицу признаков для модели
    """
    
    # Создаем копию, чтобы не менять исходные данные
    data = df.copy()
    
    # Список признаков, которые будем использовать
    feature_columns = [
        # Glicko признаки хозяев (с уже добавленным home_advantage)
        'glicko_home_rating', 'glicko_home_rd', 'glicko_home_vol',
        
        # Glicko признаки гостей
        'glicko_away_rating', 'glicko_away_rd', 'glicko_away_vol',
        
        # Букмекерские вероятности (очищенные от маржи)
        'psch', 'pscd', 'psca'
    ]
    
    # Проверяем, что все колонки существуют
    missing_cols = [col for col in feature_columns if col not in data.columns]
    if missing_cols:
        print(f"Внимание! Отсутствуют колонки: {missing_cols}")
        feature_columns = [col for col in feature_columns if col in data.columns]
    
    # Создаем дополнительные признаки для улучшения модели
    # 1. Разница рейтингов (сила команды)
    data['rating_diff'] = data['glicko_home_rating'] - data['glicko_away_rating']
    
    # 2. Сумма рейтингов (общий уровень матча)
    data['rating_sum'] = data['glicko_home_rating'] + data['glicko_away_rating']
    
    # 3. Отношение рейтингов
    data['rating_ratio'] = data['glicko_home_rating'] / (data['glicko_away_rating'] + 1e-6)
    
    # 4. Уверенность в рейтингах
    data['home_rd_inv'] = 1 / (data['glicko_home_rd'] + 1e-6)
    data['away_rd_inv'] = 1 / (data['glicko_away_rd'] + 1e-6)
    
    # 5. Разница в уверенности
    data['rd_diff'] = data['glicko_home_rd'] - data['glicko_away_rd']
    
    # 6. Комбинация рейтинга и букмекера
    expected_home = 1 / (1 + 10**((data['glicko_away_rating'] - data['glicko_home_rating']) / 400))
    data['rating_vs_bookie'] = data['psch'] - expected_home
    
    # Добавляем новые признаки в список
    additional_features = [
        'rating_diff', 'rating_sum', 'rating_ratio',
        'home_rd_inv', 'away_rd_inv', 'rd_diff', 'rating_vs_bookie'
    ]
    
    feature_columns.extend(additional_features)
    
    # Целевая переменная
    target_column = 'target'
    
    print(f"Всего признаков: {len(feature_columns)}")
    print(f"Признаки: {feature_columns}")
    
    return data, feature_columns, target_column

# ============================================
# 2. ОБУЧЕНИЕ С STRATIFIED K-FOLD
# ============================================

def train_with_stratified_kfold(data, feature_columns, target_column, n_splits=5):
    """
    Обучает Random Forest со стратифицированной K-Fold кросс-валидацией
    """
    
    # Подготовка данных
    X = data[feature_columns].values
    y = data[target_column].values
    
    # Масштабирование признаков
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Стратифицированная K-Fold
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    # Базовая модель
    base_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=5,
        class_weight={
        0: 1.0,  # гости
        1: 2.0,  # ничья - удвоенный вес
        2: 0.8   # хозяева - чуть уменьшить
        },
        random_state=42,
        n_jobs=-1,
    )
    
    # Метрики для кросс-валидации
    scoring = {
        'accuracy': 'accuracy',
        'f1_macro': 'f1_macro',
        'f1_weighted': 'f1_weighted',
        'precision_macro': 'precision_macro',
        'recall_macro': 'recall_macro'
    }
    
    # Выполняем кросс-валидацию
    cv_results = cross_validate(
        base_model, 
        X_scaled, 
        y, 
        cv=skf, 
        scoring=scoring,
        return_train_score=True,
        return_estimator=True,
        n_jobs=-1
    )
    
    print("=" * 60)
    print(f"РЕЗУЛЬТАТЫ {n_splits}-FOLD СТРАТИФИЦИРОВАННОЙ КРОСС-ВАЛИДАЦИИ")
    print("=" * 60)
    
    # Выводим результаты по каждой метрике
    for metric in scoring.keys():
        train_scores = cv_results[f'train_{metric}']
        test_scores = cv_results[f'test_{metric}']
        
        print(f"\n{metric}:")
        print(f"  Train: {train_scores.mean():.4f} (±{train_scores.std()*2:.4f})")
        print(f"  Test:  {test_scores.mean():.4f} (±{test_scores.std()*2:.4f})")
        
        if metric == 'f1_macro':
            best_f1 = test_scores.mean()
    
    # Проверка на переобучение
    train_acc = cv_results['train_accuracy'].mean()
    test_acc = cv_results['test_accuracy'].mean()
    gap = train_acc - test_acc
    
    print(f"\n{'='*50}")
    print(f"Разрыв между train и test accuracy: {gap:.4f}")
    if gap > 0.1:
        print("⚠️  Сильное переобучение! Нужно сильнее ограничивать модель")
    elif gap > 0.05:
        print("⚠️  Умеренное переобучение, можно попробовать ужесточить параметры")
    else:
        print("✅ Переобучения нет или оно минимально")
    
    # Анализ важности признаков (усредненная по всем фолдам)
    feature_importance = np.mean([est.feature_importances_ for est in cv_results['estimator']], axis=0)
    importance_df = pd.DataFrame({
        'feature': feature_columns,
        'importance': feature_importance
    }).sort_values('importance', ascending=False)
    
    print("\nТОП-10 НАИБОЛЕЕ ВАЖНЫХ ПРИЗНАКОВ:")
    print(importance_df.head(10).to_string(index=False))
    
    corr_matrix = data[['glicko_away_rd', 'glicko_home_rd', 'away_rd_inv', 'home_rd_inv', 'rating_diff', 'rating_ratio',  
                  'glicko_home_rating', 'glicko_away_rating']].corr()

    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
    plt.title('Корреляция признаков')
    plt.show()
    return cv_results, importance_df, scaler

# ============================================
# 3. ПОДБОР ГИПЕРПАРАМЕТРОВ
# ============================================

def optimize_hyperparameters(data, feature_columns, target_column):
    """
    Подбирает оптимальные гиперпараметры Random Forest
    """
    
    X = data[feature_columns].values
    y = data[target_column].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Уменьшенная сетка для скорости
    param_grid = {
        'n_estimators': [50, 100],
        'max_depth': [5, 10, 15],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'class_weight': ['balanced', None, {0: 1.0, 1: 2.0, 2: 0.8}, {0: 1.0, 1: 1.5, 2: 0.8}]
    }
    
    rf = RandomForestClassifier(random_state=42, n_jobs=-1)
    
    # Стратифицированная кросс-валидация
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    
    grid_search = GridSearchCV(
        rf, param_grid, 
        cv=cv, 
        scoring='f1_macro',
        n_jobs=-1,
        verbose=1
    )
    
    print("Поиск оптимальных гиперпараметров...")
    grid_search.fit(X_scaled, y)
    
    print(f"Лучшие параметры: {grid_search.best_params_}")
    print(f"Лучший F1 macro: {grid_search.best_score_:.4f}")
    
    return grid_search.best_params_

# ============================================
# 4. ВИЗУАЛИЗАЦИЯ
# ============================================

def visualize_results(cv_results, importance_df, data, feature_columns, target_column):
    """
    Создает визуализации для анализа модели
    """
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. Сравнение train/test метрик
    ax1 = axes[0, 0]
    metrics = ['accuracy', 'f1_macro', 'f1_weighted']
    train_means = [cv_results[f'train_{m}'].mean() for m in metrics]
    test_means = [cv_results[f'test_{m}'].mean() for m in metrics]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax1.bar(x - width/2, train_means, width, label='Train', alpha=0.8)
    ax1.bar(x + width/2, test_means, width, label='Test', alpha=0.8)
    ax1.set_xlabel('Метрика')
    ax1.set_ylabel('Значение')
    ax1.set_title('Train vs Test метрики')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Важность признаков
    ax2 = axes[0, 1]
    top_features = importance_df.head(10)
    ax2.barh(range(len(top_features)), top_features['importance'].values)
    ax2.set_yticks(range(len(top_features)))
    ax2.set_yticklabels(top_features['feature'].values)
    ax2.set_xlabel('Важность')
    ax2.set_title('Топ-10 наиболее важных признаков')
    ax2.invert_yaxis()
    
    # 3. Распределение целевой переменной
    ax3 = axes[1, 0]
    target_dist = data[target_column].value_counts(normalize=True).sort_index()
    colors = ['red', 'yellow', 'green']
    ax3.bar(['Гости (0)', 'Ничья (1)', 'Хозяева (2)'], target_dist.values, color=colors, alpha=0.7)
    ax3.set_ylabel('Доля')
    ax3.set_title('Распределение исходов в данных')
    for i, v in enumerate(target_dist.values):
        ax3.text(i, v + 0.01, f'{v:.1%}', ha='center')
    
    # 4. Распределение accuracy по фолдам
    ax4 = axes[1, 1]
    ax4.boxplot([cv_results['test_accuracy']], labels=['Accuracy'])
    ax4.set_ylabel('Значение')
    ax4.set_title('Разброс accuracy по фолдам')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('model_analysis.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    print("\n📊 Графики сохранены в 'model_analysis.png'")

# ============================================
# 5. ФИНАЛЬНАЯ МОДЕЛЬ
# ============================================

def train_final_model(data, feature_columns, target_column, best_params=None):
    """
    Обучает финальную модель на всех данных
    """
    
    X = data[feature_columns].values
    y = data[target_column].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # if best_params is None:
    #     best_params = {
    #         'n_estimators': 100,
    #         'max_depth': 10,
    #         'min_samples_split': 5,
    #         'min_samples_leaf': 2,
    #         'class_weight': 'balanced'
    #     }
    
    final_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=1,
        class_weight={0: 1.0, 1: 2.0, 2: 0.8},
        random_state=42,
        n_jobs=-1
    )
    
    print("\n" + "=" * 60)
    print("ОБУЧЕНИЕ ФИНАЛЬНОЙ МОДЕЛИ НА ВСЕХ ДАННЫХ")
    print("=" * 60)
    print(f"Параметры: {best_params}")
    print(f"Размер обучающей выборки: {len(X)}")
    
    final_model.fit(X_scaled, y)
    
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': final_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\nТоп-5 признаков в финальной модели:")
    print(feature_importance.head(5).to_string(index=False))
    
    return final_model, scaler

# ============================================
# 6. ОЦЕНКА НА ОТЛОЖЕННОЙ ВЫБОРКЕ
# ============================================

def evaluate_on_holdout(data, feature_columns, target_column, test_size=0.2):
    """
    Дополнительная оценка на отложенной выборке
    """
    
    X = data[feature_columns].values
    y = data[target_column].values
    
    # Разбиение на обучение и тест
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=42
    )
    
    # Масштабирование
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    # МОЖНО ВЫПИЛИТЬ
#     results = []

#     weight_grid = [
#     # Около версии 2
#     {0: 1.0, 1: 1.5, 2: 0.8},  # версия 2
#     {0: 1.1, 1: 1.5, 2: 0.8},  # чуть больше гостей
#     {0: 1.0, 1: 1.6, 2: 0.8},  # чуть больше ничьих
#     {0: 1.0, 1: 1.5, 2: 0.7},  # чуть меньше хозяев
#     {0: 1.1, 1: 1.4, 2: 0.8},  # гости +, ничьи -
#     {0: 1.0, 1: 2.0, 2: 0.8},  # сильнее выделяем ничьи, МОЙ ВАРИАНТ
#     {0: 1.0, 1: 1.5, 2: 0.9},  # чуть меньше гостей
#     {0: 0.9, 1: 1.5, 2: 0.8},  # чуть меньше гостей
#     {0: 1.0, 1: 1.4, 2: 0.7},  # гости +, хозяева -
#     {0: 1.2, 1: 1.5, 2: 0.8},  # больше гостей
#     {0: 1.0, 1: 1.7, 2: 0.8},  # сильнее выделяем ничьи
#     {0: 1.3, 1: 1.5, 2: 0.8},  # еще больше гостей
#     {0: 1.0, 1: 1.5, 2: 0.6},   # еще меньше хозяев
#     ]

#     for weights in weight_grid:
#         mdl = RandomForestClassifier(
#             class_weight=weights,
#             random_state=42,
#             n_jobs=-1
#         )
#         # Кросс-валидация
#         scores = cross_val_score(mdl, X, y, cv=5, scoring='f1_macro')
#         results.append({
#             'weights': weights,
#             'f1_macro': scores.mean(),
#             'f1_std': scores.std()
#         })

# # Выберите лучший вариант
#     best_weights = max(results, key=lambda x: x['f1_macro'])
#     print(f"Лучшие веса: {best_weights['weights']}")
    

    # КОНЕЦ ВЫПИЛИВАНИЯ
    # Модель
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=1,
        class_weight={0: 1.0, 1: 2.0, 2: 0.8},
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Предсказания
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)
    
    # Метрики
    accuracy = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')
    f1_weighted = f1_score(y_test, y_pred, average='weighted')
    
    print("\n" + "=" * 60)
    print("ОЦЕНКА НА ОТЛОЖЕННОЙ ВЫБОРКЕ")
    print("=" * 60)
    print(f"Размер обучающей выборки: {len(X_train)}")
    print(f"Размер тестовой выборки: {len(X_test)}")
    print(f"\nAccuracy: {accuracy:.4f}")
    print(f"F1 macro: {f1_macro:.4f}")
    print(f"F1 weighted: {f1_weighted:.4f}")
    
    # Матрица ошибок
    cm = confusion_matrix(y_test, y_pred)
    print("\nМатрица ошибок:")
    print(cm)
    
    # Classification report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Гости', 'Ничья', 'Хозяева']))
    
    return model, scaler, y_test, y_pred, y_pred_proba

def weight_bookmaker_features(df, feature_columns, bookie_weight=0.3):
    """
    Применяет вес к букмекерским признакам
    """
    
    df_weighted = df.copy()
    
    bookie_features = ['psch', 'pscd', 'psca']
    bookie_features = [f for f in bookie_features if f in feature_columns]
    
    # Умножаем букмекерские признаки на вес (< 1.0)
    for col in bookie_features:
        df_weighted[col] = df_weighted[col] * bookie_weight
    
    # Усиливаем рейтинговые признаки (опционально)
    rating_features = ['glicko_home_rating', 'glicko_away_rating', 'rating_diff']
    rating_features = [f for f in rating_features if f in feature_columns]
    
    for col in rating_features:
        df_weighted[col] = df_weighted[col] * (2 - bookie_weight)  # ~1.7
    
    return df_weighted

features_df = create_features(df)
# Подготовка признаков
print("\n🔄 Подготовка признаков...")
data, feature_columns, target_column = prepare_features(features_df)

data = weight_bookmaker_features(data, feature_columns, bookie_weight=1)


# Подбор гиперпараметров (опционально)
# print("\n🔍 Подбор гиперпараметров...")
# best_params = optimize_hyperparameters(data, feature_columns, target_column)

# Кросс-валидация
print("\n📊 Запуск K-Fold кросс-валидации...")
cv_results, importance_df, scaler_cv = train_with_stratified_kfold(
    data, feature_columns, target_column, n_splits=5
)

# Визуализация
# print("\n📈 Создание визуализаций...")
visualize_results(cv_results, importance_df, data, feature_columns, target_column)

# Оценка на отложенной выборке
print("\n🔬 Дополнительная оценка...")
holdout_model, holdout_scaler, y_test, y_pred, y_proba = evaluate_on_holdout(
    data, feature_columns, target_column, test_size=0.2
)

# Финальная модель на всех данных
# print("\n🏁 Обучение финальной модели...")
# final_model, final_scaler = train_final_model(
#     data, feature_columns, target_column)

# Запаковываем в модель
# model_artifacts = {
#     'model': final_model,
#     'scaler': final_scaler,
#     'feature_columns': feature_columns,
#     'label_encoder': label_encoder,
#     'model_name': "random_forest",
# }

# # сохраняем артефакты с отметкой времени
# timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
# filepath = rf"D:\Programming\Score_predictor\Trained models\random_forest_{timestamp}.pkl"
# joblib.dump(model_artifacts, filepath)
# print(f"Model trained and saved {filepath}")
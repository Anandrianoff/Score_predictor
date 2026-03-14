# Третья версия случайного леса. 
# Список признаков: 'glicko_home_rating', 'glicko_home_rd', 'glicko_home_vol', 'glicko_away_rating', 'glicko_away_rd', 
# 'glicko_away_vol', 'psch', 'pscd', 'psca', 'rating_diff', 'rating_sum', 'rating_ratio', 'home_rd_inv', 'away_rd_inv', 
# 'rd_diff', 'rating_vs_bookie'
# Отличия от V2 подобраны пороги срабатывания для ничьи или победы гостей. Использует ThresholdRFClassifier
# Лучшие пороги: {0: np.float64(0.6000000000000002), 1: np.float64(0.5000000000000001), 2: np.float64(0.30000000000000004)}

from posixpath import join
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, precision_recall_curve, f1_score
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
import joblib
from ThresholdRFClassifier import ThresholdRFClassifier

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
        
        # Коэффициенты букмекеров (нормализованные)
        psch = row.get('psch', np.nan)
        pscd = row.get('pscd', np.nan)
        psca = row.get('psca', np.nan)
        
        # Преимущество домашней команды будем добавлять к рейтингу домашней команды при расчете признаков, чтобы модель могла его учитывать
        home_advantage = 10  # Можно экспериментировать с этим значением
        
        feature_row = {
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

def train_with_stratified_kfold(data, feature_columns, target_column, n_splits=5, best_thresholds=None):
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
    base_model = ThresholdRFClassifier(
        thresholds = best_thresholds,
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=1,
        class_weight={0: 1.0, 1: 2.0, 2: 0.8},
        random_state=42,
        n_jobs=-1)
    
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
    
    print(cv_results['test_accuracy'])

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
    # plt.show()
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

def train_final_model(data, feature_columns, target_column, best_thresholds, best_params=None):
    """
    Обучает финальную модель на всех данных
    """
    
    X = data[feature_columns].values
    y = data[target_column].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    final_model = ThresholdRFClassifier(
        thresholds=best_thresholds,
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
    print(f"Параметры thresholds: {best_thresholds}")
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

def evaluate_on_holdout(data, feature_columns, target_column, best_thresholds, test_size=0.2):
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

    # Модель
    model = ThresholdRFClassifier(
        thresholds=best_thresholds,
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

# ============================================
# НАХОДИМ ОПТИМАЛЬНЫЕ ПОРОГИ СРАБАТЫВАНИЙ ДЛЯ КЛАССОВ
# ============================================
def find_tresholds(data, feature_columns, target_column, test_size=0.2, strategy = 'f1'):
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

    # Базовая модель
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
    # 2. ПОЛУЧИМ вероятности 
    y_proba_test = model.predict_proba(X_test_scaled)
  
    best_f1_macro = 0
    best_thresholds = {}
    
    # Диапазон порогов
    thresholds_range = np.arange(0.1, 0.8, 0.05)  # 0.1 до 0.8
    
    # Ограничиваем перебор
    np.random.seed(42)
    random_combinations = []
    
    for _ in range(1000):
        t0 = np.random.choice(thresholds_range)
        t1 = np.random.choice(thresholds_range)
        t2 = np.random.choice(thresholds_range)
        random_combinations.append({0: t0, 1: t1, 2: t2})

    for thresholds in random_combinations:
        y_pred = predict_with_thresholds(y_proba_test, thresholds)
        f1_macro = f1_score(y_test, y_pred, average='macro')
        
        if f1_macro > best_f1_macro:
            best_f1_macro = f1_macro
            best_thresholds = thresholds.copy()
    print(f"\nЛучшие пороги: {best_thresholds} с F1 macro: {best_f1_macro:.4f}")


    predictor = ThresholdRFClassifier(best_thresholds)
    predictor.fit(X_train, y_train)
    y_pred_new = predictor.predict(X_test)
    cm = confusion_matrix(y_test, y_pred_new)
    print("\nМатрица ошибок:")
    print(cm)
    print(classification_report(y_test, y_pred_new))
    return best_thresholds

def predict_with_thresholds(y_proba, thresholds):
    """
    y_proba: вероятности [[P0, P1, P2], [P0, P1, P2], ...]
    thresholds: {0: порог_гостей, 1: порог_ничья, 2: порог_хозяева}
    
    Возвращает: [класс1, класс2, класс3, ...]
    """
    predictions = []
    
    for prob in y_proba:  # Для каждого матча
        candidates = []     # Список прошедших порог
        
        # Шаг 1: проверяем каждый класс
        for class_idx in range(3):
            if prob[class_idx] >= thresholds[class_idx]:
                candidates.append((class_idx, prob[class_idx]))
        
        # Шаг 2: логика выбора
        if candidates:
            # Берём класс с максимальной вероятностью среди прошедших
            best_class = max(candidates, key=lambda x: x[1])[0]
            predictions.append(best_class)
        else:
            # Fallback: обычный argmax
            predictions.append(np.argmax(prob))
    
    return np.array(predictions)

features_df = create_features(df)
# Подготовка признаков
print("\n🔄 Подготовка признаков...")
data, feature_columns, target_column = prepare_features(features_df)

# Оцениваем и ищем оптимальные пороги срабатывания
print('\n🔬 Смотрим пороги срабатывания классификатора...')
best_thresholds = find_tresholds(data, feature_columns, target_column, test_size=0.2)
print(type(best_thresholds))


# Подбор гиперпараметров (опционально)
# print("\n🔍 Подбор гиперпараметров...")
# best_params = optimize_hyperparameters(data, feature_columns, target_column)

# Кросс-валидация
# print("\n📊 Запуск K-Fold кросс-валидации...")
# cv_results, importance_df, scaler_cv = train_with_stratified_kfold(
#     data, feature_columns, target_column, n_splits=5, best_thresholds=best_thresholds
# )

# Визуализация
# print("\n📈 Создание визуализаций...")
# visualize_results(cv_results, importance_df, data, feature_columns, target_column)

# Оценка на отложенной выборке
# print("\n🔬 Дополнительная оценка...")
# holdout_model, holdout_scaler, y_test, y_pred, y_proba = evaluate_on_holdout(
#     data, feature_columns, target_column, test_size=0.2, best_thresholds=best_thresholds
# )

# Финальная модель на всех данных
print("\n🏁 Обучение финальной модели...")
final_model, final_scaler = train_final_model(
    data, feature_columns, target_column, best_thresholds=best_thresholds)

# Запаковываем в модель
model_artifacts = {
    'model': final_model,
    'scaler': final_scaler,
    'feature_columns': feature_columns,
    'label_encoder': label_encoder,
    'model_name': "random_forest_with_thresholds",
}

# # сохраняем артефакты с отметкой времени
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filepath = rf"D:\Programming\Score_predictor\Trained models\random_forest_with_thresholds_{timestamp}.pkl"
joblib.dump(model_artifacts, filepath)
print(f"Model trained and saved {filepath}")
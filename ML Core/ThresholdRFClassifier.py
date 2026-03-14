from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
import numpy as np

class ThresholdRFClassifier(BaseEstimator, ClassifierMixin):
    """
    Random Forest с индивидуальными порогами для каждого класса
    
    Parameters:
    -----------
    thresholds : dict
        Словарь {class_idx: threshold} с порогами для каждого класса
    n_estimators : int, default=100
        Количество деревьев
    max_depth : int, default=15
        Максимальная глубина деревьев
    min_samples_split : int, default=10
        Минимальное количество образцов для разделения узла
    min_samples_leaf : int, default=1
        Минимальное количество образцов в листе
    class_weight : dict, default={0: 1.0, 1: 2.0, 2: 0.8}
        Веса классов
    random_state : int, default=42
        Seed для воспроизводимости
    n_jobs : int, default=-1
        Количество параллельных задач
    """
    
    def __init__(self, thresholds={0: 0.6000000000000002, 1: 0.5000000000000001, 2: 0.30000000000000004}, n_estimators=100, max_depth=15, 
                 min_samples_split=10, min_samples_leaf=1, 
                 class_weight={0: 1.0, 1: 2.0, 2: 0.8}, 
                 random_state=42, n_jobs=-1):
        self.thresholds = thresholds
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.class_weight = class_weight
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.model = None
        
        self._validate_thresholds(thresholds)
    
    def _validate_thresholds(self, thresholds):
        """Проверка корректности порогов"""
        if not isinstance(thresholds, dict):
            raise ValueError("thresholds должен быть словарем")
        for k, v in thresholds.items():
            if not isinstance(k, (int, np.integer)):
                raise ValueError(f"Ключ {k} должен быть целым числом")
            if not isinstance(v, (int, float)) or v < 0 or v > 1:
                raise ValueError(f"Порог {v} для класса {k} должен быть числом от 0 до 1")
    
    def fit(self, X, y):
        """Обучение базовой модели"""
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            class_weight=self.class_weight,
            random_state=self.random_state,
            n_jobs=self.n_jobs
        )
        self.model.fit(X, y)
        
        self.classes_ = self.model.classes_
        self.n_features_in_ = X.shape[1]
        
        if hasattr(X, 'columns'):
            self.feature_names_in_ = np.array(X.columns)
        else:
            self.feature_names_in_ = None
            
        return self
    
    def predict(self, X):
        """Предсказание с порогами"""
        if self.model is None:
            raise ValueError("Модель не обучена! Вызовите fit() сначала.")
        
        y_proba = self.model.predict_proba(X)
        return self._apply_thresholds(y_proba)
    
    def predict_proba(self, X):
        """Вероятности (стандартные)"""
        if self.model is None:
            raise ValueError("Модель не обучена!")
        return self.model.predict_proba(X)
    
    def _apply_thresholds(self, y_proba):
        """Внутренняя логика порогов"""
        predictions = []
        n_classes = len(self.classes_)
        
        for prob in y_proba:
            # Ищем классы, прошедшие свой порог
            candidates = []
            for class_idx in range(n_classes):
                threshold = self.thresholds.get(class_idx, 0)
                if prob[class_idx] >= threshold:
                    candidates.append((class_idx, prob[class_idx]))
            
            if candidates:
                # Берём лучший среди прошедших порог
                best_class = max(candidates, key=lambda x: x[1])[0]
                predictions.append(best_class)
            else:
                # Fallback: argmax (никто не прошёл порог)
                predictions.append(np.argmax(prob))
        
        return np.array(predictions)
    
    def get_thresholds(self):
        """Вернуть текущие пороги"""
        return self.thresholds.copy()
    
    def set_thresholds(self, thresholds):
        """Изменить пороги без переобучения"""
        self._validate_thresholds(thresholds)
        self.thresholds = thresholds
    
    def get_params(self, deep=True):
        """Обязательный для sklearn!"""
        return {
            'thresholds': self.thresholds,
            'n_estimators': self.n_estimators,
            'max_depth': self.max_depth,
            'min_samples_split': self.min_samples_split,
            'min_samples_leaf': self.min_samples_leaf,
            'class_weight': self.class_weight,
            'random_state': self.random_state,
            'n_jobs': self.n_jobs
        }
    
    def set_params(self, **parameters):
        """Обязательный для sklearn!"""
        for parameter, value in parameters.items():
            if parameter == 'thresholds':
                self._validate_thresholds(value)
            setattr(self, parameter, value)
        return self
    
    @property
    def feature_importances_(self):
        """Важность признаков из RandomForest"""
        if self.model is None:
            raise ValueError("Модель не обучена!")
        return self.model.feature_importances_
    
    def __sklearn_is_fitted__(self):
        """Проверка, обучена ли модель"""
        return self.model is not None
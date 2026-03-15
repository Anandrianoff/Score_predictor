import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sister_dir = os.path.join(current_dir, 'app')
utils_dir = os.path.join(parent_dir, 'Utils')
data_manager_path = os.path.join(parent_dir, 'ML Core')
sys.path.append(sister_dir)
sys.path.append(utils_dir)
sys.path.append(data_manager_path)

from bacground_worker import update_games_info
from background_score_predictor import update_prediction
import ThresholdRFClassifier

update_prediction()


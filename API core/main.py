import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
ludobot_path = os.path.join(parent_dir, 'ludobot')
logic_for_channel_path = os.path.join(ludobot_path, 'app')
utils_dir = os.path.join(parent_dir, 'Utils')
data_manager_path = os.path.join(parent_dir, 'ML Core')
sys.path.append(logic_for_channel_path)
sys.path.append(utils_dir)
sys.path.append(data_manager_path)
print (logic_for_channel_path)
from bacground_worker import update_games_info
from background_score_predictor import update_prediction
from logic_for_channel import weekly_send, get_matches
import asyncio

asyncio.run(get_matches('2026-03-15'))


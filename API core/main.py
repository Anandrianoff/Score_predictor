import asyncio
import sys
from datetime import datetime
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from score_predictor.bootstrap import ensure_project_import_paths

ensure_project_import_paths()

from bacground_worker import update_games_info  # type: ignore[reportMissingImports]
from background_score_predictor import update_prediction  # type: ignore[reportMissingImports]
from logic_for_channel import make_bets_for_day, update_yesterday_bet_results, daily_send, weekly_send  # type: ignore[reportMissingImports]

year = datetime.now().year
date_from = f"{year}-03-10"
date_to = f"{year}-03-22"
now = "2026-03-23"

# 1) Refresh matches in the date window.
# update_games_info(date_from=now)

# # 2) Refresh predictions for whatever matches now exist in DB.
# update_prediction(now)

# # # 3) Place bets for today’s matches (same logic as the bot scheduler).
# asyncio.run(make_bets_for_day(now))

# # # 4) Update yesterday bets results(same logic as the bot scheduler).
# asyncio.run(update_yesterday_bet_results(now))

# # 5) Make report about today and yesterday matches (same logic as the bot scheduler).
# asyncio.run(daily_send(now))

# 6) Make report about today and yesterday matches (same logic as the bot scheduler).
asyncio.run(weekly_send(now))


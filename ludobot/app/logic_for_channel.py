import asyncio
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parents[2]
_src = _root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from score_predictor.bootstrap import ensure_project_import_paths

ensure_project_import_paths()

from api_models import BetResultsDTO, MatchesResponse  # type: ignore[reportMissingImports]
from create_bot import bot  # type: ignore[reportMissingImports]
from DataManager import (  # type: ignore[reportMissingImports]
    get_matches_by_date,
    get_bet_results_by_date,
)
import DataModels  # type: ignore[reportMissingImports]
from background_daily_bets_worker import (  # type: ignore[reportMissingImports]
    make_bets_for_date,
    update_bet_results_for_date,
)

logger = logging.getLogger(__name__)

load_dotenv()
CHANNEL_ID = os.getenv("CHANNEL_ID")
bet_size = 1000


def _as_date(d):
    """Accept str 'YYYY-MM-DD', datetime.date, or datetime.datetime."""
    if d is None:
        return date.today()
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    return date.today()


def _format_result(home_team_name, away_team_name, result):
    if result is None:
        return "None"
    if result == DataModels.MatchResult.home:
        return home_team_name
    if result == DataModels.MatchResult.draw:
        return "ничья"
    return away_team_name


async def make_bets_for_day(bets_date=None) -> None:
    bets_date = bets_date or date.today()
    await asyncio.to_thread(make_bets_for_date, bets_date, bet_size)


async def update_yesterday_bet_results(day_to_update=None) -> None:
    yesterday = day_to_update or date.today() - timedelta(days=1)
    await asyncio.to_thread(update_bet_results_for_date, yesterday)


async def form_and_send_daily_message(send_date=None) -> None:
    d = _as_date(send_date)
    yesterday = d - timedelta(days=1)
    today_matches = await get_matches(d)
    yesterday_matches = await get_matches(yesterday)

    message = ""
    if len(today_matches) > 0:
        message = f"📅 Список матчей на сегодня:\n"

        matches_count = 1
        for m in today_matches:
            # MatchesResponse items are DataManager.MatchDTO.
            if m.start_match is None:
                continue
            message += f"{matches_count}. {m.home_team_name_rus} — {m.away_team_name_rus} ({m.start_match:%H:%M})\n"
            message += f"Предполагаемый победитель: {_format_result(m.home_team_name_rus, m.away_team_name_rus, m.winner_predict)}\n"
            if m.odd is not None:
                message += f"Ставка {bet_size} с коэффициентом ({m.odd:.2f})\n\n"
            else:
                message += f"Ставка {bet_size} на {_format_result(m.home_team_name_rus, m.away_team_name_rus, m.winner_predict)}\n\n"
            matches_count += 1

    if len(yesterday_matches) > 0:
        message += f"🔙 Итоги вчерашних матчей:\n"
    
        matches_count = 1
        total_profit = 0
        total_spent = 0
        for m in yesterday_matches:
            if m.start_match is None:
                continue
            message += f"{matches_count}. {m.home_team_name_rus} — {m.away_team_name_rus}\n"
            if m.home_goals is not None and m.away_goals is not None:
                message += f"Счёт: {m.home_goals}:{m.away_goals}\n"
            profit = 0
            if m.winner_predict == m.winner_fact:
                message += f"Ставка зашла\n"
                # ЭТОТ ХАРДКОД НАДО ОБЯЗАТЕЛЬНО ПЕРЕДЕЛАТЬ
                if m.odd is not None:
                    profit = m.odd * bet_size
            else:
                message += f"Ставка не зашла\n"
            total_profit = total_profit + profit - bet_size
            total_spent += bet_size
            odd_s = f"{m.odd:.2f}" if m.odd is not None else "—"
            message += f"Выигрыш: {profit} (коэффициент {odd_s})\n\n"
            matches_count += 1
        if total_profit >= 0:
            message += f"✅ ИТОГ ДНЯ: прибыль {total_profit} (ROI {total_profit / total_spent:.2%})"
        else:
            message += f"❌ ИТОГ ДНЯ: убыток {-total_profit} (ROI {total_profit / total_spent:.2%})"

    message = message.strip()
    if message:
        await bot.send_message(CHANNEL_ID, message)


async def daily_send(send_date=None) -> None:
    # Side-effects (make bets / update yesterday) are scheduled in `ludobot/bot.py`.
    await form_and_send_daily_message(send_date=send_date or date.today())


async def get_matches(match_date):
    matches_result = get_matches_by_date(match_date)
    return matches_result.matches


### The old in-function make/update logic was moved to `Utils/background_daily_bets_worker.py`.
### Keeping message formatting only in this file.


async def weekly_send(week_date=None):
    today = week_date or date.today()
    start = _as_date(today) - timedelta(days=7)
    bets = get_bet_results_by_date(start, today)
    message = await build_weekly_stats(bets)
    if message:
        await bot.send_message(CHANNEL_ID, message)


async def build_weekly_stats(bets_result: BetResultsDTO):
    if bets_result.matches_count == 0:
        return None
    message = f"📊 Статистика ставок за прошедшую неделю:\n"
    message += f"Всего ставок: {bets_result.matches_count}\n"
    message += f"Угадано: {bets_result.guess_matches}\n"
    message += f"Не угадано: {bets_result.not_guess_matches}\n"
    message += f"Потрачено: {bets_result.bet_amount}\n"
    if bets_result.bet_profit >= 0:
        message += f"Прибыль: {bets_result.bet_profit} (ROI {bets_result.bet_profit / bets_result.bet_amount:.2%})"
    else:
        message += f"Убыток: {-bets_result.bet_profit} (ROI {bets_result.bet_profit / bets_result.bet_amount:.2%})"
    return message

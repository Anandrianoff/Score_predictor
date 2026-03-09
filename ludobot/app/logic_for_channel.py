import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
data_manager_path = os.path.join(root_dir, 'DataManager')
print (data_manager_path)
sys.path.append(data_manager_path)
sys.path.append(parent_dir)

from DataManager import get_matches_by_date, make_bet, update_bet_result_by_match_id
import DataModels
from api_models import MatchesResponse
from datetime import date, timedelta
from create_bot import bot
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()
CHANNEL_ID = os.getenv('CHANNEL_ID') # Замените на ID вашего канала
bet_size = 1000

async def daily_send():
    today_matches = await get_matches(date.today())
    today_matches_message = await make_bets(today_matches)
    yesterday_matches = await get_matches(date.today() - timedelta(days=1))
    yesterday_matches_message = await build_yesterday_matches_list(yesterday_matches)
    message =  today_matches_message + yesterday_matches_message
    message = message.strip()
    if message:
        await bot.send_message(CHANNEL_ID, message)


async def get_matches(match_date):
    matches_result = get_matches_by_date(match_date)
    return matches_result.matches


async def make_bets(matches):
    if not matches:
        return ''
    
    list_of_matches = f'Список матчей на сегодня:\n'
    for number, match in enumerate(matches):
        print(match.odd)
        make_bet(match.match_id, bet_size, match.winner_predict, match.odd)
        match_result = ''
        if match.winner_predict == DataModels.MatchResult.home:
            match_result = f'Предполагаемый победитель: {match.home_team_name_rus}'
        elif match.winner_predict == DataModels.MatchResult.away:
            match_result = f'Предполагаемый победитель: {match.away_team_name_rus}'
        else:
            match_result = 'Предполагаемый исход - ничья'
        list_of_matches += f'{number + 1}. {match.home_team_name_rus} VS {match.away_team_name_rus}. \n{match_result}\nДелаем ставку {bet_size} с коэффициентом {match.odd}\n\n'
    
    return list_of_matches


async def build_yesterday_matches_list(matches):
    if not matches:
        return ''
    day_profit = 0
    list_of_matches = f'\nИтоги вчерашних матчей:\n'
    for number, match in enumerate(matches):
        bet = update_bet_result_by_match_id(match.match_id, match.winner_fact)
        if bet:
            day_profit -= bet.bet_amount
            if match.winner_predict == match.winner_fact:
                bet_result = 'зашла'
                profit = bet.bet_amount * bet.bet_odds
                day_profit += profit
            else:
                bet_result = 'не зашла'
                profit = 0
            if match.winner_fact == DataModels.MatchResult.home:
                result = f"Победитель: {match.home_team_name_rus}"
            elif match.winner_fact == DataModels.MatchResult.away:
                result = f"Победитель: {match.away_team_name_rus}"
            else:
                result = f"Ничья"
            list_of_matches += f'{number + 1}. {match.home_team_name_rus} VS {match.away_team_name_rus}. {result}. Ставка {bet_result}, коэффициент: {bet.bet_odds}. Выигрыш: {profit}\n'
    list_of_matches += f'\nИтог дня: {"прибыль" if day_profit > 0 else "убыток"} {abs(day_profit)}'
    return list_of_matches
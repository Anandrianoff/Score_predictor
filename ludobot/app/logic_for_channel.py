from DataManager.DataManager import get_matches_by_date
from DataManager.api_models import MatchesResponse
from datetime import date, timedelta
from create_bot import bot
import os
from dotenv import load_dotenv

load_dotenv()
CHANNEL_ID = os.getenv('CHANNEL_ID')


async def daily_send():
    today_matches = get_matches(date.today())
    yesterday_matches = get_matches(date.today() - timedelta(days=1))
    all_matches = f'Предсказания на сегодня:\n{today_matches}\n\nИтоги вчерашних матчей:\n{yesterday_matches}'
    bot.send_message(CHANNEL_ID, all_matches)


async def get_matches():
    matches = get_matches_by_date(date.today())
    return matches


async def build_today_matches_list(matches: MatchesResponse):
    list_of_matches = ''
    if not matches:
        return 'Сегодня матчи отсутствуют'
    
    for number, match in enumerate(matches.matches):
        list_of_matches += f'{number}. {match.home_team_name_rus} VS {match.away_team_name_rus}. Предполагаемый победитель: {match.winner_predict}\n'
    
    return list_of_matches


async def build_yesterday_matches_list(matches: MatchesResponse):
    list_of_matches = ''
    if not matches:
        return 'Вчера матчей не было'
    
    for number, match in enumerate(matches.matches):
        list_of_matches += f'{number}. {match.home_team_name_rus} VS {match.away_team_name_rus}. Победитель: {match.winner_predict}\n'
    
    return list_of_matches
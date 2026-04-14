import os
import sys
import joblib
import numpy as np
from sqlalchemy import create_engine, text

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
data_manager_path = os.path.join(root_dir, 'DataManager')
sys.path.append(data_manager_path)
import api_models
from api_models import MatchesResponse
import DataModels
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime 
import requests
from datetime import timedelta
import logging
from dotenv import load_dotenv
from typing import Any, Optional

load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

db_path = f'postgresql+psycopg2://postgres:{DB_PASSWORD}@{DB_HOST}:5432/DbScore'
Base_url = "https://api.sstats.net"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
engine = create_engine(db_path)
Session = sessionmaker(engine)

def _parse_api_datetime(dt: Optional[str]) -> Optional[datetime]:
    if not dt:
        return None
    # API обычно отдаёт ISO8601 с 'Z'. В текущей логике проект сдвигает время на -1 час.
    parsed = datetime.fromisoformat(dt.replace("Z", "+00:00")) - timedelta(hours=1)
    return parsed

def _safe_get(dct: dict[str, Any], path: list[str]) -> Any:
    cur: Any = dct
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur

def _ensure_team(session: Session, team_obj: dict[str, Any]) -> Optional[DataModels.Team]:
    team_api_id = team_obj.get("id")
    team_name = team_obj.get("name") or team_obj.get("shortName") or ""
    if team_api_id is None:
        logger.warning(f"Команда без team_api_id (obj={team_obj})")
        return None

    existing = DataModels.get_team_by_api_id(session, team_api_id)
    if existing:
        return existing

    # Заполняем минимум, чтобы можно было создать матч.
    return DataModels.add_team(
        session=session,
        team_name=team_name or str(team_api_id),
        team_api_id=int(team_api_id),
        team_name_rus=team_name or str(team_api_id),
        team_name_model=team_name or str(team_api_id),
    )

def _apply_odds_to_match(match_to_update: DataModels.Match, match_response: dict[str, Any]) -> None:
    # Статус 2 значит, что матч не начался
    if match_response.get("odds") is None or match_response.get("status") != 2:
        return

    for odd in match_response.get("odds", []):
        if odd.get("marketId") != 1:
            continue
        for odd_outcome in odd.get("odds") or []:
            name = (odd_outcome.get("name") or "").lower()
            if name == "home":
                match_to_update.psch = odd_outcome.get("value")
            elif name == "draw":
                match_to_update.pscd = odd_outcome.get("value")
            elif name == "away":
                match_to_update.psca = odd_outcome.get("value")

def _apply_match_common_fields(match_to_update: DataModels.Match, match_response: dict[str, Any]) -> None:
    match_to_update.start_match = _parse_api_datetime(match_response.get("date"))
    match_to_update.home_goals = match_response.get("homeFTResult")
    match_to_update.away_goals = match_response.get("awayFTResult")
    _apply_odds_to_match(match_to_update, match_response)

    if (
        match_to_update.home_goals is not None
        and match_to_update.away_goals is not None
        and match_response.get("statusName") == "Finished"
    ):
        if match_to_update.away_goals > match_to_update.home_goals:
            match_to_update.winner = DataModels.MatchResult.away
        elif match_to_update.home_goals > match_to_update.away_goals:
            match_to_update.winner = DataModels.MatchResult.home
        else:
            match_to_update.winner = DataModels.MatchResult.draw

def _refresh_glicko(match_to_update: DataModels.Match) -> None:
    if not match_to_update.match_api_id:
        return
    request_glicko_url = Base_url + f"/Games/glicko/{match_to_update.match_api_id}"
    logger.info(f"Запрос к Glicko API: {request_glicko_url}")
    response_glicko = requests.get(request_glicko_url, timeout=30)
    glicko_json = response_glicko.json()
    logger.info(f"Ответ от Glicko API: {response_glicko.status_code}")
    if glicko_json.get("status") != "OK":
        return
    glicko_data = _safe_get(glicko_json, ["data", "glicko"]) or {}
    match_to_update.glicko_home_rating = glicko_data.get("homeRating")
    match_to_update.glicko_home_rd = glicko_data.get("homeRd")
    match_to_update.glicko_home_vol = glicko_data.get("homeVolatility")
    match_to_update.glicko_away_rating = glicko_data.get("awayRating")
    match_to_update.glicko_away_rd = glicko_data.get("awayRd")
    match_to_update.glicko_away_vol = glicko_data.get("awayVolatility")

def _fetch_game_by_id(match_api_id: int) -> Optional[dict[str, Any]]:
    url = Base_url + f"/Games/{match_api_id}"
    resp = requests.get(url, timeout=30)
    try:
        payload = resp.json()
    except Exception:
        logger.exception(f"Не удалось распарсить JSON (url={url}, status={resp.status_code})")
        return None
    if payload.get("status") != "OK":
        logger.warning(f"API вернул не OK для {url}: {payload.get('status')}")
        return None
    return payload.get("data")

def update_games_info(date_from=None, date_to=None):
    # Новая логика: на ежедневном обновлении работаем по match_api_id.
    # 1) Сначала запрашиваем реальные матчи на сегодня, обновляем существующие по match_api_id,
    #    а если матча нет в БД — добавляем.
    # 2) Затем берём оставшиеся матчи в БД "на сегодня" и по match_api_id подтягиваем им
    #    актуальную дату через /Games/{id} (исправляет неверные даты при выгрузке сезона).

    # Оставляем прежнее формирование окна дат по умолчанию: вчера -> завтра
    date_from = date_from or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_to = date_to or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    today = datetime.now().date()

    # По документации: GET /Games/list, параметры: LeagueId, From, To (регистр не обязателен,
    # но приводим к виду из OpenAPI, чтобы избежать несовместимостей).
    request_url = Base_url + f"/Games/list?LeagueId=235&From={date_from}&To={date_to}"
    response = requests.get(request_url, timeout=30)
    data = response.json()
    logger.info(f"Матчей для обновления: {data.get('count')} (запрос: {request_url})")
    if data.get("status") != "OK":
        logger.warning(f"API вернул не OK для списка матчей: {data.get('status')}")
        return

    updated_api_ids: set[int] = set()

    with Session() as session:
        for match_response in data.get("data", []):
            match_api_id = match_response.get("id")
            if match_api_id is None:
                continue
            try:
                match_api_id_int = int(match_api_id)
            except Exception:
                logger.warning(f"Некорректный match_api_id={match_api_id}")
                continue

            updated_api_ids.add(match_api_id_int)
            logger.info(
                f"Обновление/добавление матча: "
                f"{_safe_get(match_response, ['homeTeam', 'name'])} vs {_safe_get(match_response, ['awayTeam', 'name'])} "
                f"({match_response.get('date')}, api_id={match_api_id_int})"
            )

            match_to_update = DataModels.get_match_by_api_id(session, match_api_id_int)
            season = _safe_get(match_response, ["season", "year"])

            if match_to_update is None:
                home_team = _ensure_team(session, match_response.get("homeTeam") or {})
                away_team = _ensure_team(session, match_response.get("awayTeam") or {})
                if home_team is None or away_team is None:
                    logger.warning(f"Не удалось определить команды для матча api_id={match_api_id_int}")
                    continue

                match_to_update = DataModels.add_match(
                    session=session,
                    home_team_id=home_team.team_id,
                    away_team_id=away_team.team_id,
                    match_api_id=match_api_id_int,
                    start_match=_parse_api_datetime(match_response.get("date")) or datetime.now(),
                    season=str(season) if season is not None else None,
                )
                if match_to_update is None:
                    continue

            _apply_match_common_fields(match_to_update, match_response)
            if season is not None:
                match_to_update.season = str(season)

            _refresh_glicko(match_to_update)

            logger.info(
                f"match_id={match_to_update.match_id} api_id={match_to_update.match_api_id} "
                f"season={match_to_update.season} start_match={match_to_update.start_match} "
                f"psch={match_to_update.psch} pscd={match_to_update.pscd} psca={match_to_update.psca} "
                f"home_goals={match_to_update.home_goals} away_goals={match_to_update.away_goals} "
                f"winner={match_to_update.winner}"
            )
            session.commit()

        # Шаг 2: "оставшиеся" матчи на сегодня из БД — обновим им дату по match_api_id
        day_start = datetime.combine(today, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        db_matches_today = DataModels.get_matches_by_date(session, day_start, day_end)
        leftovers = [m for m in db_matches_today if m.match_api_id and int(m.match_api_id) not in updated_api_ids]

        if leftovers:
            logger.info(f"Оставшихся матчей на сегодня для коррекции даты: {len(leftovers)}")

        for m in leftovers:
            api_id = int(m.match_api_id)
            details = _fetch_game_by_id(api_id)
            if not details:
                continue
            new_start = _parse_api_datetime(details.get("date"))
            if new_start:
                logger.info(
                    f"Коррекция даты матча match_id={m.match_id} api_id={api_id}: {m.start_match} -> {new_start}"
                )
                m.start_match = new_start
                session.commit()

    return


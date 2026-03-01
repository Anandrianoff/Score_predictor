import enum
from datetime import datetime, timedelta 
from typing import Optional
from psycopg2 import IntegrityError
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy import Column, DateTime, Enum, Float, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    sessionmaker,
    mapped_column,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
	pass

class Team(Base):
    __tablename__ = 'teams'
    
    # Позже можно будет добавить поля, хранящие форму команд и другие данные для рассчета вероятности победы
    team_id: Mapped[int] = mapped_column(primary_key=True)
    team_name: Mapped[str] = mapped_column(String)  # По умолчанию nullable=False
    team_name_rus: Mapped[str] = mapped_column(String) 
    team_name_model: Mapped[str] = mapped_column(String) # название команды в датасете
    team_api_id: Mapped[Optional[int]]

class MatchResult(enum.Enum):
    home = "h"
    away = "a"
    draw = "d"

class Match(Base):
    __tablename__ = 'matches'
    
    match_id: Mapped[int] = mapped_column(primary_key=True)
    home_team: Mapped[int] = mapped_column(ForeignKey('teams.team_id'))
    away_team: Mapped[int] = mapped_column(ForeignKey('teams.team_id'))
    season: Mapped[Optional[str]] = mapped_column(String)  # NULL разрешен, если сезон может быть неизвестен
    start_match: Mapped[Optional[datetime]]  # DateTime выводится из аннотации
    home_goals: Mapped[Optional[int]]
    away_goals: Mapped[Optional[int]]
    winner: Mapped[Optional[MatchResult]]  # Используем enum
    psch: Mapped[Optional[float]]  # коэффициент на победу home
    pscd: Mapped[Optional[float]]  # коэффициент на ничью
    psca: Mapped[Optional[float]]
    predicted_score: Mapped[Optional[MatchResult]]

def add_team(
    session: Session,
    team_name: str,
    team_api_id: Optional[int] = None
) -> Optional[Team]:
    """
    Добавляет новую команду в базу данных.
    
    Args:
        session: Сессия SQLAlchemy
        team_name: Название команды (обязательно)
        team_api_id: ID команды из API (опционально)
    
    Returns:
        Объект Team или None в случае ошибки
    """
    try:
        # Проверяем, существует ли уже такая команда
        existing_team = session.query(Team).filter(
            Team.team_name == team_name
        ).first()
        
        if existing_team:
            logger.warning(f"Команда '{team_name}' уже существует с ID {existing_team.team_id}")
            return existing_team
        
        # Создаем новую команду
        new_team = Team(
            team_name=team_name,
            team_api_id=team_api_id
        )
        
        session.add(new_team)
        session.commit()
        logger.info(f"✅ Команда '{team_name}' успешно добавлена с ID {new_team.team_id}")
        
        return new_team
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Ошибка целостности данных при добавлении команды '{team_name}': {e}")
        return None
    except Exception as e:
        session.rollback()
        logger.error(f"Неожиданная ошибка при добавлении команды '{team_name}': {e}")
        return None
    
# Функция для добавления нового матча
def add_match(
    session: Session,
    home_team_id: int,
    away_team_id: int,
    start_match: Optional[datetime] = None,
    season: Optional[str] = None,
    home_goals: Optional[int] = None,
    away_goals: Optional[int] = None,
    psch: Optional[float] = None,  # коэффициент на победу home
    pscd: Optional[float] = None,  # коэффициент на ничью
    psca: Optional[float] = None,  # коэффициент на победу away
    winner: Optional[MatchResult] = None
) -> Optional[Match]:
    """
    Добавляет новый матч в базу данных.
    
    Args:
        session: Сессия SQLAlchemy
        home_team_id: ID домашней команды
        away_team_id: ID гостевой команды
        start_match: Дата и время начала матча
        season: Сезон (например, "2023/2024")
        home_goals: Количество голов домашней команды
        away_goals: Количество голов гостевой команды
        psch: Коэффициент на победу home (PSC Home)
        pscd: Коэффициент на ничью (PSC Draw)
        psca: Коэффициент на победу away (PSC Away)
        winner: Результат матча (home/away/draw)
    
    Returns:
        Объект Match или None в случае ошибки
    """
    try:
        # Проверяем существование команд
        home_team = session.get(Team, home_team_id)
        away_team = session.get(Team, away_team_id)
        
        if not home_team:
            logger.error(f"Домашняя команда с ID {home_team_id} не найдена")
            return None
        
        if not away_team:
            logger.error(f"Гостевая команда с ID {away_team_id} не найдена")
            return None
        
        # Если указаны голы, но не указан победитель - определяем автоматически
        if home_goals is not None and away_goals is not None and winner is None:
            if home_goals > away_goals:
                winner = MatchResult.home
            elif home_goals < away_goals:
                winner = MatchResult.away
            else:
                winner = MatchResult.draw
        
        # Создаем новый матч
        new_match = Match(
            home_team=home_team_id,
            away_team=away_team_id,
            start_match=start_match or datetime.now(),
            season=season,
            home_goals=home_goals,
            away_goals=away_goals,
            winner=winner,
            psch=psch,
            pscd=pscd,
            psca=psca
        )
        
        session.add(new_match)
        session.commit()
        
        logger.info(
            f"✅ Матч #{new_match.match_id} добавлен: "
            f"{home_team.team_name} vs {away_team.team_name} "
            f"({home_goals or '?'}:{away_goals or '?'})"
        )
        
        return new_match
        
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Ошибка целостности данных при добавлении матча: {e}")
        return None
    except Exception as e:
        session.rollback()
        logger.error(f"Неожиданная ошибка при добавлении матча: {e}")
        return None
    
def get_team_by_api_id(session: Session, team_api_id: str) -> Optional[Team]:
    """
    Получает команду по её API ID.
    
    Args:
        session: Сессия SQLAlchemy
        team_api_id: ID команды из API
    
    Returns:
        Объект Team или None, если команда не найдена
    """
    try:
        logger.info(f"Поиск команды с API ID '{team_api_id}'")
        team = session.query(Team).filter(Team.team_api_id == team_api_id).first()
        if team:
            logger.info(f"Команда с API ID '{team_api_id}' найдена: {team.team_name} (ID {team.team_id})")
        else:
            logger.warning(f"Команда с API ID '{team_api_id}' не найдена")
        return team
    except Exception as e:
        logger.error(f"Ошибка при получении команды по API ID '{team_api_id}': {e}")
        return None
    
def get_matches_by_date(session: Session, date: datetime) -> list[Match]:
    """
     Получает матчи за указанный день.
     
     Args:
        session: Сессия SQLAlchemy
        date: Дата для поиска матчей
        
    Returns:
        Список объектов Match за указанный день
    """
    try:
        end_date = date + timedelta(days=1)
        matches = session.query(Match).filter(
            Match.start_match >= date,
            Match.start_match < end_date
        ).order_by(Match.start_match).all()
            
        logger.info(f"Найдено {len(matches)} матчей с {date} по {end_date}")
        print(matches)
        return matches
    except Exception as e:
        logger.error(f"Ошибка при получении матчей за период: {e}")
        return [] 
    
def get_team_by_id(session: Session, team_id: int) -> Optional[Team]:
    """
    Получает команду по её ID.
    
    Args:
        session: Сессия SQLAlchemy
        team_id: ID команды
    
    Returns:
        Объект Team или None, если команда не найдена
    """
    try:
        team = session.get(Team, team_id)
        if team:
            logger.info(f"Команда с ID {team_id} найдена: {team.team_name}")
        else:
            logger.warning(f"Команда с ID {team_id} не найдена")
        return team
    except Exception as e:
        logger.error(f"Ошибка при получении команды с ID {team_id}: {e}")
        return None
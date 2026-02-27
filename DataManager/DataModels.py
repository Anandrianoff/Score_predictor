import enum

from sqlalchemy import Column, DateTime, Enum, Float, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
	pass

class Team(Base):
    __tablename__ = 'teams'
    
    #Позже можно будет добавить поля, хранящие форму команд и другие данные для рассчета вероятности победы
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    team_api_id = Column(String) # идентификатор команды из API, если он есть

class MatchResult(enum.Enum):
    home = "h"
    away = "a"
    draw = "d"

class Match(Base):
    __tablename__ = 'matches'
        
    match_id = Column(Integer, primary_key=True)
    home_team = Column(Integer, ForeignKey('teams.team_id'))
    away_team = Column(Integer, ForeignKey('teams.team_id'))
    season = Column(String)
    start_match = Column(DateTime)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    winner = Column(Enum(MatchResult))
    psch = Column(Float)
    pscd = Column(Float)
    psca = Column(Float)
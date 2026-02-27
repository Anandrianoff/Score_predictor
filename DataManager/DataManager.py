import sys
from sqlalchemy import create_engine
sys.path.append(r'D:\Programming\Score_predictor')
from DataModels import Base, Team, Match
from sqlalchemy.orm import sessionmaker
import psycopg2

# db_path = 'postgresql://postgres:1234@localhost:5432/scorepredictordb'
db_path = 'postgresql+psycopg2://postgres:1234@localhost:5432/scorepredictordb'
# engine = create_engine(db_path, echo=True)



try:
    engine = create_engine(db_path)
    Session = sessionmaker(engine)
except Exception as e:
    print(f"Не удалось подключиться к бд в sync_models.py: {e}")

with Session() as session:
    Base.metadata.create_all(engine)
    

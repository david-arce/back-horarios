from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:aHLTwsOgDEdLpisQSnmUBpPgIyuvAPQG@metro.proxy.rlwy.net:40243/railway")

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base() 
# Dependencia para inyectar la sesión a FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

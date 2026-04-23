import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

def get_database_url():
    url = os.getenv("DATABASE_URL", "")
    # pg8000 needs postgresql+pg8000:// instead of postgresql://
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+pg8000://", 1)
    return url

engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

def get_database_url():
    url = os.getenv("DATABASE_URL", "")
    # pg8000 uses postgresql+pg8000:// and handles SSL via connect_args
    if "postgresql://" in url and "+pg8000" not in url:
        url = url.replace("postgresql://", "postgresql+pg8000://", 1)
    # Remove ?sslmode=require from URL - we pass SSL via connect_args instead
    if "?sslmode=require" in url:
        url = url.replace("?sslmode=require", "")
    return url

engine = create_engine(
    get_database_url(),
    connect_args={
        "ssl_context": True   # pg8000 uses ssl_context instead of sslmode
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
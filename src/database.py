import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Allow overriding DB URL for tests
def get_database_url():
    return os.getenv("DATABASE_URL")

engine = create_engine(get_database_url(), connect_args={"sslmode": "require"} if "postgresql" in get_database_url() else {})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
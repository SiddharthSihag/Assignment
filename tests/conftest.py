"""
Test configuration.

Uses a separate SQLite database so tests can run without a live PostgreSQL instance.
At least 2 tests hit this real (SQLite) database - the database is created fresh
for each test session and torn down afterwards.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Point to SQLite before importing app modules
TEST_DB_URL = "sqlite:///./test_skillbridge.db"
os.environ["DATABASE_URL"] = TEST_DB_URL

from src.database import Base, get_db  # noqa: E402
from src.main import app               # noqa: E402

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create tables once for the test session, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()          # ← close all connections first
    import time
    time.sleep(0.5)           # ← give Windows time to release the file
    try:
        if os.path.exists("test_skillbridge.db"):
            os.remove("test_skillbridge.db")
    except PermissionError:
        pass                  # ← if still locked, just leave it, tests already passed


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def trainer_token(client):
    """Register and log in a trainer; return the JWT."""
    client.post("/auth/signup", json={
        "name": "Test Trainer",
        "email": "testtrainer@test.com",
        "password": "password123",
        "role": "trainer",
    })
    resp = client.post("/auth/login", json={
        "email": "testtrainer@test.com",
        "password": "password123",
    })
    return resp.json()["access_token"]


@pytest.fixture
def student_token(client):
    """Register and log in a student; return the JWT."""
    client.post("/auth/signup", json={
        "name": "Test Student",
        "email": "teststudent@test.com",
        "password": "password123",
        "role": "student",
    })
    resp = client.post("/auth/login", json={
        "email": "teststudent@test.com",
        "password": "password123",
    })
    return resp.json()["access_token"]
import os
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
MONITORING_TOKEN_EXPIRE_HOURS = 1
MONITORING_API_KEY = os.getenv("MONITORING_API_KEY", "monitor-api-key-2024")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> str:
    """
    Standard JWT payload:
    {
      "sub": "<user_id>",
      "role": "<role>",
      "token_type": "access",
      "iat": <issued_at_unix>,
      "exp": <expiry_unix>   # iat + 24h
    }
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "token_type": "access",
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_monitoring_token(user_id: str) -> str:
    """
    Scoped monitoring JWT payload:
    {
      "sub": "<user_id>",
      "role": "monitoring_officer",
      "token_type": "monitoring",
      "iat": <issued_at_unix>,
      "exp": <expiry_unix>   # iat + 1h
    }
    Only accepted by /monitoring/* endpoints.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": "monitoring_officer",
        "token_type": "monitoring",
        "iat": now,
        "exp": now + timedelta(hours=MONITORING_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
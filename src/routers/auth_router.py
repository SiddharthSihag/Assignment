from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.auth import (
    hash_password, verify_password,
    create_access_token, create_monitoring_token,
    MONITORING_API_KEY,
)
from src.database import get_db
from src.dependencies import get_current_user
from src.models import User
from src.schemas import SignupRequest, LoginRequest, TokenResponse, MonitoringTokenRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user and return a JWT."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        institution_id=body.institution_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return a signed JWT."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token)


@router.post("/monitoring-token", response_model=TokenResponse)
def monitoring_token(
    body: MonitoringTokenRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Exchange a valid Monitoring Officer JWT + API key for a short-lived
    scoped monitoring token (1 hour, read-only).

    Requires:
    - Authorization: Bearer <standard_login_token>
    - Body: { "key": "<MONITORING_API_KEY>" }
    """
    if current_user.role != "monitoring_officer":
        raise HTTPException(status_code=403, detail="Only Monitoring Officers can request a monitoring token.")

    if body.key != MONITORING_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    token = create_monitoring_token(current_user.id)
    return TokenResponse(access_token=token)
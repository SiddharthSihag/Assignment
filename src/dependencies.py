import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.auth import decode_token
from src.database import get_db
from src.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Extract and decode any bearer token. Returns 401 if missing or invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token.",
        )
    try:
        return decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the JWT sub claim to a User row."""
    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def require_roles(*allowed_roles: str):
    """
    Factory that returns a FastAPI dependency enforcing role membership.
    Usage: current_user: User = Depends(require_roles("trainer", "institution"))
    """
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}.",
            )
        return user
    return _check


def get_monitoring_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Stricter dependency for /monitoring/* endpoints.
    Requires token_type == "monitoring" in the JWT payload.
    A standard access token is explicitly rejected.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Monitoring token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    if payload.get("token_type") != "monitoring":
        raise HTTPException(
            status_code=401,
            detail="This endpoint requires a monitoring-scoped token. "
                   "Use POST /auth/monitoring-token to obtain one.",
        )
    if payload.get("role") != "monitoring_officer":
        raise HTTPException(status_code=403, detail="Access denied.")

    user = db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user
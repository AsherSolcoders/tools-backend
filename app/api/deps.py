"""Shared API dependencies — admin authentication."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login", auto_error=False)


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {"sub": str(user.id), "email": user.email, "role": user.role.value, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_admin(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    creds_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise creds_error
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise creds_error
    user = db.get(User, user_id)
    if not user:
        raise creds_error
    return user


def _require_roles(*allowed: str):
    """Dependency factory: allow only the given roles, else 403."""
    def guard(user: User = Depends(get_current_admin)) -> User:
        if user.role.value not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user
    return guard


# super_admin + admin may manage users and delete content; editors cannot.
require_admin = _require_roles("super_admin", "admin")
# Only the super_admin (ENV account) may touch site-wide code / analytics injection.
require_super_admin = _require_roles("super_admin")

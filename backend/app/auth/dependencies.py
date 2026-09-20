"""
JWT authentication dependencies for FastAPI.

Supports multiple auth providers (local JWT, Firebase, Supabase)
configured via AUTH_PROVIDER env var. For this scaffold, the 'local'
provider is fully implemented; Firebase/Supabase hooks are extensible.
"""

from __future__ import annotations

import enum
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel

from app.config import get_settings

security = HTTPBearer(auto_error=False)


class UserRole(str, enum.Enum):
    """Role-based access control roles."""
    CLIENT = "client"
    LAWYER = "lawyer"
    ADMIN = "admin"


class TokenPayload(BaseModel):
    """Decoded JWT token claims."""
    sub: str  # user ID
    email: str | None = None
    role: UserRole = UserRole.CLIENT
    exp: datetime | None = None


def create_access_token(
    user_id: str,
    email: str | None = None,
    role: UserRole = UserRole.CLIENT,
) -> str:
    """Create a signed JWT access token (for the local auth provider)."""
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "exp": expires,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(
            sub=payload["sub"],
            email=payload.get("email"),
            role=UserRole(payload.get("role", "client")),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            if "exp" in payload
            else None,
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenPayload:
    """
    FastAPI dependency — extracts and validates the JWT from the
    Authorization header. Returns the decoded token payload.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


def require_role(*roles: UserRole):
    """
    Dependency factory — restricts access to specific roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """

    async def _check_role(
        user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in roles]}",
            )
        return user

    return _check_role

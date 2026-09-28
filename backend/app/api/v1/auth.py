"""
Authentication API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.auth.password import verify_password
from app.auth.dependencies import create_access_token, get_current_user, TokenPayload, UserRole
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in user",
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email/password and return JWT token."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(data.email)
    
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        token_version=user.token_version,
    )
    logger.info("User logged in successfully", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account."""
    user_repo = UserRepository(db)
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Self-registration is strictly server-enforced to UserRole.LAWYER.
    # Client cannot specify or escalate role via self-registration.
    user = await user_repo.create_user(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role=UserRole.LAWYER,
        firm=data.firm,
        bar_number=data.bar_number,
    )
    await db.commit()
    logger.info("User registered successfully", user_id=str(user.id), email=user.email, role=user.role.value)
    return UserResponse.model_validate(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current logged in user profile",
)
async def get_me(
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Fetch current user profile using JWT token."""
    import uuid
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(current_user.sub))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out user",
)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Logout endpoint — revokes all active tokens by incrementing user token_version."""
    import uuid
    from sqlalchemy import update
    from app.models.user import User

    user_uuid = uuid.UUID(current_user.sub)
    await db.execute(
        update(User)
        .where(User.id == user_uuid)
        .values(token_version=User.token_version + 1)
    )
    await db.commit()
    logger.info("User logged out, token_version incremented", user_id=current_user.sub)
    return {"status": "success", "message": "Logged out successfully"}

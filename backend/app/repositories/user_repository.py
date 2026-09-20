"""
User repository for database operations.
"""

from __future__ import annotations

import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.auth.dependencies import UserRole
from app.auth.password import hash_password
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access layer for User entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by unique email address."""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.LAWYER,
        firm: str | None = None,
        bar_number: str | None = None,
    ) -> User:
        """Create and persist a new user."""
        hashed = hash_password(password)
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed,
            full_name=full_name,
            role=role,
            firm=firm,
            bar_number=bar_number,
        )
        self._session.add(user)
        await self._session.flush()
        return user

"""
User ORM Model for Authentication and Role Management.
"""

from __future__ import annotations

import enum
from sqlalchemy import String, Boolean, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.auth.dependencies import UserRole


class User(Base):
    """User account model for authentication and access control."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_constraint=True, native_enum=False, length=50),
        default=UserRole.LAWYER,
        server_default=UserRole.LAWYER.value,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    firm: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bar_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' role={self.role.value}>"

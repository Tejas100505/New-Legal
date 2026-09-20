"""
Pydantic schemas for authentication and user accounts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.dependencies import UserRole


class LoginRequest(BaseModel):
    """User login request body."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """User registration request body. Role is strictly server-enforced and cannot be set by client."""
    email: EmailStr
    password: str = Field(...)
    full_name: str = Field(..., min_length=1)
    firm: str | None = None
    bar_number: str | None = None

    model_config = {"extra": "ignore"}

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce strong password policy on registration:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (non-alphanumeric)
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(not c.isalnum() for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserResponse(BaseModel):
    """User profile response."""
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    firm: str | None = None
    bar_number: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT Token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

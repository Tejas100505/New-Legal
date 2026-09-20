"""
Case request/response schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.case import CaseStatus, CasePriority


class CaseCreate(BaseModel):
    """Request body for creating a new case."""
    name: str = Field(..., min_length=1, max_length=500, description="Case name")
    case_number: str | None = Field(None, description="Case tracking number")
    description: str | None = Field(None, description="Optional case description")
    priority: CasePriority = Field(CasePriority.MEDIUM, description="Priority level")
    tags: list[str] | dict | None = Field(default_factory=list, description="Associated tags")


class CaseUpdate(BaseModel):
    """Request body for updating a case."""
    name: str | None = Field(None, min_length=1, max_length=500)
    case_number: str | None = None
    description: str | None = None
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    tags: list[str] | dict | None = None


class CaseResponse(BaseModel):
    """Single case in API responses."""
    id: uuid.UUID
    name: str
    case_number: str | None = None
    description: str | None = None
    status: CaseStatus
    priority: CasePriority = CasePriority.MEDIUM
    tags: list[str] | dict | None = None
    created_by: str | None = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    """Paginated list of cases."""
    cases: list[CaseResponse]
    total: int
    page: int = 1
    page_size: int = 20

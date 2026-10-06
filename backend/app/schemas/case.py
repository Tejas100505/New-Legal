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
    case_number: str | None = Field(None, max_length=100, description="Case or docket tracking number")
    matter_number: str | None = Field(None, max_length=100, description="Internal matter tracking number")
    client: str | None = Field(None, max_length=255, description="Client or organization name")
    case_type: str | None = Field(None, max_length=100, description="Type of case / practice area")
    description: str | None = Field(None, description="Optional case description")
    priority: CasePriority = Field(CasePriority.MEDIUM, description="Priority level")
    tags: list[str] | dict | None = Field(default_factory=list, description="Associated tags")
    is_system_fixture: bool = Field(False, description="Whether this case is an internal system/integration test fixture")


class CaseUpdate(BaseModel):
    """Request body for updating a case."""
    name: str | None = Field(None, min_length=1, max_length=500)
    case_number: str | None = None
    matter_number: str | None = None
    client: str | None = None
    case_type: str | None = None
    description: str | None = None
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    tags: list[str] | dict | None = None
    is_system_fixture: bool | None = None


class CaseResponse(BaseModel):
    """Single case in API responses with real telemetry."""
    id: uuid.UUID
    name: str
    case_number: str | None = None
    matter_number: str | None = None
    client: str | None = None
    case_type: str | None = None
    description: str | None = None
    status: CaseStatus
    priority: CasePriority = CasePriority.MEDIUM
    tags: list[str] | dict | None = None
    created_by: str | None = None
    is_system_fixture: bool = False
    document_count: int = 0
    reviewed_count: int = 0
    flagged_count: int = 0
    privileged_count: int = 0
    high_risk_count: int = 0
    processing_count: int = 0
    last_activity: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    """Paginated list of cases."""
    cases: list[CaseResponse]
    total: int
    page: int = 1
    page_size: int = 20

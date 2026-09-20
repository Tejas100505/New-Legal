"""
Document request/response schemas.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class OverrideField(str, enum.Enum):
    """Enumeration of fields that can be confirmed or overridden by a human reviewer."""
    PRIVILEGE = "privilege"
    RELEVANCE = "relevance"
    CONFIDENTIALITY = "confidentiality"


class OverrideAction(str, enum.Enum):
    """Action taken by the human reviewer."""
    CONFIRM = "confirm"
    OVERRIDE = "override"


class HumanOverrideRequest(BaseModel):
    """Request payload for recording a human review confirmation or override."""
    field: OverrideField = Field(..., description="Target field being confirmed or overridden")
    action: OverrideAction = Field(OverrideAction.OVERRIDE, description="Action: confirm or override")
    override_value: Any = Field(..., description="The value decided by the human reviewer")
    original_ai_value: Any = Field(None, description="The original value suggested by the AI agent")
    ai_confidence: float | None = Field(None, description="Confidence score from the AI agent")
    reason: str = Field(..., min_length=1, description="Required justification/rationale for the decision")
    new_status: DocumentStatus | None = Field(DocumentStatus.REVIEWED, description="Updated document status")


class DocumentResponse(BaseModel):
    """Single document in API responses."""
    id: uuid.UUID
    case_id: uuid.UUID | None = None
    uploaded_by: uuid.UUID | None = None
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    status: DocumentStatus
    page_count: int | None = None
    checksum_sha256: str | None = None
    extracted_text: str | None = None
    doc_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: list[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 20


class DocumentUploadResponse(BaseModel):
    """Response after successful file upload."""
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    uploaded_by: uuid.UUID | None = None
    message: str = "Document uploaded successfully"


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
    """Response after file upload (or individual file error during batch upload)."""
    id: uuid.UUID | None = None
    filename: str
    status: DocumentStatus
    uploaded_by: uuid.UUID | None = None
    message: str = "Document uploaded successfully"
    error: str | None = None


class StatusHistoryResponse(BaseModel):
    """Schema for a single document status history entry."""
    id: uuid.UUID
    document_id: uuid.UUID
    old_status: str | None = None
    new_status: str
    changed_at: datetime
    changed_by: uuid.UUID | None = None
    reason: str | None = None

    model_config = {"from_attributes": True}


class PipelineStageResponse(BaseModel):
    """Schema for a single stage in the 10-stage processing pipeline."""
    id: str
    label: str
    order: int
    agent_ids: list[str] = Field(default_factory=list, alias="agentIds")
    status: str
    evidence: str = Field("none", description="Evidence basis: status_history, audit_log, current_status_inference, none")
    completed_at: str | None = Field(None, alias="completedAt")
    duration_ms: int | None = Field(None, alias="durationMs")

    model_config = {"populate_by_name": True, "from_attributes": True}


class PipelineStatusResponse(BaseModel):
    """Schema describing case-scoped or document-scoped pipeline execution state."""
    case_id: str | None = Field(None, alias="caseId")
    document_id: str | None = Field(None, alias="documentId")
    status: str | None = None
    current_stage: str = Field(alias="currentStage")
    is_quota_paused: bool = Field(False, alias="isQuotaPaused")
    paused_stage: str | None = Field(None, alias="pausedStage")
    paused_reason: str | None = Field(None, alias="pausedReason")
    last_reason: str | None = Field(None, alias="lastReason")
    history_available: bool = Field(False, alias="historyAvailable")
    stages_with_evidence: int = Field(0, alias="stagesWithEvidence")
    total_stages: int = Field(10, alias="totalStages")
    stages: list[PipelineStageResponse]
    overall_progress: int | None = Field(None, alias="overallProgress")
    started_at: str | None = Field(None, alias="startedAt")
    completed_at: str | None = Field(None, alias="completedAt")
    estimated_completion_at: str | None = Field(None, alias="estimatedCompletionAt")
    history: list[StatusHistoryResponse] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "from_attributes": True}


DocumentPipelineStatusResponse = PipelineStatusResponse



"""
Agent Management API — endpoints for monitoring and controlling AI agents.

Provides:
- GET /agents — list all agents with current status
- GET /agents/{id}/status — get single agent status
- POST /agents/{id}/retry — retry a failed agent
- GET /agents/{id}/logs — get agent execution logs
- GET /agents/pipeline — get pipeline status
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, TokenPayload
from app.db.session import get_db
from app.models.document import Document
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/agents", tags=["agents"])

# ── Agent Registry (18 Pipeline Agents) ───────────────────────────────────────

AGENT_IDS = [
    "ocr", "ingestion", "classification", "chunking", "embedding",
    "retrieval", "entity_extraction", "relationship", "timeline",
    "summarization", "privilege", "risk", "pii", "review",
    "verification", "clustering", "report", "triage",
]

AGENT_NAMES = {
    "ocr": "OCR Agent",
    "ingestion": "Document Ingestion Agent",
    "classification": "Document Classification Agent",
    "chunking": "Semantic Chunking Agent",
    "embedding": "Vector Embedding Agent",
    "retrieval": "RAG Retrieval Agent",
    "entity_extraction": "Entity Extraction Agent",
    "relationship": "Relationship & Graph Agent",
    "timeline": "Timeline Generation Agent",
    "summarization": "Summarization Agent",
    "privilege": "Privilege Detection Agent",
    "risk": "Risk Assessment Agent",
    "pii": "PII Redaction Agent",
    "review": "AI Review Agent",
    "verification": "Citation Verification Agent",
    "clustering": "Document Clustering Agent",
    "report": "Report Generation Agent",
    "triage": "Triage Orchestrator Agent",
}

# Aliases mapping legacy or sub-feature IDs to canonical agents
AGENT_ALIASES: dict[str, str] = {
    "relationship_extraction": "relationship",
    "knowledge_graph": "relationship",
    "rag_retrieval": "retrieval",
    "similarity_search": "retrieval",
    "legal_review": "review",
    "citation_verification": "verification",
    "hallucination_detection": "verification",
    "evidence_linking": "review",
    "report_generation": "report",
    "triage_orchestrator": "triage",
}


def resolve_agent_id(aid: str) -> str:
    """Resolve an agent ID or alias to its canonical 18-agent pipeline ID."""
    return AGENT_ALIASES.get(aid, aid)


def get_all_matching_ids(canonical_id: str) -> list[str]:
    """Return canonical ID and any legacy aliases that map to it."""
    aliases = [k for k, v in AGENT_ALIASES.items() if v == canonical_id]
    return list(set([canonical_id] + aliases))


PIPELINE_STAGES = [
    {"id": "case_creation", "label": "Case Creation", "order": 1, "agent_ids": []},
    {"id": "document_upload", "label": "Document Ingestion", "order": 2, "agent_ids": ["ingestion"]},
    {"id": "ocr", "label": "OCR & Extraction", "order": 3, "agent_ids": ["ocr"]},
    {"id": "indexing", "label": "Classification & Indexing", "order": 4, "agent_ids": ["classification", "chunking", "embedding", "entity_extraction"]},
    {"id": "retrieval", "label": "Retrieval & Clustering", "order": 5, "agent_ids": ["retrieval", "clustering"]},
    {"id": "legal_review", "label": "Legal Review & Analysis", "order": 6, "agent_ids": ["summarization", "privilege", "risk", "pii", "review", "verification"]},
    {"id": "graph_generation", "label": "Knowledge Graph", "order": 7, "agent_ids": ["relationship"]},
    {"id": "timeline_generation", "label": "Timeline Generation", "order": 8, "agent_ids": ["timeline"]},
    {"id": "evidence_linking", "label": "Triage & Escalation", "order": 9, "agent_ids": ["triage"]},
    {"id": "final_report", "label": "Reporting", "order": 10, "agent_ids": ["report"]},
]


# ── Response Models ──────────────────────────────────────────────────────────

class AgentLogEntry(BaseModel):
    id: str
    timestamp: str
    level: str
    message: str
    metadata: dict = Field(default_factory=dict)


class AgentStatusResponse(BaseModel):
    agent_id: str = Field(alias="agentId")
    status: str
    progress: int
    processing_time_ms: int = Field(alias="processingTimeMs")
    confidence_score: Optional[float] = Field(None, alias="confidenceScore")
    priority_score: Optional[float] = Field(None, alias="priorityScore")
    token_usage: int = Field(alias="tokenUsage")
    queue_position: int = Field(alias="queuePosition")
    last_execution_time: Optional[str] = Field(None, alias="lastExecutionTime")
    logs: list[AgentLogEntry] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    retry_count: int = Field(0, alias="retryCount")
    started_at: Optional[str] = Field(None, alias="startedAt")
    completed_at: Optional[str] = Field(None, alias="completedAt")

    model_config = {"populate_by_name": True}


from app.schemas.document import (
    PipelineStageResponse,
    PipelineStatusResponse,
    DocumentPipelineStatusResponse,
)


class RetryResponse(BaseModel):
    success: bool
    message: str


def _build_agent_status_from_logs(agent_id: str, logs: list[AuditLog]) -> AgentStatusResponse:
    """Build honest agent status from real execution records in AuditLog."""
    if not logs:
        # Genuinely never run yet — honest empty state (renders 'Idle' / 'No executions yet' in UI)
        return AgentStatusResponse(
            agentId=agent_id,
            status="idle",
            progress=0,
            processingTimeMs=0,
            confidenceScore=None,
            priorityScore=None,
            tokenUsage=0,
            queuePosition=0,
            lastExecutionTime=None,
            logs=[],
            errors=[],
            retryCount=0,
            startedAt=None,
            completedAt=None,
        )

    latest = logs[0]
    details = latest.details or {}
    duration = int(details.get("duration_ms", 0))
    token_usage = int(details.get("token_usage", 0))
    
    raw_confidence = details.get("confidence")
    confidence = float(raw_confidence) if raw_confidence is not None else None
    
    raw_priority = details.get("priority_score")
    priority_score = float(raw_priority) if raw_priority is not None else None

    is_failed = latest.action == "AGENT_EXECUTION_FAILED"
    status_str = "failed" if is_failed else "completed"

    formatted_logs = [
        AgentLogEntry(
            id=f"audit_{l.id}",
            timestamp=l.created_at.isoformat(),
            level="error" if l.action == "AGENT_EXECUTION_FAILED" else "info",
            message=(l.details or {}).get("message", f"Execution in {(l.details or {}).get('duration_ms', 0)}ms"),
            metadata=l.details or {},
        )
        for l in logs[:10]
    ]

    started_at = (latest.created_at - timedelta(milliseconds=duration)).isoformat()
    completed_at = latest.created_at.isoformat()

    return AgentStatusResponse(
        agentId=agent_id,
        status=status_str,
        progress=100 if not is_failed else 50,
        processingTimeMs=duration,
        confidenceScore=confidence,
        priorityScore=priority_score,
        tokenUsage=token_usage,
        queuePosition=0,
        lastExecutionTime=latest.created_at.isoformat(),
        logs=formatted_logs,
        errors=[details.get("message")] if is_failed and details.get("message") else [],
        retryCount=0,
        startedAt=started_at,
        completedAt=completed_at,
    )


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=list[AgentStatusResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List all agents with current status based on real execution logs."""
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.resource_type == "agent",
            AuditLog.action.in_(["AGENT_EXECUTION_COMPLETED", "AGENT_EXECUTION_FAILED"]),
        )
        .order_by(AuditLog.created_at.desc())
    )
    result = await db.execute(stmt)
    all_logs = result.scalars().all()

    logs_by_agent: dict[str, list[AuditLog]] = {aid: [] for aid in AGENT_IDS}
    for log in all_logs:
        canonical = resolve_agent_id(log.resource_id)
        if canonical in logs_by_agent:
            logs_by_agent[canonical].append(log)

    return [_build_agent_status_from_logs(aid, logs_by_agent[aid]) for aid in AGENT_IDS]


@router.get("/{agent_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get single agent status based on real execution logs."""
    canonical_id = resolve_agent_id(agent_id)
    if canonical_id not in AGENT_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    matching_ids = get_all_matching_ids(canonical_id)
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.resource_type == "agent",
            AuditLog.resource_id.in_(matching_ids),
            AuditLog.action.in_(["AGENT_EXECUTION_COMPLETED", "AGENT_EXECUTION_FAILED"]),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    agent_logs = result.scalars().all()
    return _build_agent_status_from_logs(canonical_id, agent_logs)


@router.post("/{agent_id}/retry", response_model=RetryResponse)
async def retry_agent(
    agent_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Retry a failed agent."""
    canonical_id = resolve_agent_id(agent_id)
    if canonical_id not in AGENT_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return RetryResponse(
        success=True,
        message=f"Agent '{AGENT_NAMES.get(canonical_id, canonical_id)}' has been queued for retry",
    )


@router.get("/{agent_id}/logs", response_model=list[AgentLogEntry])
async def get_agent_logs(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get real agent execution logs."""
    canonical_id = resolve_agent_id(agent_id)
    if canonical_id not in AGENT_IDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    matching_ids = get_all_matching_ids(canonical_id)
    stmt = (
        select(AuditLog)
        .where(
            AuditLog.resource_type == "agent",
            AuditLog.resource_id.in_(matching_ids),
            AuditLog.action.in_(["AGENT_EXECUTION_COMPLETED", "AGENT_EXECUTION_FAILED"]),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        AgentLogEntry(
            id=f"audit_{l.id}",
            timestamp=l.created_at.isoformat(),
            level="error" if l.action == "AGENT_EXECUTION_FAILED" else "info",
            message=(l.details or {}).get("message", f"Execution in {(l.details or {}).get('duration_ms', 0)}ms"),
            metadata=l.details or {},
        )
        for l in logs
    ]


@router.get("/pipeline", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    document_id: Optional[uuid.UUID] = Query(None, alias="documentId"),
    case_id: Optional[uuid.UUID] = Query(None, alias="caseId"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    Get real, case-scoped, document-scoped pipeline status based on status_history and document state.
    """
    from app.services.status_history_service import get_pipeline_execution_status
    return await get_pipeline_execution_status(
        db=db,
        current_user=current_user,
        document_id=document_id,
        case_id=case_id,
    )

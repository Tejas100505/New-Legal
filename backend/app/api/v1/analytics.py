"""
Analytics and Evaluation Metrics API routes.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document
from app.repositories.evaluation_repository import EvaluationRepository
from app.auth.dependencies import get_current_user, TokenPayload, UserRole

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class FeedbackRequest(BaseModel):
    case_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    metric_type: str = "review"
    user_feedback: Dict[str, Any]


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get aggregated evaluation metrics",
)
async def get_analytics(
    case_id: Optional[uuid.UUID] = Query(None, description="Optional case filter"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Calculate and return aggregate performance and quality metrics."""
    if case_id and current_user.role != UserRole.ADMIN:
        case = await db.get(Case, case_id)
        if not case or case.created_by != current_user.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case analytics")

    repo = EvaluationRepository(db)
    aggregates = await repo.get_aggregates_by_case(case_id)
    
    from app.models.document import DocumentStatus

    # Query real document counts
    base_filter = []
    if case_id:
        base_filter.append(Document.case_id == case_id)
    elif current_user.role != UserRole.ADMIN:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except (ValueError, TypeError):
            user_uuid = None
        filter_cond = (Case.created_by == current_user.sub)
        if user_uuid is not None:
            filter_cond = filter_cond | ((Document.case_id.is_(None)) & (Document.uploaded_by == user_uuid))
        base_filter.append(filter_cond)

    total_stmt = select(func.count(Document.id)).outerjoin(Case, Document.case_id == Case.id)
    if base_filter:
        total_stmt = total_stmt.where(*base_filter)
    total_docs = (await db.execute(total_stmt)).scalar() or 0

    reviewed_stmt = (
        select(func.count(Document.id))
        .outerjoin(Case, Document.case_id == Case.id)
        .where(Document.status == DocumentStatus.REVIEWED)
    )
    if base_filter:
        reviewed_stmt = reviewed_stmt.where(*base_filter)
    reviewed_docs = (await db.execute(reviewed_stmt)).scalar() or 0

    flagged_stmt = (
        select(func.count(Document.id))
        .outerjoin(Case, Document.case_id == Case.id)
        .where(Document.status == DocumentStatus.FLAGGED)
    )
    if base_filter:
        flagged_stmt = flagged_stmt.where(*base_filter)
    flagged_docs = (await db.execute(flagged_stmt)).scalar() or 0

    quota_paused_stmt = (
        select(func.count(Document.id))
        .outerjoin(Case, Document.case_id == Case.id)
        .where(Document.status == DocumentStatus.QUOTA_PAUSED)
    )
    if base_filter:
        quota_paused_stmt = quota_paused_stmt.where(*base_filter)
    quota_paused_docs = (await db.execute(quota_paused_stmt)).scalar() or 0

    # ── Real Document Chunk Count ───────────────────────────────────────────
    from app.models.chunk import DocumentChunk
    chunks_stmt = (
        select(func.count(DocumentChunk.id))
        .outerjoin(Document, DocumentChunk.document_id == Document.id)
        .outerjoin(Case, Document.case_id == Case.id)
    )
    if base_filter:
        chunks_stmt = chunks_stmt.where(*base_filter)
    total_chunks = (await db.execute(chunks_stmt)).scalar() or 0

    # ── Real Entity Detection Count (Correction A & D) ───────────────────────
    # Full DocumentStatus enum from app.models.document:
    #   UPLOADED, VALIDATING, OCR_PROCESSING, CHUNKING, EMBEDDING, ANALYZING,
    #   REVIEWED, FLAGGED, QUOTA_PAUSED, ERROR
    #
    # Negative exclude-list of pipeline-incomplete statuses:
    # - UPLOADED, VALIDATING, OCR_PROCESSING, CHUNKING, EMBEDDING: Stages preceding entity extraction.
    # - ANALYZING: Document is actively undergoing or was interrupted during entity/relationship extraction.
    # - QUOTA_PAUSED: Pipeline paused mid-execution on quota exhaustion; extraction incomplete.
    # - ERROR: Pipeline failed with an exception.
    #
    # Statuses included (pipeline completed entity extraction):
    # - REVIEWED: Successfully completed full pipeline without triage escalation.
    # - FLAGGED: Successfully completed full pipeline with triage escalation.
    excluded_entity_statuses = [
        DocumentStatus.UPLOADED,
        DocumentStatus.VALIDATING,
        DocumentStatus.OCR_PROCESSING,
        DocumentStatus.CHUNKING,
        DocumentStatus.EMBEDDING,
        DocumentStatus.ANALYZING,
        DocumentStatus.QUOTA_PAUSED,
        DocumentStatus.ERROR,
    ]

    entity_stmt = (
        select(Document.doc_metadata)
        .outerjoin(Case, Document.case_id == Case.id)
        .where(
            Document.doc_metadata.isnot(None),
            Document.status.notin_(excluded_entity_statuses),
        )
    )
    if base_filter:
        entity_stmt = entity_stmt.where(*base_filter)

    entity_docs = (await db.execute(entity_stmt)).scalars().all()

    total_entities = 0
    for meta in entity_docs:
        if isinstance(meta, dict):
            ents = meta.get("entities", {})
            if isinstance(ents, dict):
                for cat_items in ents.values():
                    if isinstance(cat_items, list):
                        total_entities += len(cat_items)
            elif isinstance(ents, list):
                total_entities += len(ents)

    # ── Real Storage Usage (Bytes) ───────────────────────────────────────────
    storage_stmt = (
        select(func.sum(Document.file_size))
        .outerjoin(Case, Document.case_id == Case.id)
        .where(
            Document.status.notin_(excluded_entity_statuses),
        )
    )
    if base_filter:
        storage_stmt = storage_stmt.where(*base_filter)
    total_storage_bytes = (await db.execute(storage_stmt)).scalar() or 0

    enriched_metrics = {
        "total_documents": total_docs,
        "reviewed_documents": reviewed_docs,
        "flagged_documents": flagged_docs,
        "quota_paused_documents": quota_paused_docs,
        "total_chunks": total_chunks,
        "total_storage_bytes": total_storage_bytes,
        "avg_review_time_seconds": None,
        "total_entities_detected": total_entities,
        "avg_confidence_score": None,
        **aggregates,
    }
    
    # Explainability and Ground Truth Context:
    # Some metrics (like OCR Accuracy or Retrieval Precision/Recall) require
    # a ground-truth dataset. If no metrics have been run, or if the metrics
    # cannot be fully computed without ground-truth annotations, we report them
    # clearly as None or state so explicitly in the response context.
    return {
        "status": "success",
        "case_id": str(case_id) if case_id else None,
        "metrics": enriched_metrics,
        "explanation": {
            "ocr_accuracy": "Evaluated relative to digital text character overlap extraction.",
            "retrieval_precision_recall": "Currently calculated on mock search queries or simulated ground truth.",
            "hallucination_rate": "Computed via N-gram term verification against the source document (excluding stopwords)."
        }
    }


@router.get(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="Get raw metrics history",
)
async def get_metrics_history(
    case_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Return all recorded metric entries."""
    repo = EvaluationRepository(db)
    if case_id:
        entries = await repo.get_by_case_id(case_id)
    else:
        entries = await repo.get_all(limit=100)
        
    return [
        {
            "id": str(e.id),
            "case_id": str(e.case_id) if e.case_id else None,
            "document_id": str(e.document_id) if e.document_id else None,
            "metric_type": e.metric_type,
            "ocr_accuracy": e.ocr_accuracy,
            "rouge_scores": e.rouge_scores,
            "hallucination_rate": e.hallucination_rate,
            "latency_ms": e.latency_ms,
            "token_usage": e.token_usage,
            "privilege_accuracy": e.privilege_accuracy,
            "created_at": e.created_at.isoformat()
        }
        for e in entries
    ]


@router.post(
    "/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Log user feedback on AI predictions",
)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Submit rating or correction feedback on AI summaries, risks, or privilege flags."""
    repo = EvaluationRepository(db)
    
    # Create evaluation metric entry representing user feedback
    feedback_entry = await repo.create(
        case_id=request.case_id,
        document_id=request.document_id,
        metric_type="user_feedback",
        user_feedback=request.user_feedback,
        latency_ms=0.0
    )
    
    await db.commit()
    
    return {
        "status": "logged",
        "entry_id": str(feedback_entry.id),
        "message": "User feedback successfully logged for quality evaluation metrics"
    }

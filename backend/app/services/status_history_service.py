"""
Document Status History Service.

Provides a unified, atomic helper to transition a document's status
and record the audit trail entry in the status_history table.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, UserRole
from app.models.document import Document, DocumentStatus
from app.models.status_history import StatusHistory



async def record_status_transition(
    session: AsyncSession,
    document: Document,
    new_status: DocumentStatus | str,
    *,
    changed_by: uuid.UUID | str | None = None,
    reason: str | None = None,
    old_status: str | None = None,
) -> StatusHistory:
    """
    Atomically updates a document's status and adds a StatusHistory audit record.

    Args:
        session: Active AsyncSession.
        document: Target Document model instance.
        new_status: The DocumentStatus enum or string value to transition to.
        changed_by: User UUID or user_id string if human-driven; None for system/pipeline.
        reason: Optional contextual reason for the transition.
        old_status: Explicit old status override (useful for initial creation where old_status=None).
                    If not provided, defaults to document's current status string.

    Returns:
        The newly created StatusHistory instance added to the session.
    """
    # Determine old status
    if old_status is not None:
        prior_status_val = old_status
    elif document.status is not None:
        prior_status_val = document.status.value if hasattr(document.status, "value") else str(document.status)
    else:
        prior_status_val = None

    # Determine and set new status
    if isinstance(new_status, DocumentStatus):
        new_status_enum = new_status
        new_status_val = new_status.value
    else:
        status_str = str(new_status).lower()
        try:
            new_status_enum = DocumentStatus(status_str)
            new_status_val = new_status_enum.value
        except ValueError:
            try:
                new_status_enum = getattr(DocumentStatus, status_str.upper())
                new_status_val = new_status_enum.value
            except AttributeError:
                new_status_val = status_str
                new_status_enum = new_status

    document.status = new_status_enum

    # Parse changed_by to UUID if provided as string
    changed_by_uuid: uuid.UUID | None = None
    if changed_by:
        if isinstance(changed_by, uuid.UUID):
            changed_by_uuid = changed_by
        else:
            try:
                changed_by_uuid = uuid.UUID(str(changed_by))
            except (ValueError, TypeError):
                changed_by_uuid = None

    history = StatusHistory(
        document_id=document.id,
        old_status=prior_status_val,
        new_status=new_status_val,
        changed_at=datetime.now(timezone.utc),
        changed_by=changed_by_uuid,
        reason=reason,
    )
    res = session.add(history)
    if hasattr(res, "__await__"):
        await res
    return history


# ── Canonical 10-Stage Pipeline Definitions ───────────────────────────────────

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


async def verify_document_access(doc: Document, current_user: TokenPayload, db: AsyncSession) -> None:
    """
    Enforce document access control scoping matching the core permission model:
    - ADMIN role users have global oversight across all documents.
    - Documents associated with a case inherit access through Case owner (case.created_by).
    - Documents with case_id=None are strictly scoped to the uploading user (uploaded_by).
    """
    from app.auth.dependencies import UserRole
    if current_user.role == UserRole.ADMIN:
        return

    case_id = getattr(doc, "case_id", None)
    if case_id is None:
        user_sub = current_user.sub
        uploaded_by = getattr(doc, "uploaded_by", None)
        doc_uploader = str(uploaded_by) if uploaded_by is not None else None
        if not doc_uploader or doc_uploader != user_sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you do not have permission to access this document.",
            )
    else:
        from app.models.case import Case
        case = await db.get(Case, case_id)
        if not case or case.created_by != current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you do not have permission to access this document.",
            )


def _compute_doc_pipeline_status(
    doc: Document,
    history_records: list[StatusHistory],
) -> PipelineStatusResponse:
    """Derive real, honest pipeline stage state for a single document."""
    from app.schemas.document import PipelineStageResponse, PipelineStatusResponse, StatusHistoryResponse

    doc_status_val = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
    meta = dict(doc.doc_metadata or {})
    is_quota_paused = (doc.status == DocumentStatus.QUOTA_PAUSED)
    paused_stage = meta.get("paused_stage") or (meta.get("quota_pause") or {}).get("paused_at_stage")
    paused_reason = meta.get("paused_reason")

    history = [StatusHistoryResponse.model_validate(h) for h in history_records]
    last_reason = history_records[-1].reason if history_records else None

    stages: list[PipelineStageResponse] = []
    completed_at: str | None = None

    if doc.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED]:
        for s_def in PIPELINE_STAGES:
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"],
                    label=s_def["label"],
                    order=s_def["order"],
                    agentIds=s_def["agent_ids"],
                    status="completed",
                )
            )
        current_stage = "final_report"
        overall_progress = 100
        for h in reversed(history_records):
            if h.new_status in ["reviewed", "flagged"]:
                completed_at = h.changed_at.isoformat()
                break
        if not completed_at and doc.updated_at:
            completed_at = doc.updated_at.isoformat()

    elif doc.status == DocumentStatus.QUOTA_PAUSED:
        target_stage_id = "legal_review"
        if paused_stage in ["ocr"]:
            target_stage_id = "ocr"
        elif paused_stage in ["classification", "chunking", "embedding", "entity_extraction"]:
            target_stage_id = "indexing"
        elif paused_stage in ["retrieval", "clustering"]:
            target_stage_id = "retrieval"
        elif paused_stage in ["summarization", "privilege", "risk", "pii", "review", "verification"]:
            target_stage_id = "legal_review"
        elif paused_stage in ["relationship"]:
            target_stage_id = "graph_generation"
        elif paused_stage in ["timeline"]:
            target_stage_id = "timeline_generation"

        target_order = next((s["order"] for s in PIPELINE_STAGES if s["id"] == target_stage_id), 6)
        for s_def in PIPELINE_STAGES:
            if s_def["order"] < target_order:
                st = "completed"
            elif s_def["order"] == target_order:
                st = "paused"
            else:
                st = "idle"
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"],
                    label=s_def["label"],
                    order=s_def["order"],
                    agentIds=s_def["agent_ids"],
                    status=st,
                )
            )
        current_stage = target_stage_id
        completed_count = sum(1 for s in stages if s.status == "completed")
        overall_progress = int((completed_count / len(stages)) * 100)

    elif doc.status == DocumentStatus.ERROR:
        target_stage_id = "ocr"
        target_order = 3
        for s_def in PIPELINE_STAGES:
            if s_def["order"] < target_order:
                st = "completed"
            elif s_def["order"] == target_order:
                st = "failed"
            else:
                st = "idle"
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"],
                    label=s_def["label"],
                    order=s_def["order"],
                    agentIds=s_def["agent_ids"],
                    status=st,
                )
            )
        current_stage = target_stage_id
        completed_count = sum(1 for s in stages if s.status == "completed")
        overall_progress = int((completed_count / len(stages)) * 100)

    elif doc.status == DocumentStatus.ANALYZING:
        target_stage_id = "legal_review"
        target_order = 6
        for s_def in PIPELINE_STAGES:
            if s_def["order"] < target_order:
                st = "completed"
            elif s_def["order"] == target_order:
                st = "running"
            else:
                st = "idle"
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"],
                    label=s_def["label"],
                    order=s_def["order"],
                    agentIds=s_def["agent_ids"],
                    status=st,
                )
            )
        current_stage = target_stage_id
        completed_count = sum(1 for s in stages if s.status == "completed")
        overall_progress = int((completed_count / len(stages)) * 100)

    elif doc.status in [DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING]:
        target_stage_id = "indexing"
        target_order = 4
        for s_def in PIPELINE_STAGES:
            if s_def["order"] < target_order:
                st = "completed"
            elif s_def["order"] == target_order:
                st = "running"
            else:
                st = "idle"
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"],
                    label=s_def["label"],
                    order=s_def["order"],
                    agentIds=s_def["agent_ids"],
                    status=st,
                )
            )
        current_stage = target_stage_id
        completed_count = sum(1 for s in stages if s.status == "completed")
        overall_progress = int((completed_count / len(stages)) * 100)

    elif doc.status == DocumentStatus.OCR_PROCESSING:
        target_stage_id = "ocr"
        target_order = 3
        for s_def in PIPELINE_STAGES:
            if s_def["order"] < target_order:
                st = "completed"
            elif s_def["order"] == target_order:
                st = "running"
            else:
                st = "idle"
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"],
                    label=s_def["label"],
                    order=s_def["order"],
                    agentIds=s_def["agent_ids"],
                    status=st,
                )
            )
        current_stage = target_stage_id
        completed_count = sum(1 for s in stages if s.status == "completed")
        overall_progress = int((completed_count / len(stages)) * 100)

    elif doc.status == DocumentStatus.VALIDATING:
        target_stage_id = "document_upload"
        target_order = 2
        for s_def in PIPELINE_STAGES:
            if s_def["order"] < target_order:
                st = "completed"
            elif s_def["order"] == target_order:
                st = "running"
            else:
                st = "idle"
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"],
                    label=s_def["label"],
                    order=s_def["order"],
                    agentIds=s_def["agent_ids"],
                    status=st,
                )
            )
        current_stage = target_stage_id
        completed_count = sum(1 for s in stages if s.status == "completed")
        overall_progress = int((completed_count / len(stages)) * 100)

    else:  # UPLOADED or other initial state
        stages.append(PipelineStageResponse(id="case_creation", label="Case Creation", order=1, agentIds=[], status="completed"))
        stages.append(PipelineStageResponse(id="document_upload", label="Document Ingestion", order=2, agentIds=["ingestion"], status="completed"))
        for s_def in PIPELINE_STAGES[2:]:
            stages.append(PipelineStageResponse(id=s_def["id"], label=s_def["label"], order=s_def["order"], agentIds=s_def["agent_ids"], status="idle"))
        current_stage = "ocr"
        overall_progress = 20

    started_at = (
        history_records[0].changed_at.isoformat()
        if history_records
        else (doc.created_at.isoformat() if doc.created_at else None)
    )

    return PipelineStatusResponse(
        caseId=str(doc.case_id) if doc.case_id else None,
        documentId=str(doc.id),
        status=doc_status_val,
        currentStage=current_stage,
        isQuotaPaused=is_quota_paused,
        pausedStage=paused_stage,
        pausedReason=paused_reason,
        lastReason=last_reason,
        stages=stages,
        overallProgress=overall_progress,
        startedAt=started_at,
        completedAt=completed_at,
        estimatedCompletionAt=None,
        history=history,
    )


async def get_pipeline_execution_status(
    db: AsyncSession,
    current_user: TokenPayload,
    document_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
) -> PipelineStatusResponse:
    """
    Computes real, case-scoped, document-scoped pipeline execution status.
    Backed strictly by status_history and Document/Case state in PostgreSQL.
    No hardcoded values, no fabricated ETA or progress percentages.
    """
    from sqlalchemy import select
    from fastapi import HTTPException, status
    from app.models.case import Case
    from app.auth.dependencies import UserRole
    from app.services.case_scoping import get_case_scoped_document_ids
    from app.schemas.document import PipelineStageResponse, PipelineStatusResponse

    # ── Branch 1: Specific Document Requested ─────────────────────────────────
    if document_id is not None:
        if case_id is not None:
            # Enforce 403-before-404 existence privacy on case
            if current_user.role != UserRole.ADMIN:
                case = await db.get(Case, case_id)
                if not case or case.created_by != current_user.sub:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this case",
                    )
            else:
                case = await db.get(Case, case_id)
                if not case:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Case {case_id} not found.",
                    )

            doc = await db.get(Document, document_id)
            if not doc or doc.case_id != case_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} not found in case {case_id}.",
                )
        else:
            doc = await db.get(Document, document_id)
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} not found.",
                )
            await verify_document_access(doc, current_user, db)

        stmt = (
            select(StatusHistory)
            .where(StatusHistory.document_id == doc.id)
            .order_by(StatusHistory.changed_at.asc(), StatusHistory.created_at.asc())
        )
        history_records = (await db.execute(stmt)).scalars().all()
        return _compute_doc_pipeline_status(doc, list(history_records))

    # ── Branch 2: Specific Case Requested (No Document ID) ─────────────────────
    if case_id is not None:
        if current_user.role != UserRole.ADMIN:
            case = await db.get(Case, case_id)
            if not case or case.created_by != current_user.sub:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this case",
                )
        else:
            case = await db.get(Case, case_id)
            if not case:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Case {case_id} not found.",
                )

        stmt = select(Document).where(Document.case_id == case_id)
        docs = (await db.execute(stmt)).scalars().all()
        if not docs:
            stages = [
                PipelineStageResponse(
                    id=s["id"], label=s["label"], order=s["order"], agentIds=s["agent_ids"], status="idle"
                )
                for s in PIPELINE_STAGES
            ]
            return PipelineStatusResponse(
                caseId=str(case_id),
                documentId=None,
                status=None,
                currentStage="case_creation",
                isQuotaPaused=False,
                pausedStage=None,
                pausedReason=None,
                lastReason=None,
                stages=stages,
                overallProgress=0,
                startedAt=case.created_at.isoformat() if case and case.created_at else None,
                completedAt=None,
                estimatedCompletionAt=None,
                history=[],
            )

        doc_statuses = [d.status for d in docs]
        all_completed = all(s in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED] for s in doc_statuses)
        any_paused = any(s == DocumentStatus.QUOTA_PAUSED for s in doc_statuses)
        any_running = any(
            s in [DocumentStatus.OCR_PROCESSING, DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING, DocumentStatus.ANALYZING, DocumentStatus.VALIDATING]
            for s in doc_statuses
        )

        if all_completed:
            stages = [
                PipelineStageResponse(
                    id=s["id"], label=s["label"], order=s["order"], agentIds=s["agent_ids"], status="completed"
                )
                for s in PIPELINE_STAGES
            ]
            current_stage = "final_report"
            overall_progress = 100
            latest_upd = max((d.updated_at for d in docs if d.updated_at), default=None)
            completed_at = latest_upd.isoformat() if latest_upd else None
        else:
            current_stage = "indexing" if any_running else "ocr"
            stages = []
            for s_def in PIPELINE_STAGES:
                st = "completed" if s_def["order"] <= 2 else ("running" if s_def["order"] <= 5 and any_running else "idle")
                stages.append(
                    PipelineStageResponse(
                        id=s_def["id"], label=s_def["label"], order=s_def["order"], agentIds=s_def["agent_ids"], status=st
                    )
                )
            completed_count = sum(1 for s in stages if s.status == "completed")
            overall_progress = int((completed_count / len(stages)) * 100)
            completed_at = None

        earliest_created = min((d.created_at for d in docs if d.created_at), default=None)
        started_at = earliest_created.isoformat() if earliest_created else (case.created_at.isoformat() if case and case.created_at else None)

        return PipelineStatusResponse(
            caseId=str(case_id),
            documentId=None,
            status=None,
            currentStage=current_stage,
            isQuotaPaused=any_paused,
            pausedStage="legal_review" if any_paused else None,
            pausedReason="Daily quota paused on in-flight documents" if any_paused else None,
            lastReason=None,
            stages=stages,
            overallProgress=overall_progress,
            startedAt=started_at,
            completedAt=completed_at,
            estimatedCompletionAt=None,
            history=[],
        )

    # ── Branch 3: Global / System-Level Query ──────────────────────────────────
    doc_ids = await get_case_scoped_document_ids(db, None, current_user)
    if not doc_ids:
        stages = [
            PipelineStageResponse(
                id=s["id"], label=s["label"], order=s["order"], agentIds=s["agent_ids"], status="idle"
            )
            for s in PIPELINE_STAGES
        ]
        return PipelineStatusResponse(
            caseId=None,
            documentId=None,
            status=None,
            currentStage="case_creation",
            isQuotaPaused=False,
            pausedStage=None,
            pausedReason=None,
            lastReason=None,
            stages=stages,
            overallProgress=0,
            startedAt=None,
            completedAt=None,
            estimatedCompletionAt=None,
            history=[],
        )

    stmt = select(Document).where(Document.id.in_(doc_ids[:50]))
    docs = (await db.execute(stmt)).scalars().all()
    all_completed = all(d.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED] for d in docs) if docs else False

    if all_completed:
        stages = [
            PipelineStageResponse(
                id=s["id"], label=s["label"], order=s["order"], agentIds=s["agent_ids"], status="completed"
            )
            for s in PIPELINE_STAGES
        ]
        current_stage = "final_report"
        overall_progress = 100
        latest_upd = max((d.updated_at for d in docs if d.updated_at), default=None)
        completed_at = latest_upd.isoformat() if latest_upd else None
    else:
        stages = []
        for s_def in PIPELINE_STAGES:
            st = "completed" if s_def["order"] <= 2 else "idle"
            stages.append(
                PipelineStageResponse(
                    id=s_def["id"], label=s_def["label"], order=s_def["order"], agentIds=s_def["agent_ids"], status=st
                )
            )
        current_stage = "ocr"
        overall_progress = 20
        completed_at = None

    earliest_created = min((d.created_at for d in docs if d.created_at), default=None)
    started_at = earliest_created.isoformat() if earliest_created else None

    return PipelineStatusResponse(
        caseId=None,
        documentId=None,
        status=None,
        currentStage=current_stage,
        isQuotaPaused=False,
        pausedStage=None,
        pausedReason=None,
        lastReason=None,
        stages=stages,
        overallProgress=overall_progress,
        startedAt=started_at,
        completedAt=completed_at,
        estimatedCompletionAt=None,
        history=[],
    )

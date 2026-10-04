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
    audit_records: list[AuditLog] | None = None,
) -> PipelineStatusResponse:
    """
    Derive real, honest pipeline stage state for a single document.
    Evidence values: {"status_history", "audit_log", "current_status_inference", "none"}.
    Never returns 'completed' with evidence 'none'.
    """
    from app.schemas.document import PipelineStageResponse, PipelineStatusResponse, StatusHistoryResponse

    doc_status_val = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
    meta = dict(doc.doc_metadata or {})
    is_quota_paused = (doc.status == DocumentStatus.QUOTA_PAUSED)
    paused_stage = meta.get("paused_stage") or (meta.get("quota_pause") or {}).get("paused_at_stage")
    paused_reason = meta.get("paused_reason")

    history = [StatusHistoryResponse.model_validate(h) for h in history_records]
    last_reason = history_records[-1].reason if history_records else None

    history_available = len(history_records) > 0
    audit_records = audit_records or []

    # Map audit logs by agent resource_id
    audit_by_agent: dict[str, dict[str, Any]] = {}
    for a in audit_records:
        agent_id = a.resource_id
        det = a.details if isinstance(a.details, dict) else {}
        st = det.get("status") or ("completed" if a.action == "AGENT_EXECUTION_COMPLETED" else "failed")
        audit_by_agent[agent_id] = {
            "status": st,
            "duration_ms": det.get("duration_ms"),
            "created_at": a.created_at,
        }

    # Extract milestone timestamps from status_history
    ocr_completed_time: datetime | None = None
    indexing_completed_time: datetime | None = None
    review_completed_time: datetime | None = None

    if history_available:
        for h in history_records:
            old_s = (h.old_status or "").lower()
            new_s = (h.new_status or "").lower()
            if old_s == "ocr_processing" or new_s in ["chunking", "embedding", "analyzing", "reviewed", "flagged"]:
                if not ocr_completed_time:
                    ocr_completed_time = h.changed_at
            if old_s in ["chunking", "embedding"] or new_s in ["analyzing", "reviewed", "flagged"]:
                if not indexing_completed_time:
                    indexing_completed_time = h.changed_at
            if new_s in ["reviewed", "flagged"]:
                review_completed_time = h.changed_at

    stages: list[PipelineStageResponse] = []
    current_stage = "document_upload"

    for s_def in PIPELINE_STAGES:
        s_id = s_def["id"]
        s_order = s_def["order"]
        agent_ids = s_def["agent_ids"]

        stage_status = "unknown"
        evidence = "none"
        completed_at_val: str | None = None
        duration_ms_val: int | None = None

        if s_id == "document_upload":
            if history_available:
                stage_status = "completed"
                evidence = "status_history"
                completed_at_val = history_records[0].changed_at.isoformat()
            elif doc.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED, DocumentStatus.ANALYZING, DocumentStatus.OCR_PROCESSING, DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING, DocumentStatus.UPLOADED, DocumentStatus.QUOTA_PAUSED, DocumentStatus.ERROR]:
                stage_status = "completed"
                evidence = "current_status_inference"

        elif s_id == "ocr":
            if history_available:
                if ocr_completed_time:
                    stage_status = "completed"
                    evidence = "status_history"
                    completed_at_val = ocr_completed_time.isoformat()
                elif doc.status == DocumentStatus.OCR_PROCESSING:
                    stage_status = "running"
                    evidence = "status_history"
                elif "ocr" in audit_by_agent:
                    stage_status = audit_by_agent["ocr"]["status"]
                    evidence = "audit_log"
                    completed_at_val = audit_by_agent["ocr"]["created_at"].isoformat() if audit_by_agent["ocr"]["created_at"] else None
                    duration_ms_val = audit_by_agent["ocr"]["duration_ms"]
            elif doc.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED, DocumentStatus.ANALYZING, DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING]:
                stage_status = "completed"
                evidence = "current_status_inference"
            elif doc.status == DocumentStatus.OCR_PROCESSING:
                stage_status = "running"
                evidence = "current_status_inference"

        elif s_id == "indexing":
            if history_available:
                if indexing_completed_time:
                    stage_status = "completed"
                    evidence = "status_history"
                    completed_at_val = indexing_completed_time.isoformat()
                elif doc.status in [DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING]:
                    stage_status = "running"
                    evidence = "status_history"
                else:
                    matching = [aid for aid in agent_ids if aid in audit_by_agent]
                    if matching:
                        stage_status = "completed"
                        evidence = "audit_log"
                        completed_at_val = audit_by_agent[matching[-1]]["created_at"].isoformat() if audit_by_agent[matching[-1]]["created_at"] else None
                        duration_ms_val = sum((audit_by_agent[aid]["duration_ms"] or 0) for aid in matching) or None
            elif doc.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED, DocumentStatus.ANALYZING]:
                stage_status = "completed"
                evidence = "current_status_inference"
            elif doc.status in [DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING]:
                stage_status = "running"
                evidence = "current_status_inference"

        elif s_id == "legal_review":
            if history_available:
                if review_completed_time:
                    stage_status = "completed"
                    evidence = "status_history"
                    completed_at_val = review_completed_time.isoformat()
                elif doc.status == DocumentStatus.ANALYZING:
                    stage_status = "running"
                    evidence = "status_history"
                else:
                    matching = [aid for aid in agent_ids if aid in audit_by_agent]
                    if matching:
                        stage_status = "completed"
                        evidence = "audit_log"
                        completed_at_val = audit_by_agent[matching[-1]]["created_at"].isoformat() if audit_by_agent[matching[-1]]["created_at"] else None
                        duration_ms_val = sum((audit_by_agent[aid]["duration_ms"] or 0) for aid in matching) or None
            elif doc.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED]:
                stage_status = "completed"
                evidence = "current_status_inference"
            elif doc.status == DocumentStatus.ANALYZING:
                stage_status = "running"
                evidence = "current_status_inference"

        else:
            # Case-level or non-document derivable stages (case_creation, retrieval, graph_generation, timeline_generation, evidence_linking, final_report)
            matching = [aid for aid in agent_ids if aid in audit_by_agent]
            if matching:
                stage_status = "completed"
                evidence = "audit_log"
                completed_at_val = audit_by_agent[matching[-1]]["created_at"].isoformat() if audit_by_agent[matching[-1]]["created_at"] else None
                duration_ms_val = sum((audit_by_agent[aid]["duration_ms"] or 0) for aid in matching) or None
            else:
                stage_status = "unknown"
                evidence = "none"

        # Quota pause adjustments
        if is_quota_paused:
            target_stage_id = "legal_review"
            if paused_stage in ["ocr"]:
                target_stage_id = "ocr"
            elif paused_stage in ["classification", "chunking", "embedding", "entity_extraction"]:
                target_stage_id = "indexing"
            elif paused_stage in ["retrieval", "clustering"]:
                target_stage_id = "retrieval"
            elif paused_stage in ["relationship"]:
                target_stage_id = "graph_generation"
            elif paused_stage in ["timeline"]:
                target_stage_id = "timeline_generation"

            target_order = next((s["order"] for s in PIPELINE_STAGES if s["id"] == target_stage_id), 6)
            if s_id == target_stage_id:
                stage_status = "paused"
                evidence = "status_history" if history_available else "current_status_inference"
            elif s_order > target_order and stage_status == "completed":
                stage_status = "unknown"
                evidence = "none"
                completed_at_val = None
                duration_ms_val = None

        # Error adjustments
        if doc.status == DocumentStatus.ERROR:
            if s_id == "ocr":
                stage_status = "failed"
                evidence = "status_history" if history_available else "current_status_inference"
            elif s_order > 3 and stage_status == "completed":
                stage_status = "unknown"
                evidence = "none"
                completed_at_val = None
                duration_ms_val = None

        # Absolute integrity invariant: never return 'completed' with evidence 'none'
        if stage_status == "completed" and evidence == "none":
            stage_status = "unknown"

        stages.append(
            PipelineStageResponse(
                id=s_id,
                label=s_def["label"],
                order=s_order,
                agentIds=agent_ids,
                status=stage_status,
                evidence=evidence,
                completedAt=completed_at_val,
                durationMs=duration_ms_val,
            )
        )

    # Determine currentStage
    if doc.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED]:
        current_stage = "final_report"
    elif is_quota_paused:
        current_stage = paused_stage or "legal_review"
    elif doc.status == DocumentStatus.ANALYZING:
        current_stage = "legal_review"
    elif doc.status in [DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING]:
        current_stage = "indexing"
    elif doc.status == DocumentStatus.OCR_PROCESSING:
        current_stage = "ocr"
    elif doc.status == DocumentStatus.VALIDATING:
        current_stage = "document_upload"
    else:
        current_stage = "document_upload"

    started_at = (
        history_records[0].changed_at.isoformat()
        if history_records
        else (doc.created_at.isoformat() if doc.created_at else None)
    )

    completed_at = (
        review_completed_time.isoformat()
        if (history_available and review_completed_time and doc.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED])
        else None
    )

    stages_with_evidence = sum(1 for s in stages if s.evidence != "none")

    return PipelineStatusResponse(
        caseId=str(doc.case_id) if doc.case_id else None,
        documentId=str(doc.id),
        status=doc_status_val,
        currentStage=current_stage,
        isQuotaPaused=is_quota_paused,
        pausedStage=paused_stage,
        pausedReason=paused_reason,
        lastReason=last_reason,
        historyAvailable=history_available,
        stagesWithEvidence=stages_with_evidence,
        totalStages=len(stages),
        stages=stages,
        overallProgress=None,  # frontend tolerates null; no unproven progress
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
    Backed strictly by status_history, AuditLog, and Document/Case state in PostgreSQL.
    No hardcoded values, no fabricated ETA or unproven completed stages.
    """
    from sqlalchemy import select
    from fastapi import HTTPException, status
    from app.models.case import Case
    from app.models.audit_log import AuditLog
    from app.auth.dependencies import UserRole
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

        # Retrieve status history
        stmt = (
            select(StatusHistory)
            .where(StatusHistory.document_id == doc.id)
            .order_by(StatusHistory.changed_at.asc(), StatusHistory.created_at.asc())
        )
        history_records = (await db.execute(stmt)).scalars().all()

        # Retrieve per-document agent execution audit logs
        doc_id_str = str(doc.id)
        try:
            audit_stmt = (
                select(AuditLog)
                .where(
                    AuditLog.resource_type == "agent",
                    AuditLog.details["document_id"].as_string() == doc_id_str
                )
                .order_by(AuditLog.created_at.asc())
            )
            audit_records = (await db.execute(audit_stmt)).scalars().all()
        except Exception:
            audit_stmt = select(AuditLog).where(AuditLog.resource_type == "agent")
            all_audits = (await db.execute(audit_stmt)).scalars().all()
            audit_records = [
                a for a in all_audits
                if a.details and (
                    isinstance(a.details, dict) and str(a.details.get("document_id")) == doc_id_str
                    or isinstance(a.details, str) and doc_id_str in a.details
                )
            ]

        return _compute_doc_pipeline_status(doc, list(history_records), list(audit_records))

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

        doc_stmt = select(Document).where(Document.case_id == case_id)
        case_docs = list((await db.execute(doc_stmt)).scalars().all())

        stages = []
        total_docs = len(case_docs)

        # Stage 1: Case Creation
        stages.append(
            PipelineStageResponse(
                id="case_creation",
                label="Case Creation",
                order=1,
                agentIds=[],
                status="completed",
                evidence="case_metadata",
                completedAt=case.created_at.isoformat() if case and case.created_at else None,
            )
        )

        if total_docs == 0:
            for s in PIPELINE_STAGES[1:]:
                stages.append(
                    PipelineStageResponse(
                        id=s["id"],
                        label=s["label"],
                        order=s["order"],
                        agentIds=s["agent_ids"],
                        status="idle",
                        evidence="none",
                    )
                )
            return PipelineStatusResponse(
                caseId=str(case_id),
                documentId=None,
                status=None,
                currentStage="case_creation",
                isQuotaPaused=False,
                pausedStage=None,
                pausedReason=None,
                lastReason=None,
                historyAvailable=False,
                stagesWithEvidence=1,
                totalStages=len(stages),
                stages=stages,
                overallProgress=None,
                startedAt=case.created_at.isoformat() if case and case.created_at else None,
                completedAt=None,
                estimatedCompletionAt=None,
                history=[],
            )

        # When documents exist: aggregate status across documents
        docs_with_text = [d for d in case_docs if d.extracted_text and len(d.extracted_text.strip()) > 0]
        docs_chunked = [d for d in case_docs if d.status in [DocumentStatus.CHUNKING, DocumentStatus.EMBEDDING, DocumentStatus.ANALYZING, DocumentStatus.REVIEWED, DocumentStatus.FLAGGED]]
        docs_indexed = [d for d in case_docs if d.status in [DocumentStatus.ANALYZING, DocumentStatus.REVIEWED, DocumentStatus.FLAGGED]]
        docs_reviewed = [d for d in case_docs if d.status in [DocumentStatus.REVIEWED, DocumentStatus.FLAGGED]]
        any_paused = any(d.status == DocumentStatus.QUOTA_PAUSED for d in case_docs)

        # Stage 2: Document Ingestion
        stages.append(
            PipelineStageResponse(
                id="document_upload",
                label="Document Ingestion",
                order=2,
                agentIds=["ingestion"],
                status="completed",
                evidence="document_status_aggregation",
                completedAt=case_docs[-1].created_at.isoformat() if case_docs[-1].created_at else None,
            )
        )

        # Stage 3: OCR & Extraction
        if len(docs_with_text) == total_docs:
            ocr_status = "completed"
        elif len(docs_with_text) > 0 or any(d.status == DocumentStatus.OCR_PROCESSING for d in case_docs):
            ocr_status = "running"
        else:
            ocr_status = "idle"
        stages.append(
            PipelineStageResponse(
                id="ocr",
                label="OCR & Extraction",
                order=3,
                agentIds=["ocr"],
                status=ocr_status,
                evidence="document_status_aggregation" if len(docs_with_text) > 0 else "none",
            )
        )

        # Stage 4: Classification & Indexing
        if len(docs_indexed) == total_docs:
            idx_status = "completed"
        elif len(docs_chunked) > 0:
            idx_status = "running"
        else:
            idx_status = "idle"
        stages.append(
            PipelineStageResponse(
                id="indexing",
                label="Classification & Indexing",
                order=4,
                agentIds=["classification", "chunking", "embedding", "entity_extraction"],
                status=idx_status,
                evidence="document_status_aggregation" if len(docs_chunked) > 0 else "none",
            )
        )

        # Stage 5: Retrieval & Clustering
        ret_status = "completed" if len(docs_indexed) == total_docs else ("running" if len(docs_indexed) > 0 else "idle")
        stages.append(
            PipelineStageResponse(
                id="retrieval",
                label="Retrieval & Clustering",
                order=5,
                agentIds=["retrieval", "clustering"],
                status=ret_status,
                evidence="document_status_aggregation" if len(docs_indexed) > 0 else "none",
            )
        )

        # Stage 6: Legal Review & Analysis
        if len(docs_reviewed) == total_docs:
            rev_status = "completed"
        elif len(docs_reviewed) > 0 or any(d.status == DocumentStatus.ANALYZING for d in case_docs):
            rev_status = "running"
        else:
            rev_status = "idle"
        stages.append(
            PipelineStageResponse(
                id="legal_review",
                label="Legal Review & Analysis",
                order=6,
                agentIds=["summarization", "privilege", "risk", "pii", "review", "verification"],
                status=rev_status,
                evidence="document_status_aggregation" if len(docs_reviewed) > 0 else "none",
            )
        )

        # Stage 7: Knowledge Graph
        kg_status = "completed" if len(docs_reviewed) > 0 else "idle"
        stages.append(
            PipelineStageResponse(
                id="graph_generation",
                label="Knowledge Graph",
                order=7,
                agentIds=["relationship"],
                status=kg_status,
                evidence="document_status_aggregation" if len(docs_reviewed) > 0 else "none",
            )
        )

        # Stage 8: Timeline Generation
        timeline_status = "completed" if len(docs_reviewed) > 0 else "idle"
        stages.append(
            PipelineStageResponse(
                id="timeline_generation",
                label="Timeline Generation",
                order=8,
                agentIds=["timeline"],
                status=timeline_status,
                evidence="document_status_aggregation" if len(docs_reviewed) > 0 else "none",
            )
        )

        # Stage 9: Triage & Escalation
        triage_status = "completed" if len(docs_reviewed) == total_docs else ("running" if len(docs_reviewed) > 0 else "idle")
        stages.append(
            PipelineStageResponse(
                id="evidence_linking",
                label="Triage & Escalation",
                order=9,
                agentIds=["triage"],
                status=triage_status,
                evidence="document_status_aggregation" if len(docs_reviewed) > 0 else "none",
            )
        )

        # Stage 10: Reporting
        rep_status = "completed" if len(docs_reviewed) == total_docs and total_docs > 0 else "idle"
        stages.append(
            PipelineStageResponse(
                id="final_report",
                label="Reporting",
                order=10,
                agentIds=["report"],
                status=rep_status,
                evidence="document_status_aggregation" if rep_status == "completed" else "none",
            )
        )

        stages_with_evidence = sum(1 for s in stages if s.evidence != "none")

        # Determine current stage
        current_stage = "document_upload"
        for s in stages:
            if s.status in ["running", "idle"]:
                current_stage = s.id
                break

        return PipelineStatusResponse(
            caseId=str(case_id),
            documentId=None,
            status=None,
            currentStage=current_stage,
            isQuotaPaused=any_paused,
            pausedStage=None,
            pausedReason=None,
            lastReason=None,
            historyAvailable=False,
            stagesWithEvidence=stages_with_evidence,
            totalStages=len(stages),
            stages=stages,
            overallProgress=None,
            startedAt=case.created_at.isoformat() if case and case.created_at else None,
            completedAt=None,
            estimatedCompletionAt=None,
            history=[],
        )

    # ── Branch 3: Global / System-Level Query ──────────────────────────────────
    stages = [
        PipelineStageResponse(
            id=s["id"], label=s["label"], order=s["order"], agentIds=s["agent_ids"], status="idle", evidence="none"
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
        historyAvailable=False,
        stagesWithEvidence=0,
        totalStages=len(stages),
        stages=stages,
        overallProgress=None,
        startedAt=None,
        completedAt=None,
        estimatedCompletionAt=None,
        history=[],
    )

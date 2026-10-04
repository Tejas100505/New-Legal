"""
Document API routes.

Handles file uploads and document retrieval. Business logic is delegated
to DocumentService; routes handle HTTP concerns only.

All endpoints require JWT authentication. DELETE requires LAWYER or ADMIN role.

Document Ownership & Scoping:
    The Document model includes an `uploaded_by` FK to users.id.
    Documents associated with a Case inherit access through the Case.
    Documents with case_id=None are strictly scoped to the uploading user
    (matching current_user.sub), while ADMIN users have global oversight.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter

from datetime import datetime, timezone

from app.services.orchestrator import run_document_pipeline

from app.db.session import get_db
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    HumanOverrideRequest,
    OverrideField,
    OverrideAction,
    StatusHistoryResponse,
    PipelineStatusResponse,
)
from app.services.status_history_service import (
    record_status_transition,
    get_pipeline_execution_status,
)
from app.services.document_service import DocumentService
from app.auth.dependencies import get_current_user, require_role, TokenPayload, UserRole

router = APIRouter(prefix="/documents", tags=["Documents"])


async def check_document_access(doc: Any, current_user: TokenPayload, db: AsyncSession) -> None:
    """
    Enforce document access control scoping.
    - ADMIN role users have global oversight across all documents.
    - Documents associated with a case inherit access through the Case owner (case.created_by).
    - Documents with case_id=None are strictly scoped to the uploading user (uploaded_by).
    """
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


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="Upload a PDF, text, DOCX, or email file for e-discovery review.",
)
@limiter.limit("60/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload"),
    case_id: uuid.UUID | None = Query(None, description="Optional case to attach to"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> DocumentUploadResponse:
    """Upload and register a document for processing."""
    if case_id is not None and current_user.role != UserRole.ADMIN:
        from app.models.case import Case
        target_case = await db.get(Case, case_id)
        if not target_case or target_case.created_by != current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot upload to a case you do not own.",
            )

    service = DocumentService(db)
    user_uuid = None
    if current_user and current_user.sub:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except Exception:
            pass

    try:
        result = await service.upload_document(file, case_id=case_id, uploaded_by=user_uuid)
        # Commit the transaction so the background task can see the document
        await db.commit()
        # Trigger dynamic agent pipeline in the background
        background_tasks.add_task(run_document_pipeline, str(result.id))
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/upload-multiple",
    response_model=list[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Batch upload documents",
)
@limiter.limit("10/minute")
async def upload_multiple_documents(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="List of files to upload"),
    case_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[DocumentUploadResponse]:
    """Upload multiple documents in a single request."""
    if case_id is not None and current_user.role != UserRole.ADMIN:
        from app.models.case import Case
        target_case = await db.get(Case, case_id)
        if not target_case or target_case.created_by != current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot upload to a case you do not own.",
            )

    service = DocumentService(db)
    user_uuid = None
    if current_user and current_user.sub:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except Exception:
            pass

    results = []
    for file in files:
        try:
            res = await service.upload_document(file, case_id=case_id, uploaded_by=user_uuid)
            await db.commit()
            background_tasks.add_task(run_document_pipeline, str(res.id))
            results.append(res)
        except Exception as e:
            continue
    return results


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> DocumentResponse:
    """Fetch a single document by ID."""
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    await check_document_access(doc, current_user, db)
    return doc


@router.get(
    "/{document_id}/download",
    summary="Download raw document file",
)
async def get_document_file(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> StreamingResponse:
    """Download or stream raw document file."""
    import io
    from fastapi.responses import StreamingResponse
    from app.repositories.document_repository import DocumentRepository
    from app.services.storage_service import get_storage_service, StorageException

    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await check_document_access(doc, current_user, db)
    if not doc.storage_path:
        raise HTTPException(status_code=404, detail="Document file not found")

    storage_service = get_storage_service()
    try:
        content = await storage_service.download_document_file(doc.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File content missing on storage")
    except StorageException as e:
        raise HTTPException(status_code=502, detail=f"Storage backend error: {e}")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=doc.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )


@router.get(
    "/{document_id}/content",
    summary="Get document extracted text content",
)
async def get_document_content(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> dict:
    """Fetch extracted text and metadata for inline viewing."""
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await check_document_access(doc, current_user, db)
    
    return {
        "id": str(doc.id),
        "filename": doc.original_filename,
        "content_type": doc.content_type,
        "page_count": doc.page_count or 1,
        "extracted_text": doc.extracted_text or None,
        "doc_metadata": doc.doc_metadata or {},
    }


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update document status or metadata",
)
async def update_document(
    document_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> DocumentResponse:
    """Update document status or metadata by ID."""
    from app.repositories.document_repository import DocumentRepository
    from app.models.document import DocumentStatus
    from app.models.audit_log import AuditLog
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await check_document_access(doc, current_user, db)
    
    if "status" in payload:
        new_status = payload["status"]
        target_status = None
        if hasattr(DocumentStatus, new_status.upper()):
            target_status = getattr(DocumentStatus, new_status.upper())
        elif new_status in [s.value for s in DocumentStatus]:
            target_status = DocumentStatus(new_status)
        if target_status:
            await record_status_transition(
                db,
                doc,
                target_status,
                changed_by=current_user.sub,
                reason="manual_update_via_patch",
            )

    audit_log = AuditLog(
        user_email=current_user.email or f"user:{current_user.sub}",
        action=f"DOCUMENT_{payload.get('status', 'UPDATED').upper()}",
        resource_type="document",
        resource_id=str(doc.id),
        details={"status": str(doc.status.value)}
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.post(
    "/{document_id}/override",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit human review confirmation or override",
    description="Record a human decision confirming or overriding AI-generated tags (privilege, relevance, etc.) with auditable reason.",
)
async def override_document_review(
    document_id: uuid.UUID,
    data: HumanOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> DocumentResponse:
    """Record a human confirmation or override for an AI-suggested tag."""
    from app.repositories.document_repository import DocumentRepository
    from app.models.document import DocumentStatus
    from app.models.audit_log import AuditLog

    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await check_document_access(doc, current_user, db)

    reviewer_identity = current_user.email or f"user:{current_user.sub}"
    now_iso = datetime.now(timezone.utc).isoformat()

    doc_metadata = dict(doc.doc_metadata or {})
    human_overrides = list(doc_metadata.get("human_overrides", []))

    override_record = {
        "id": f"ovr_{uuid.uuid4().hex[:8]}",
        "field": data.field.value,
        "action": data.action.value,
        "override_value": data.override_value,
        "original_ai_value": data.original_ai_value,
        "ai_confidence": data.ai_confidence,
        "reason": data.reason,
        "reviewed_by": reviewer_identity,
        "reviewed_at": now_iso,
    }
    human_overrides.append(override_record)
    doc_metadata["human_overrides"] = human_overrides
    doc_metadata["review_status"] = "reviewed_by_human"
    doc_metadata["reviewed_by"] = reviewer_identity
    doc_metadata["reviewed_at"] = now_iso

    # Apply field-specific updates
    if data.field == OverrideField.PRIVILEGE:
        is_priv = bool(data.override_value)
        if "privilege_analysis" in doc_metadata and isinstance(doc_metadata["privilege_analysis"], dict):
            doc_metadata["privilege_analysis"]["is_privileged"] = is_priv
            doc_metadata["privilege_analysis"]["human_overridden"] = (data.action == OverrideAction.OVERRIDE)
        else:
            doc_metadata["privilege_analysis"] = {
                "is_privileged": is_priv,
                "confidence_score": 1.0,
                "human_overridden": (data.action == OverrideAction.OVERRIDE),
                "reasoning": f"Human review override: {data.reason}",
            }
        if "privilege" in doc_metadata and isinstance(doc_metadata["privilege"], dict):
            doc_metadata["privilege"]["is_privileged"] = is_priv

    elif data.field == OverrideField.RELEVANCE:
        doc_metadata["relevance"] = data.override_value

    elif data.field == OverrideField.CONFIDENTIALITY:
        doc_metadata["confidentiality"] = data.override_value

    if data.new_status:
        await record_status_transition(
            db,
            doc,
            data.new_status,
            changed_by=current_user.sub,
            reason=f"human_review_{data.action.value}:{data.field.value}",
        )

    doc.doc_metadata = doc_metadata

    # Create audit log record
    user_uuid = None
    try:
        user_uuid = uuid.UUID(current_user.sub)
    except Exception:
        pass

    action_label = "HUMAN_OVERRIDE" if data.action == OverrideAction.OVERRIDE else "HUMAN_CONFIRM"
    audit_entry = AuditLog(
        user_id=user_uuid,
        user_email=reviewer_identity,
        action=f"DOCUMENT_{action_label}_{data.field.value.upper()}",
        resource_type="document",
        resource_id=str(doc.id),
        details={
            "field": data.field.value,
            "action": data.action.value,
            "override_value": data.override_value,
            "original_ai_value": data.original_ai_value,
            "ai_confidence": data.ai_confidence,
            "reason": data.reason,
            "reviewer": reviewer_identity,
            "reviewed_at": now_iso,
        }
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(UserRole.LAWYER, UserRole.ADMIN)),
) -> None:
    """Delete a document by ID. Requires LAWYER or ADMIN role."""
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    await check_document_access(doc, current_user, db)
    deleted = await service.delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
)
async def list_documents(
    case_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    include_content: bool = Query(False, description="Include full extracted text"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> DocumentListResponse:
    """List documents with case filter and pagination, scoped to owner unless admin."""
    from app.models.case import Case
    from app.models.document import Document
    from sqlalchemy import select, func, or_, and_

    # If specific case_id requested, verify access upfront
    if case_id is not None and current_user.role != UserRole.ADMIN:
        target_case = await db.get(Case, case_id)
        if not target_case or target_case.created_by != current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you do not have permission to access documents for this case.",
            )

    offset = (page - 1) * page_size
    stmt = select(Document)

    if case_id is not None:
        stmt = stmt.where(Document.case_id == case_id)
    elif current_user.role != UserRole.ADMIN:
        user_uuid = None
        if current_user.sub:
            try:
                user_uuid = uuid.UUID(current_user.sub)
            except Exception:
                pass
        case_subq = select(Case.id).where(Case.created_by == current_user.sub)
        stmt = stmt.where(
            or_(
                Document.case_id.in_(case_subq),
                and_(Document.case_id.is_(None), Document.uploaded_by == user_uuid),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
    docs = (await db.execute(stmt)).scalars().all()

    results = []
    for d in docs:
        item = DocumentResponse.model_validate(d)
        if not include_content:
            item.extracted_text = None
        results.append(item)

    return DocumentListResponse(
        documents=results, total=total, page=page, page_size=page_size
    )


@router.post(
    "/{document_id}/retry",
    response_model=DocumentResponse,
    summary="Retry document processing pipeline",
    description="Resumes the document pipeline from the paused stage with preserved upstream results.",
)
@limiter.limit("10/minute")
async def retry_document_pipeline(
    request: Request,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> DocumentResponse:
    from app.models.document import Document, DocumentStatus
    from app.models.audit_log import AuditLog

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    await check_document_access(doc, current_user, db)

    if doc.status not in [DocumentStatus.QUOTA_PAUSED, DocumentStatus.ERROR]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry document in '{doc.status.value if hasattr(doc.status, 'value') else doc.status}' status. Only quota_paused or error documents can be retried.",
        )

    meta = dict(doc.doc_metadata or {})
    paused_stage = meta.get("paused_stage") or (meta.get("quota_pause") or {}).get("paused_at_stage")
    pipeline_data = meta.get("pipeline", {})
    preserved_stages = [
        k for k, v in pipeline_data.items()
        if isinstance(v, dict) and v.get("status") == "completed"
    ]

    # Reset status to VALIDATING to reflect active re-entry into pipeline
    await record_status_transition(
        db,
        doc,
        DocumentStatus.VALIDATING,
        changed_by=current_user.sub,
        reason="retry_requested",
    )
    meta["retry_initiated_at"] = datetime.now(timezone.utc).isoformat()
    meta["retry_initiated_by"] = current_user.sub or current_user.email
    meta["retry_available"] = False
    doc.doc_metadata = meta

    audit_log = AuditLog(
        user_email=current_user.email or "user@system.local",
        action="DOCUMENT_RETRY_INITIATED",
        resource_type="document",
        resource_id=str(doc.id),
        details={
            "filename": doc.original_filename,
            "resumed_from_stage": paused_stage,
            "preserved_stages": preserved_stages,
        },
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(doc)

    background_tasks.add_task(run_document_pipeline, str(doc.id))

    return DocumentResponse.model_validate(doc)


@router.get(
    "/{document_id}/status-history",
    response_model=list[StatusHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get document status history",
)
async def get_document_status_history(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> list[StatusHistoryResponse]:
    """Retrieve the full, chronologically ordered status transition audit trail for a document."""
    from sqlalchemy import select
    from app.models.document import Document
    from app.models.status_history import StatusHistory

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
    await check_document_access(doc, current_user, db)

    stmt = (
        select(StatusHistory)
        .where(StatusHistory.document_id == document_id)
        .order_by(StatusHistory.changed_at.asc(), StatusHistory.created_at.asc())
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()
    return [StatusHistoryResponse.model_validate(e) for e in entries]


@router.get(
    "/{document_id}/pipeline-status",
    response_model=PipelineStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document pipeline execution status",
)
async def get_document_pipeline_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> PipelineStatusResponse:
    """
    Retrieve real, case-scoped, document-scoped pipeline execution status backed by status_history.
    """
    return await get_pipeline_execution_status(
        db=db,
        current_user=current_user,
        document_id=document_id,
    )



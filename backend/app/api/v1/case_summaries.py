"""
Case Summary API routes.

Provides endpoints for generating and retrieving case-level executive summaries:
- POST /api/v1/cases/{case_id}/summary/generate
- GET /api/v1/cases/{case_id}/summary

Both endpoints strictly enforce creator-only + admin-override security via get_case_scoped_document_ids.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, TokenPayload, UserRole
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.case import Case
from app.models.case_summary import CaseSummary, CaseSummaryStatus
from app.models.document import Document
from app.repositories.case_summary_repository import CaseSummaryRepository
from app.services.case_intelligence_service import (
    compute_case_data_hash,
    generate_case_summary,
)
from app.services.case_scoping import get_case_scoped_document_ids

router = APIRouter(tags=["Case Summaries"])


@router.post(
    "/cases/{case_id}/summary/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate Case-Level Executive Summary",
)
@limiter.limit("2/minute")
async def generate_case_summary_endpoint(
    request: Request,
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generate or regenerate a synthesized case-level executive summary.
    
    Enforces:
    - Creator-only / Admin-override authorization via get_case_scoped_document_ids
    - Rate limit: 2/minute per client
    - Concurrency guard: 409 Conflict if GENERATING is already in flight
    - Quota-exhaustion handling: 503 Service Unavailable on QuotaExhaustedException
    """
    # 1. Authorize case access using get_case_scoped_document_ids
    # Raises 403 if user does not own the case (and is not admin)
    await get_case_scoped_document_ids(db, case_id, current_user)

    # 2. Check case existence
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    user_uuid: Optional[uuid.UUID] = None
    if current_user.sub:
        try:
            parsed_sub = uuid.UUID(current_user.sub)
            from app.models.user import User
            existing_user = await db.get(User, parsed_sub)
            if existing_user:
                user_uuid = parsed_sub
        except (ValueError, TypeError):
            user_uuid = None

    # 3. Call case_intelligence_service
    summary = await generate_case_summary(db, case_id, user_id=user_uuid)

    return {
        "id": str(summary.id),
        "case_id": str(summary.case_id),
        "status": summary.status.value,
        "source_doc_count": summary.source_doc_count,
        "source_data_hash": summary.source_data_hash,
        "model_version": summary.model_version,
        "generated_at": summary.generated_at.isoformat() if summary.generated_at else None,
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
        "summary_json": summary.summary_json,
        "stale": False,
        "generating": False,
    }


@router.get(
    "/cases/{case_id}/summary",
    status_code=status.HTTP_200_OK,
    summary="Get Latest Case-Level Executive Summary",
)
async def get_case_summary_endpoint(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve the latest executive summary for a case.
    
    Behavior per state machine:
    - 404 if no summary exists for the case.
    - If status == GENERATING: returns previous COMPLETE summary (if any) with generating: True.
      If no previous COMPLETE exists, returns generating status without summary payload.
    - If status == COMPLETE: checks live source_data_hash. If mismatch, adds stale: True (never regenerates).
    - If status == FAILED / QUOTA_PAUSED: returns previous COMPLETE summary (if any) with
      failed_last_generation: True. If no previous COMPLETE exists, returns status.
    """
    # 1. Authorize case access using get_case_scoped_document_ids
    await get_case_scoped_document_ids(db, case_id, current_user)

    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    repo = CaseSummaryRepository(db)
    latest = await repo.get_latest_by_case_id(case_id)

    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary generated yet for this case",
        )

    # Compute current live hash to determine staleness
    docs_stmt = select(Document).where(Document.case_id == case_id)
    docs_res = await db.execute(docs_stmt)
    docs = list(docs_res.scalars().all())
    live_hash = compute_case_data_hash(docs) if docs else ""

    # Check if currently generating
    if latest.status == CaseSummaryStatus.GENERATING:
        # Find latest COMPLETE summary if one exists
        stmt = (
            select(CaseSummary)
            .where(
                CaseSummary.case_id == case_id,
                CaseSummary.status == CaseSummaryStatus.COMPLETE,
            )
            .order_by(CaseSummary.created_at.desc())
            .limit(1)
        )
        complete_res = await db.execute(stmt)
        prev_complete = complete_res.scalars().first()

        if prev_complete:
            is_stale = (prev_complete.source_data_hash != live_hash)
            return {
                "id": str(prev_complete.id),
                "case_id": str(prev_complete.case_id),
                "status": prev_complete.status.value,
                "source_doc_count": prev_complete.source_doc_count,
                "source_data_hash": prev_complete.source_data_hash,
                "model_version": prev_complete.model_version,
                "generated_at": prev_complete.generated_at.isoformat() if prev_complete.generated_at else None,
                "created_at": prev_complete.created_at.isoformat() if prev_complete.created_at else None,
                "summary_json": prev_complete.summary_json,
                "stale": is_stale,
                "generating": True,
            }
        else:
            return {
                "id": str(latest.id),
                "case_id": str(latest.case_id),
                "status": latest.status.value,
                "source_doc_count": latest.source_doc_count,
                "source_data_hash": latest.source_data_hash,
                "model_version": latest.model_version,
                "generated_at": None,
                "created_at": latest.created_at.isoformat() if latest.created_at else None,
                "summary_json": None,
                "stale": False,
                "generating": True,
            }

    # If latest status is FAILED or QUOTA_PAUSED, serve previous COMPLETE if available
    if latest.status in (CaseSummaryStatus.FAILED, CaseSummaryStatus.QUOTA_PAUSED):
        stmt = (
            select(CaseSummary)
            .where(
                CaseSummary.case_id == case_id,
                CaseSummary.status == CaseSummaryStatus.COMPLETE,
            )
            .order_by(CaseSummary.created_at.desc())
            .limit(1)
        )
        complete_res = await db.execute(stmt)
        prev_complete = complete_res.scalars().first()

        if prev_complete:
            is_stale = (prev_complete.source_data_hash != live_hash)
            return {
                "id": str(prev_complete.id),
                "case_id": str(prev_complete.case_id),
                "status": prev_complete.status.value,
                "source_doc_count": prev_complete.source_doc_count,
                "source_data_hash": prev_complete.source_data_hash,
                "model_version": prev_complete.model_version,
                "generated_at": prev_complete.generated_at.isoformat() if prev_complete.generated_at else None,
                "created_at": prev_complete.created_at.isoformat() if prev_complete.created_at else None,
                "summary_json": prev_complete.summary_json,
                "stale": is_stale,
                "generating": False,
                "failed_last_generation": True,
                "last_generation_status": latest.status.value,
            }

    # Latest is COMPLETE (or standard non-generating)
    is_stale = (latest.source_data_hash != live_hash)
    return {
        "id": str(latest.id),
        "case_id": str(latest.case_id),
        "status": latest.status.value,
        "source_doc_count": latest.source_doc_count,
        "source_data_hash": latest.source_data_hash,
        "model_version": latest.model_version,
        "generated_at": latest.generated_at.isoformat() if latest.generated_at else None,
        "created_at": latest.created_at.isoformat() if latest.created_at else None,
        "summary_json": latest.summary_json,
        "stale": is_stale,
        "generating": False,
    }

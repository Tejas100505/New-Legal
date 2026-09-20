"""
Shared Case Scoping Helper for access control and multi-tenant isolation.

Centralizes case-scoping queries across services, guaranteeing creator-only
ownership boundaries and admin-override semantics without modifying existing
security-critical route logic.
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.case import Case
from app.models.document import Document
from app.auth.dependencies import TokenPayload, UserRole


async def get_case_scoped_document_ids(
    db: AsyncSession,
    case_id: Optional[uuid.UUID],
    current_user: TokenPayload,
) -> List[uuid.UUID]:
    """
    Retrieve document IDs accessible to current_user.

    Enforces the existing creator-only + admin-override access model:
    - If user is ADMIN:
      - With case_id: returns all document IDs belonging to that case.
      - Without case_id (None): returns all document IDs in the system.
    - If user is non-ADMIN:
      - With case_id: verifies case exists and case.created_by == current_user.sub.
        Raises 403 Forbidden if not owned/accessible, then returns document IDs for that case.
      - Without case_id (None): returns document IDs for cases created by current_user
        plus orphan documents (case_id is None) uploaded by current_user (uploaded_by == user_uuid).
    """
    # 1. When a specific case_id is requested
    if case_id is not None:
        if current_user.role != UserRole.ADMIN:
            case = await db.get(Case, case_id)
            if not case or case.created_by != current_user.sub:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this case",
                )
        stmt = select(Document.id).where(Document.case_id == case_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 2. When case_id is None (global query for accessible documents)
    if current_user.role == UserRole.ADMIN:
        stmt = select(Document.id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # Non-admin global scoping: owned cases or orphan docs uploaded by user
    user_uuid: Optional[uuid.UUID] = None
    if current_user.sub:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except (ValueError, TypeError):
            user_uuid = None

    accessible_filter = (Case.created_by == current_user.sub)
    if user_uuid is not None:
        accessible_filter = accessible_filter | (
            (Document.case_id.is_(None)) & (Document.uploaded_by == user_uuid)
        )

    stmt = (
        select(Document.id)
        .outerjoin(Case, Document.case_id == Case.id)
        .where(accessible_filter)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

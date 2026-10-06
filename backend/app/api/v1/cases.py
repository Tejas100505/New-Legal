"""
Case management API routes.

Full CRUD for legal cases — create, read, update, delete.
All endpoints require JWT authentication. DELETE requires LAWYER or ADMIN role.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.case import CaseCreate, CaseListResponse, CaseResponse, CaseUpdate
from app.services.case_service import CaseService
from app.auth.dependencies import get_current_user, require_role, TokenPayload, UserRole

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new case",
)
async def create_case(
    data: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> CaseResponse:
    """Create a new legal case/matter, associating with current user."""
    service = CaseService(db)
    return await service.create_case(data, created_by=current_user.sub)


@router.get(
    "",
    response_model=CaseListResponse,
    summary="List cases",
)
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_fixtures: bool = Query(False, description="Whether to include system/integration test fixtures"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> CaseListResponse:
    """List cases with pagination, scoped to owner unless admin, excluding system fixtures by default."""
    service = CaseService(db)
    created_by_filter = None if current_user.role == UserRole.ADMIN else current_user.sub
    cases, total = await service.list_cases(
        created_by=created_by_filter,
        include_fixtures=include_fixtures,
        page=page,
        page_size=page_size,
    )
    return CaseListResponse(
        cases=cases, total=total, page=page, page_size=page_size
    )


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Get case details",
)
async def get_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> CaseResponse:
    """Fetch a single case by ID with owner access verification."""
    service = CaseService(db)
    case = await service.get_case(case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )
    if current_user.role != UserRole.ADMIN and case.created_by != current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to access this case.",
        )
    return case


@router.put(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Update a case",
)
async def update_case(
    case_id: uuid.UUID,
    data: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> CaseResponse:
    """Update an existing case with owner access verification."""
    service = CaseService(db)
    existing_case = await service.get_case(case_id)
    if existing_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )
    if current_user.role != UserRole.ADMIN and existing_case.created_by != current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to update this case.",
        )
    case = await service.update_case(case_id, data)
    return case


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a case",
)
async def delete_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(UserRole.LAWYER, UserRole.ADMIN)),
) -> None:
    """Delete a case and all associated documents. Requires owner or ADMIN role."""
    service = CaseService(db)
    existing_case = await service.get_case(case_id)
    if existing_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )
    if current_user.role != UserRole.ADMIN and existing_case.created_by != current_user.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to delete this case.",
        )
    await service.delete_case(case_id)

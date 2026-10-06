"""
Case service — business logic for legal case management.
"""

from __future__ import annotations

import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.case_repository import CaseRepository
from app.schemas.case import CaseCreate, CaseResponse, CaseUpdate


class CaseService:
    """Handles case CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = CaseRepository(session)

    async def create_case(
        self, data: CaseCreate, created_by: str | None = None
    ) -> CaseResponse:
        """Create a new legal case with optional matter number, client, and case type."""
        case_number = data.case_number or f"CASE-{str(uuid.uuid4())[:8].upper()}"
        case = await self._repo.create_case(
            name=data.name,
            case_number=case_number,
            matter_number=data.matter_number,
            client=data.client,
            case_type=data.case_type,
            description=data.description,
            priority=data.priority,
            tags=data.tags,
            created_by=created_by,
            is_system_fixture=data.is_system_fixture,
        )
        logger.info("Created case", case_id=str(case.id), name=case.name)
        return CaseResponse(
            id=case.id,
            name=case.name,
            case_number=case.case_number,
            matter_number=case.matter_number,
            client=case.client,
            case_type=case.case_type,
            description=case.description,
            status=case.status,
            priority=case.priority,
            tags=case.tags or [],
            created_by=case.created_by,
            is_system_fixture=case.is_system_fixture,
            document_count=0,
            reviewed_count=0,
            flagged_count=0,
            privileged_count=0,
            high_risk_count=0,
            processing_count=0,
            last_activity=case.created_at,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    async def get_case(self, case_id: uuid.UUID) -> CaseResponse | None:
        """Fetch a case with its full legal telemetry."""
        result = await self._repo.get_with_telemetry(case_id)
        if result is None:
            return None
        case = result["case"]
        return CaseResponse(
            id=case.id,
            name=case.name,
            case_number=case.case_number,
            matter_number=case.matter_number,
            client=case.client,
            case_type=case.case_type,
            description=case.description,
            status=case.status,
            priority=case.priority,
            tags=case.tags or [],
            created_by=case.created_by,
            is_system_fixture=case.is_system_fixture,
            document_count=result["document_count"],
            reviewed_count=result["reviewed_count"],
            flagged_count=result["flagged_count"],
            privileged_count=result["privileged_count"],
            high_risk_count=result["high_risk_count"],
            processing_count=result["processing_count"],
            last_activity=result["last_activity"],
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    async def list_cases(
        self,
        *,
        created_by: str | None = None,
        include_fixtures: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CaseResponse], int]:
        """List cases with pagination and real telemetry, optionally scoped to creator and fixture status."""
        offset = (page - 1) * page_size
        case_rows = await self._repo.get_all_with_counts(
            created_by=created_by,
            include_fixtures=include_fixtures,
            offset=offset,
            limit=page_size,
        )
        total = await self._repo.count_cases(
            created_by=created_by,
            include_fixtures=include_fixtures,
        )
        return [
            CaseResponse(
                id=c.id,
                name=c.name,
                case_number=c.case_number,
                matter_number=c.matter_number,
                client=c.client,
                case_type=c.case_type,
                description=c.description,
                status=c.status,
                priority=c.priority,
                tags=c.tags or [],
                created_by=c.created_by,
                is_system_fixture=c.is_system_fixture,
                document_count=doc_count,
                reviewed_count=reviewed_count,
                flagged_count=flagged_count,
                privileged_count=privileged_count,
                high_risk_count=high_risk_count,
                processing_count=processing_count,
                last_activity=last_activity,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c, doc_count, reviewed_count, flagged_count, privileged_count, high_risk_count, processing_count, last_activity in case_rows
        ], total

    async def update_case(
        self, case_id: uuid.UUID, data: CaseUpdate
    ) -> CaseResponse | None:
        """Update a case's mutable fields."""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_case(case_id)
        case = await self._repo.update(case_id, **update_data)
        if case is None:
            return None
        return await self.get_case(case_id)

    async def delete_case(self, case_id: uuid.UUID) -> bool:
        """Delete a case and its associated documents."""
        deleted = await self._repo.delete(case_id)
        if deleted:
            logger.info("Deleted case", case_id=str(case_id))
        return deleted

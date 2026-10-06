"""
Case repository — database access for legal cases.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.case import Case, CasePriority, CaseStatus
from app.models.document import Document, DocumentStatus
from app.repositories.base import BaseRepository


class CaseRepository(BaseRepository[Case]):
    """Data access layer for legal cases."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Case, session)

    @staticmethod
    def _build_telemetry_columns():
        """Construct database-side aggregation expressions for case telemetry."""
        is_reviewed = or_(
            Document.status == DocumentStatus.REVIEWED,
            Document.doc_metadata["review_status"].astext == "reviewed",
        )
        is_flagged = or_(
            Document.status == DocumentStatus.FLAGGED,
            Document.doc_metadata["review_status"].astext == "flagged",
        )
        is_processing = Document.status.in_([
            DocumentStatus.UPLOADED,
            DocumentStatus.VALIDATING,
            DocumentStatus.OCR_PROCESSING,
            DocumentStatus.CHUNKING,
            DocumentStatus.EMBEDDING,
            DocumentStatus.ANALYZING,
            DocumentStatus.QUOTA_PAUSED,
        ])
        is_privileged = or_(
            cast(Document.doc_metadata["privilege"]["is_privileged"].astext, Boolean) == True,
            cast(Document.doc_metadata["triage"]["signal_summary"]["is_privileged"].astext, Boolean) == True,
            cast(Document.doc_metadata["is_privileged"].astext, Boolean) == True,
        )
        is_high_risk = or_(
            func.upper(func.coalesce(Document.doc_metadata["risk"]["overall_risk"].astext, "")) == "HIGH",
            func.upper(func.coalesce(Document.doc_metadata["triage"]["signal_summary"]["risk_level"].astext, "")) == "HIGH",
            func.upper(func.coalesce(Document.doc_metadata["risk_level"].astext, "")) == "HIGH",
        )

        doc_count_col = func.count(Document.id).label("document_count")
        reviewed_col = func.count(case((is_reviewed, Document.id))).label("reviewed_count")
        flagged_col = func.count(case((is_flagged, Document.id))).label("flagged_count")
        privileged_col = func.count(case((is_privileged, Document.id))).label("privileged_count")
        high_risk_col = func.count(case((is_high_risk, Document.id))).label("high_risk_count")
        processing_col = func.count(case((is_processing, Document.id))).label("processing_count")
        last_activity_col = func.coalesce(func.max(Document.updated_at), Case.updated_at).label("last_activity")

        return (
            doc_count_col,
            reviewed_col,
            flagged_col,
            privileged_col,
            high_risk_col,
            processing_col,
            last_activity_col,
        )

    async def create_case(
        self,
        *,
        name: str,
        case_number: str | None = None,
        matter_number: str | None = None,
        client: str | None = None,
        case_type: str | None = None,
        description: str | None = None,
        priority: CasePriority = CasePriority.MEDIUM,
        tags: list[str] | dict | None = None,
        created_by: str | None = None,
        is_system_fixture: bool = False,
    ) -> Case:
        """Create and persist a new Case."""
        return await self.create(
            name=name,
            case_number=case_number,
            matter_number=matter_number,
            client=client,
            case_type=case_type,
            description=description,
            priority=priority,
            tags=tags,
            created_by=created_by,
            is_system_fixture=is_system_fixture,
        )

    async def get_with_telemetry(self, case_id: uuid.UUID) -> dict | None:
        """Fetch a case along with its full telemetry metrics."""
        cols = self._build_telemetry_columns()
        stmt = (
            select(Case, *cols)
            .options(noload(Case.documents))
            .outerjoin(Document, Document.case_id == Case.id)
            .where(Case.id == case_id)
            .group_by(Case.id)
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        case_obj = row[0]
        return {
            "case": case_obj,
            "document_count": row.document_count,
            "reviewed_count": row.reviewed_count,
            "flagged_count": row.flagged_count,
            "privileged_count": row.privileged_count,
            "high_risk_count": row.high_risk_count,
            "processing_count": row.processing_count,
            "last_activity": row.last_activity,
        }

    async def get_with_document_count(self, case_id: uuid.UUID) -> dict | None:
        """Fetch a case along with its telemetry (backward-compatible)."""
        return await self.get_with_telemetry(case_id)

    async def get_all_with_counts(
        self,
        *,
        created_by: str | None = None,
        include_fixtures: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> list[tuple]:
        """Fetch cases with real telemetry in a single efficient query, optionally scoped to created_by and fixture status."""
        cols = self._build_telemetry_columns()
        stmt = (
            select(Case, *cols)
            .options(noload(Case.documents))
            .outerjoin(Document, Document.case_id == Case.id)
            .group_by(Case.id)
            .order_by(Case.created_at.desc())
        )
        if not include_fixtures:
            stmt = stmt.where(Case.is_system_fixture.is_(False))
        if created_by is not None:
            stmt = stmt.where(Case.created_by == created_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.all())

    async def count_cases(
        self,
        *,
        created_by: str | None = None,
        include_fixtures: bool = False,
    ) -> int:
        """Return total count of cases, optionally scoped to creator and fixture status."""
        stmt = select(func.count()).select_from(Case)
        if not include_fixtures:
            stmt = stmt.where(Case.is_system_fixture.is_(False))
        if created_by is not None:
            stmt = stmt.where(Case.created_by == created_by)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def search_by_name(self, query: str, *, limit: int = 20) -> list[Case]:
        """Search cases by name (case-insensitive partial match)."""
        stmt = (
            select(Case)
            .where(Case.name.ilike(f"%{query}%"))
            .order_by(Case.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

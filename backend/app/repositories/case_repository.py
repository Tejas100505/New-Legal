"""
Case repository — database access for legal cases.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case, CaseStatus
from app.models.document import Document
from app.repositories.base import BaseRepository


class CaseRepository(BaseRepository[Case]):
    """Data access layer for legal cases."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Case, session)

    async def get_with_document_count(self, case_id: uuid.UUID) -> dict | None:
        """Fetch a case along with its document count."""
        case = await self.get_by_id(case_id)
        if case is None:
            return None
        count_stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.case_id == case_id)
        )
        result = await self._session.execute(count_stmt)
        doc_count = result.scalar_one()
        return {"case": case, "document_count": doc_count}

    async def get_all_with_counts(
        self, *, created_by: str | None = None, offset: int = 0, limit: int = 100
    ) -> list[tuple[Case, int]]:
        """Fetch cases with document counts in a single efficient query, optionally scoped to created_by."""
        stmt = (
            select(Case, func.count(Document.id))
            .outerjoin(Document, Document.case_id == Case.id)
            .group_by(Case.id)
            .order_by(Case.created_at.desc())
        )
        if created_by is not None:
            stmt = stmt.where(Case.created_by == created_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.all())

    async def count_cases(self, *, created_by: str | None = None) -> int:
        """Return total count of cases, optionally scoped to creator."""
        stmt = select(func.count()).select_from(Case)
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

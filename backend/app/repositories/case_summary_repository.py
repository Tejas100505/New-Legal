"""
CaseSummary repository — database access for case-level summaries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case_summary import CaseSummary, CaseSummaryStatus
from app.repositories.base import BaseRepository


class CaseSummaryRepository(BaseRepository[CaseSummary]):
    """Data access layer for case summaries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CaseSummary, session)

    async def get_latest_by_case_id(
        self, case_id: uuid.UUID | str
    ) -> CaseSummary | None:
        """Fetch the most recent summary for a case, ordered by created_at DESC."""
        if isinstance(case_id, str):
            try:
                case_id = uuid.UUID(case_id)
            except ValueError:
                pass

        stmt = (
            select(CaseSummary)
            .where(CaseSummary.case_id == case_id)
            .order_by(CaseSummary.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def update_status(
        self, id: uuid.UUID | str, status: CaseSummaryStatus | str
    ) -> CaseSummary | None:
        """Update the status of a case summary."""
        if isinstance(status, str):
            status = CaseSummaryStatus(status)
        return await self.update(id, status=status)

    async def update_completed(
        self,
        id: uuid.UUID | str,
        *,
        summary_json: dict[str, Any],
        model_version: str,
        generated_at: datetime | None = None,
    ) -> CaseSummary | None:
        """Mark a summary as complete with its generated payload and metadata."""
        if generated_at is None:
            generated_at = datetime.now(timezone.utc)
        return await self.update(
            id,
            summary_json=summary_json,
            model_version=model_version,
            generated_at=generated_at,
            status=CaseSummaryStatus.COMPLETE,
        )

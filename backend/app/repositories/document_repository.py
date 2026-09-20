"""
Document repository — database access for documents.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Data access layer for documents."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Document, session)

    async def get_by_case_id(
        self,
        case_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        """Fetch all documents belonging to a case."""
        stmt = (
            select(Document)
            .where(Document.case_id == case_id)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self, status: DocumentStatus, *, limit: int = 50
    ) -> Sequence[Document]:
        """Fetch documents with a given processing status."""
        stmt = (
            select(Document)
            .where(Document.status == status)
            .order_by(Document.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self, doc_id: uuid.UUID, status: DocumentStatus
    ) -> Document | None:
        """Update just the processing status of a document."""
        return await self.update(doc_id, status=status)

    async def get_by_checksum(self, checksum: str) -> Document | None:
        """Fetch a document by its SHA-256 checksum."""
        stmt = select(Document).where(Document.checksum_sha256 == checksum)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

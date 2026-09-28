"""
Chunk repository — database access and vector search for chunks.
"""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[DocumentChunk]):
    """Data access layer for document chunks and vector search."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentChunk, session)

    async def get_by_document_id(
        self, document_id: uuid.UUID
    ) -> Sequence[DocumentChunk]:
        """Fetch all chunks for a specific document."""
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def vector_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        filters: dict | None = None,
        min_chunk_chars: Optional[int] = None,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        """
        Perform a nearest-neighbor vector search using pgvector cosine distance,
        returning (chunk, cosine_similarity) tuples.
        Falls back to in-memory cosine similarity calculation via numpy if pgvector is unavailable.
        """
        try:
            distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)
            stmt = select(
                DocumentChunk,
                (1.0 - distance_expr).label("similarity")
            ).order_by(distance_expr).limit(limit)

            if min_chunk_chars is not None:
                stmt = stmt.where(func.length(DocumentChunk.text) >= min_chunk_chars)

            if filters:
                if "document_id" in filters:
                    stmt = stmt.where(DocumentChunk.document_id == filters["document_id"])
                if "document_ids" in filters:
                    doc_ids = list(filters["document_ids"])
                    if not doc_ids:
                        return []
                    stmt = stmt.where(DocumentChunk.document_id.in_(doc_ids))
                if "page" in filters:
                    stmt = stmt.where(DocumentChunk.page == filters["page"])

            result = await self._session.execute(stmt)
            rows = result.all()
            if rows:
                return [(row[0], float(row[1])) for row in rows]
        except Exception:
            pass

        # Fallback to in-memory cosine similarity calculation
        import numpy as np

        stmt = select(DocumentChunk)
        if min_chunk_chars is not None:
            stmt = stmt.where(func.length(DocumentChunk.text) >= min_chunk_chars)
        if filters:
            if "document_id" in filters:
                stmt = stmt.where(DocumentChunk.document_id == filters["document_id"])
            if "document_ids" in filters:
                doc_ids = list(filters["document_ids"])
                if not doc_ids:
                    return []
                stmt = stmt.where(DocumentChunk.document_id.in_(doc_ids))
            if "page" in filters:
                stmt = stmt.where(DocumentChunk.page == filters["page"])

        result = await self._session.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = float(np.linalg.norm(q_vec))
        if q_norm == 0.0:
            return []

        scored_chunks: list[tuple[DocumentChunk, float]] = []
        for chunk in chunks:
            emb = chunk.embedding
            if not emb or not isinstance(emb, list) or len(emb) != len(query_embedding):
                continue
            c_vec = np.array(emb, dtype=np.float32)
            c_norm = float(np.linalg.norm(c_vec))
            if c_norm == 0.0:
                continue
            sim = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
            scored_chunks.append((chunk, sim))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:limit]


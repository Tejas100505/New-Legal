"""
Document chunk model for Semantic Search.
"""

from __future__ import annotations

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentChunk(Base):
    """A semantically chunked piece of a legal document."""

    __tablename__ = "document_chunks"

    # Foreign key to document
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identifiers
    chunk_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Embeddings and metadata
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024).with_variant(JSON(), "sqlite"), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Relationship
    document = relationship("Document")

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.chunk_id} for Document {self.document_id}>"

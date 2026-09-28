"""
Document ORM model.

Represents a legal document uploaded for e-discovery review (PDF, email, text, etc.).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Enum as SAEnum, ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentStatus(str, enum.Enum):
    """Processing status of a document in the pipeline."""
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    OCR_PROCESSING = "ocr_processing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    ANALYZING = "analyzing"
    REVIEWED = "reviewed"
    FLAGGED = "flagged"
    QUOTA_PAUSED = "quota_paused"
    ERROR = "error"


class Document(Base):
    """A legal document uploaded for review within a case."""

    __tablename__ = "documents"

    # Foreign key to case
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Foreign key to user who uploaded the document
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Processing state
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, name="document_status", create_constraint=True, native_enum=False, length=50),
        default=DocumentStatus.UPLOADED,
        server_default=DocumentStatus.UPLOADED.value,
        nullable=False,
        index=True,
    )

    # Page/content info (populated after OCR)
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Flexible metadata store
    doc_metadata: Mapped[dict | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="documents")
    status_history = relationship(
        "StatusHistory",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at.asc()",
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} filename='{self.filename}' "
            f"status={self.status.value}>"
        )

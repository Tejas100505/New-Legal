"""
Document Status History ORM model.

Records every document status transition across pipeline stages and human interventions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StatusHistory(Base):
    """Audit trail for document status transitions."""

    __tablename__ = "status_history"

    # Foreign key to document (CASCADE delete: history belongs exclusively to the document)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Previous status (nullable for initial creation / upload)
    old_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Target status transitioned into
    new_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Timestamp of the transition
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # User who triggered the transition (nullable for automated pipeline transitions)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Contextual reason for the transition
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    document = relationship("Document", back_populates="status_history")
    user = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<StatusHistory id={self.id} doc={self.document_id} "
            f"{self.old_status} -> {self.new_status} reason='{self.reason}'>"
        )

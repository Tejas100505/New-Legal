"""
CaseSummary ORM model.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Integer, String, JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CaseSummaryStatus(str, enum.Enum):
    """Lifecycle status for a case-level summary."""
    GENERATING = "generating"
    COMPLETE = "complete"
    QUOTA_PAUSED = "quota_paused"
    FAILED = "failed"


class CaseSummary(Base):
    """Stores case-level executive summary generated from aggregated document metadata."""

    __tablename__ = "case_summaries"

    # Foreign key to case (CASCADE delete: summaries are case-scoped and cannot exist without a case)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Generated summary payload (JSONB in PostgreSQL, JSON in SQLite). NULL during GENERATING.
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )

    # Computable before generation starts — non-nullable, must be supplied by caller
    source_doc_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Hash of source data used to detect staleness — non-nullable
    source_data_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Model used for generation — NULL during GENERATING
    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # User who requested generation
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamp when generation succeeded — NULL until COMPLETE
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Lifecycle status
    status: Mapped[CaseSummaryStatus] = mapped_column(
        sa.Enum(
            CaseSummaryStatus,
            name="case_summary_status",
            native_enum=False,
            create_constraint=True,
            length=50,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=CaseSummaryStatus.GENERATING,
        server_default=CaseSummaryStatus.GENERATING.value,
    )

    # Relationships
    case = relationship("Case")
    generator = relationship("User")

    def __repr__(self) -> str:
        return f"<CaseSummary id={self.id} case_id={self.case_id} status='{self.status}'>"

"""
Case ORM model.

Represents a legal case/matter that groups related documents for review.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CasePriority(str, enum.Enum):
    """Priority level of a legal case."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseStatus(str, enum.Enum):
    """Lifecycle status of a legal case."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Case(Base):
    """A legal case/matter containing documents for e-discovery review."""

    __tablename__ = "cases"

    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    case_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, name="case_status", create_constraint=True, native_enum=False, length=50),
        default=CaseStatus.CREATED,
        server_default=CaseStatus.CREATED.value,
        nullable=False,
        index=True,
    )
    priority: Mapped[CasePriority] = mapped_column(
        SAEnum(CasePriority, name="case_priority", create_constraint=True, native_enum=False, length=50, values_callable=lambda obj: [e.value for e in obj]),
        default=CasePriority.MEDIUM,
        server_default=CasePriority.MEDIUM.value,
        nullable=False,
        index=True,
    )
    tags: Mapped[dict | list | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", type_=Text, nullable=True
    )

    # Relationships
    documents = relationship(
        "Document",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} name='{self.name}' status={self.status.value}>"

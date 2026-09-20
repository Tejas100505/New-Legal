"""
EvaluationMetric ORM model.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Float, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EvaluationMetric(Base):
    """Stores automated and user-feedback evaluation metrics for AI processing."""

    __tablename__ = "evaluation_metrics"

    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Specific metrics
    ocr_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    rouge_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    hallucination_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    graph_generation_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_usage: Mapped[dict[str, int] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    privilege_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_feedback: Mapped[dict[str, Any] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Relationships
    case = relationship("Case")
    document = relationship("Document")

    def __repr__(self) -> str:
        return f"<EvaluationMetric id={self.id} type='{self.metric_type}'>"

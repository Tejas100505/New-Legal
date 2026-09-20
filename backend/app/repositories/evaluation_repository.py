"""
Evaluation metrics repository.
"""

from __future__ import annotations

import uuid
from typing import Sequence, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import EvaluationMetric
from app.repositories.base import BaseRepository


class EvaluationRepository(BaseRepository[EvaluationMetric]):
    """Data access layer for evaluation metrics."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EvaluationMetric, session)

    async def get_by_case_id(self, case_id: uuid.UUID) -> Sequence[EvaluationMetric]:
        """Fetch all evaluation metrics for a case."""
        stmt = select(EvaluationMetric).where(EvaluationMetric.case_id == case_id).order_by(EvaluationMetric.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_document_id(self, doc_id: uuid.UUID) -> Sequence[EvaluationMetric]:
        """Fetch all evaluation metrics for a specific document."""
        stmt = select(EvaluationMetric).where(EvaluationMetric.document_id == doc_id).order_by(EvaluationMetric.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_aggregates_by_case(self, case_id: uuid.UUID | None = None) -> Dict[str, Any]:
        """Compute average metrics aggregated by case, or globally if case_id is None."""
        metrics_fields = [
            func.avg(EvaluationMetric.ocr_accuracy).label("avg_ocr_accuracy"),
            func.avg(EvaluationMetric.retrieval_precision).label("avg_retrieval_precision"),
            func.avg(EvaluationMetric.retrieval_recall).label("avg_retrieval_recall"),
            func.avg(EvaluationMetric.semantic_similarity).label("avg_semantic_similarity"),
            func.avg(EvaluationMetric.hallucination_rate).label("avg_hallucination_rate"),
            func.avg(EvaluationMetric.latency_ms).label("avg_latency_ms"),
            func.avg(EvaluationMetric.graph_generation_time_ms).label("avg_graph_generation_time_ms"),
            func.avg(EvaluationMetric.privilege_accuracy).label("avg_privilege_accuracy"),
            func.count(EvaluationMetric.id).label("total_records")
        ]

        stmt = select(*metrics_fields)
        if case_id:
            stmt = stmt.where(EvaluationMetric.case_id == case_id)

        result = await self._session.execute(stmt)
        row = result.fetchone()
        if not row or row.total_records == 0:
            return {
                "avg_ocr_accuracy": None,
                "avg_retrieval_precision": None,
                "avg_retrieval_recall": None,
                "avg_semantic_similarity": None,
                "avg_hallucination_rate": None,
                "avg_latency_ms": None,
                "avg_graph_generation_time_ms": None,
                "avg_privilege_accuracy": None,
                "total_records": 0
            }

        return {
            "avg_ocr_accuracy": float(row.avg_ocr_accuracy) if row.avg_ocr_accuracy is not None else None,
            "avg_retrieval_precision": float(row.avg_retrieval_precision) if row.avg_retrieval_precision is not None else None,
            "avg_retrieval_recall": float(row.avg_retrieval_recall) if row.avg_retrieval_recall is not None else None,
            "avg_semantic_similarity": float(row.avg_semantic_similarity) if row.avg_semantic_similarity is not None else None,
            "avg_hallucination_rate": float(row.avg_hallucination_rate) if row.avg_hallucination_rate is not None else None,
            "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms is not None else None,
            "avg_graph_generation_time_ms": float(row.avg_graph_generation_time_ms) if row.avg_graph_generation_time_ms is not None else None,
            "avg_privilege_accuracy": float(row.avg_privilege_accuracy) if row.avg_privilege_accuracy is not None else None,
            "total_records": int(row.total_records)
        }

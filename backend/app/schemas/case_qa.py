"""
Pydantic schemas for Case Q&A (Batch 3 Grounded RAG).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class QuestionRequest(BaseModel):
    """Input request body for case Q&A."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Non-empty question string scoped to the case (max 1000 characters).",
    )

    @field_validator("question")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace.")
        return v


class CitationItem(BaseModel):
    """Metadata for a cited or retrieved evidence chunk."""
    chunk_id: str
    document_id: str
    filename: str
    section: str = "unavailable"
    page: Optional[int] = None
    excerpt: str


class GroundingDiagnostics(BaseModel):
    """Diagnostic details for Gate A and Gate B verification."""
    gate_a_passed: bool
    gate_b_passed: bool
    failure_reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class QuestionResponse(BaseModel):
    """Response payload for case Q&A."""
    status: str = Field(
        ...,
        description="Outcome status: 'grounded' | 'insufficient_evidence' | 'suppressed'",
    )
    answer: Optional[str] = Field(
        default=None,
        description="Grounded answer text (non-null only when status is 'grounded').",
    )
    citations: List[CitationItem] = Field(
        default_factory=list,
        description="List of verified citation items mapping to cited chunk labels.",
    )
    retrieved_evidence: List[CitationItem] = Field(
        default_factory=list,
        description="Top retrieved candidate excerpts available for human inspection on non-grounded outcomes.",
    )
    grounding_diagnostics: GroundingDiagnostics = Field(
        ...,
        description="Verification gate results and failure diagnostics.",
    )
    model_version: str = Field(
        ...,
        description="LLM model identifier used for generation.",
    )
    ai_generated: bool = Field(
        default=True,
        description="Flag indicating output was synthesized by AI for attorney review.",
    )
    llm_calls: int = Field(
        default=0,
        description="Count of live LLM generation calls consumed (0 or 1).",
    )

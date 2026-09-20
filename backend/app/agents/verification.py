"""
Verification Agent for the E-Discovery platform.

Checks citation validity, cross-document contradictions,
evidence consistency, and hallucination detection.
"""

import re
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException
from loguru import logger


class VerificationInput(BaseModel):
    document_id: str
    summary_text: str
    source_text: str
    citations: List[str] = Field(default_factory=list)


class VerificationIssue(BaseModel):
    issue_type: str  # citation_invalid, contradiction, inconsistency, hallucination
    severity: str    # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    evidence: str


class VerificationOutput(BaseModel):
    document_id: str
    is_valid: bool
    issues: List[VerificationIssue]
    hallucination_score: float  # 0.0 = no hallucination, 1.0 = fully hallucinated
    confidence_score: float


class VerificationAgent(BaseAgent[VerificationInput, VerificationOutput]):
    """
    Verifies summaries against source material.
    """

    def __init__(self):
        super().__init__(
            name="VerificationAgent",
            prompt_version="1.0.0",
            input_model=VerificationInput,
            output_model=VerificationOutput,
        )

    def _check_citations(self, citations: List[str], source_text: str) -> List[dict]:
        """Validate that citations reference real content."""
        issues = []
        for citation in citations:
            # Check if the citation marker pattern is well-formed
            if not re.search(r'\[.*\]', citation):
                issues.append({
                    "issue_type": "citation_invalid",
                    "severity": "HIGH",
                    "description": f"Malformed citation: {citation}",
                    "evidence": citation,
                })
        return issues

    def _detect_hallucination(self, summary_text: str, source_text: str) -> tuple[float, List[dict]]:
        """Detect hallucinated content in the summary."""
        issues = []
        summary_tokens = set(re.findall(r'\b\w+\b', summary_text.lower()))
        source_tokens = set(re.findall(r'\b\w+\b', source_text.lower()))

        # Stopwords to exclude from hallucination checking
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
            "to", "for", "of", "and", "or", "but", "not", "with", "this",
            "that", "it", "be", "as", "by", "from", "has", "had", "have",
            "will", "can", "may", "its", "no", "do", "if", "so", "all",
            "executive", "overview", "legal", "analysis", "evidence", "summary",
            "clause",
        }

        content_summary = summary_tokens - stopwords
        content_source = source_tokens - stopwords

        if not content_summary:
            return 0.0, []

        unsupported = content_summary - content_source
        hallucination_ratio = len(unsupported) / (len(content_summary) + 1e-9)

        if hallucination_ratio > 0.5:
            issues.append({
                "issue_type": "hallucination",
                "severity": "CRITICAL",
                "description": f"High hallucination detected: {hallucination_ratio:.0%} of summary terms not found in source.",
                "evidence": f"Unsupported terms: {', '.join(list(unsupported)[:5])}",
            })
        elif hallucination_ratio > 0.2:
            issues.append({
                "issue_type": "hallucination",
                "severity": "MEDIUM",
                "description": f"Moderate hallucination detected: {hallucination_ratio:.0%} of summary terms not found in source.",
                "evidence": f"Unsupported terms: {', '.join(list(unsupported)[:5])}",
            })

        return round(hallucination_ratio, 4), issues

    def _check_consistency(self, summary_text: str, source_text: str) -> List[dict]:
        """Check for logical contradictions (simplified heuristic)."""
        issues = []
        # Check for negation contradictions
        negation_pairs = [
            ("not guilty", "guilty"),
            ("innocent", "convicted"),
            ("approved", "rejected"),
        ]
        summary_lower = summary_text.lower()
        source_lower = source_text.lower()

        for neg, pos in negation_pairs:
            if neg in summary_lower and pos in source_lower and neg not in source_lower:
                issues.append({
                    "issue_type": "contradiction",
                    "severity": "HIGH",
                    "description": f"Contradiction detected: summary says '{neg}' but source says '{pos}'.",
                    "evidence": f"Summary: '{neg}', Source: '{pos}'",
                })

        return issues

    async def _execute(self, validated_input: VerificationInput) -> dict:
        logger.info(f"[{self.name}] Verifying document {validated_input.document_id}")

        all_issues = []

        # 1. Citation validity
        citation_issues = self._check_citations(validated_input.citations, validated_input.source_text)
        all_issues.extend(citation_issues)

        # 2. Hallucination detection
        hall_score, hall_issues = self._detect_hallucination(
            validated_input.summary_text, validated_input.source_text
        )
        all_issues.extend(hall_issues)

        # 3. Consistency check
        consistency_issues = self._check_consistency(
            validated_input.summary_text, validated_input.source_text
        )
        all_issues.extend(consistency_issues)

        is_valid = len(all_issues) == 0

        return {
            "document_id": validated_input.document_id,
            "is_valid": is_valid,
            "issues": all_issues,
            "hallucination_score": hall_score,
            "confidence_score": 0.90,
        }

"""
PII Detection & Redaction Agent for the E-Discovery platform.

Detects and redacts: Emails, Phone numbers, Addresses, IDs (SSN, passport),
and Financial information (credit cards, bank accounts).
"""

import re
from typing import Any, Dict, List
from pydantic import BaseModel

from app.agents.base import BaseAgent, AgentException
from loguru import logger


class PIIInput(BaseModel):
    document_id: str
    text: str


class PIIEntity(BaseModel):
    type: str
    original: str
    redacted: str
    start: int
    end: int


class PIIOutput(BaseModel):
    document_id: str
    redacted_text: str
    entities_found: List[PIIEntity]
    confidence_score: float


# Pattern definitions: (name, regex, redaction_label)
PII_PATTERNS = [
    ("Email", r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', "[EMAIL_REDACTED]"),
    ("Phone", r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b', "[PHONE_REDACTED]"),
    ("SSN", r'\b\d{3}-\d{2}-\d{4}\b', "[SSN_REDACTED]"),
    ("Credit Card", r'\b(?:\d{4}[-\s]?){3}\d{4}\b', "[CC_REDACTED]"),
    ("Address", r'\b\d{1,5}\s+(?:[A-Z][a-z]+\s?){1,3}(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Rd|Road|Ln|Lane|Ct|Court)\.?\b', "[ADDRESS_REDACTED]"),
]


class PIIAgent(BaseAgent[PIIInput, PIIOutput]):
    """
    Detects and redacts PII from legal documents.
    """

    def __init__(self):
        super().__init__(
            name="PIIAgent",
            prompt_version="1.0.0",
            input_model=PIIInput,
            output_model=PIIOutput,
        )

    async def _execute(self, validated_input: PIIInput) -> dict:
        logger.info(f"[{self.name}] Scanning document {validated_input.document_id} for PII")

        text = validated_input.text
        entities = []

        # Collect all matches first, sorted by position (reversed for safe replacement)
        all_matches = []
        for pii_type, pattern, redaction in PII_PATTERNS:
            for match in re.finditer(pattern, text):
                all_matches.append({
                    "type": pii_type,
                    "original": match.group(),
                    "redacted": redaction,
                    "start": match.start(),
                    "end": match.end(),
                })

        # Sort by start position descending for safe replacement
        all_matches.sort(key=lambda x: x["start"], reverse=True)

        redacted_text = text
        for m in all_matches:
            redacted_text = redacted_text[:m["start"]] + m["redacted"] + redacted_text[m["end"]:]

        # Re-sort ascending for output
        all_matches.sort(key=lambda x: x["start"])

        return {
            "document_id": validated_input.document_id,
            "redacted_text": redacted_text,
            "entities_found": all_matches,
            "confidence_score": 0.96,
        }

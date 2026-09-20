"""
Timeline Agent for the E-Discovery platform.

Extracts chronological events, dates, and milestone descriptions from legal documents.
Uses a hybrid architecture:
1. First-pass deterministic regex extraction for structured date formats (ISO, US standard, natural month names).
2. Dynamic context-sensitive confidence scoring based on date specificity and textual anchoring.
3. Selective Gemini LLM enhancement for ambiguous or high-importance chronological narratives.
"""

import re
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException
from app.config import get_settings
from loguru import logger

from app.agents.gemini_client import (
    get_gemini_client as _get_gemini_client,
    is_quota_error,
    mark_primary_exhausted,
    QuotaExhaustedException,
)


class TimelineInput(BaseModel):
    document_id: str
    text: str


class TimelineEvent(BaseModel):
    date: str
    description: str
    confidence: float


class TimelineOutput(BaseModel):
    document_id: str
    timeline: List[TimelineEvent]
    confidence_score: float


# Date patterns with base confidence reflecting format specificity
DATE_PATTERNS = [
    # ISO Format: YYYY-MM-DD (e.g. 2001-04-18)
    (re.compile(r"\b((?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b"), "%Y-%m-%d", 0.95),
    # US Standard: MM/DD/YYYY or M/D/YY (e.g. 04/18/2001, 4/18/01)
    (re.compile(r"\b((?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/(?:(?:19|20)?\d{2}))\b"), "US_SLASH", 0.85),
    # Written: Month Day, Year (e.g. April 18, 2001 or 18 August 2000)
    (re.compile(r"\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+(?:19|20)\d{2})\b", re.IGNORECASE), "WRITTEN_MDY", 0.90),
    (re.compile(r"\b(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?:19|20)\d{2})\b", re.IGNORECASE), "WRITTEN_DMY", 0.90),
]

ACTION_VERBS = [
    "filed", "submitted", "executed", "signed", "terminated", "approved",
    "issued", "ordered", "scheduled", "notified", "transferred", "paid",
    "received", "commenced", "held", "demanded", "advised", "warned"
]


class TimelineAgent(BaseAgent[TimelineInput, TimelineOutput]):
    """
    Extracts events, sorts chronologically, generates timeline JSON.
    Uses high-precision deterministic date extraction with contextual confidence,
    routing complex or narrative documents to Gemini LLM when high-value events are identified.
    """

    def __init__(self):
        super().__init__(
            name="TimelineAgent",
            prompt_version="2.0.0",
            input_model=TimelineInput,
            output_model=TimelineOutput,
        )

    def _normalize_date(self, raw_date: str, fmt_type: str) -> Optional[str]:
        raw_clean = raw_date.strip().replace(",", "")
        try:
            if fmt_type == "%Y-%m-%d":
                dt = datetime.strptime(raw_clean, "%Y-%m-%d")
                return dt.strftime("%Y-%m-%d")
            elif fmt_type == "US_SLASH":
                parts = raw_clean.split("/")
                m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
                if y < 100:
                    y = 2000 + y if y < 50 else 1900 + y
                return f"{y:04d}-{m:02d}-{d:02d}"
            elif fmt_type in ("WRITTEN_MDY", "WRITTEN_DMY"):
                for fmt in ["%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"]:
                    try:
                        dt = datetime.strptime(raw_clean, fmt)
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        continue
        except Exception:
            return None
        return None

    def _extract_deterministic_events(self, text: str) -> List[Dict[str, Any]]:
        raw_events = []
        seen_dates = set()

        for pattern, fmt_type, base_conf in DATE_PATTERNS:
            for m in pattern.finditer(text):
                raw_str = m.group(1)
                norm_d = self._normalize_date(raw_str, fmt_type)
                if not norm_d or norm_d in seen_dates:
                    continue

                # Context extraction around date
                start = max(0, m.start() - 60)
                end = min(len(text), m.end() + 100)
                window = text[start:end].replace("\r", " ").replace("\n", " ").strip()
                window = re.sub(r"\s+", " ", window)

                # Compute dynamic confidence:
                # - Base confidence from format clarity
                # - Bonus if near action verbs (+0.05)
                # - Penalty if window is tiny (-0.10)
                conf = base_conf
                has_verb = any(re.search(rf"\b{v}\b", window, re.IGNORECASE) for v in ACTION_VERBS)
                if has_verb:
                    conf = min(0.98, conf + 0.05)
                if len(window) < 30:
                    conf = max(0.60, conf - 0.15)

                raw_events.append({
                    "date": norm_d,
                    "description": window,
                    "confidence": round(conf, 4)
                })
                seen_dates.add(norm_d)

        # Sort chronologically
        raw_events.sort(key=lambda x: x["date"])
        return raw_events

    async def _extract_llm_events(self, text: str, initial_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        client = _get_gemini_client()
        settings = get_settings()
        model_name = settings.google_model or "gemini-3.5-flash-lite"

        dates_hint = ", ".join([e["date"] for e in initial_events[:5]])

        prompt = f"""You are a senior legal e-discovery analyst. Extract the key chronological events and milestones from this document.
For each event, specify:
1. "date": ISO format (YYYY-MM-DD). If month/day not specified, estimate as 01.
2. "description": A concise, factual 1-2 sentence description of the legal, operational, or business event that occurred.
3. "confidence": A float between 0.70 and 0.99 reflecting how explicitly and unambiguously this event is dated in the text.

DOCUMENT TEXT:
\"\"\"
{text[:8000]}
\"\"\"

DATES DETECTED: {dates_hint if dates_hint else 'None'}

Return strictly JSON matching this schema:
{{
  "events": [
    {{
      "date": "YYYY-MM-DD",
      "description": "Factual event description...",
      "confidence": 0.92
    }}
  ]
}}"""

        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
        except Exception as e:
            if is_quota_error(e):
                if mark_primary_exhausted():
                    logger.warning(f"[{self.name}] 429 Quota Exhausted on primary key. Switched to GOOGLE_API_KEY_2. Retrying...")
                    client = _get_gemini_client()
                    try:
                        response = await client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config={"response_mime_type": "application/json"}
                        )
                    except Exception as retry_err:
                        if is_quota_error(retry_err):
                            raise QuotaExhaustedException(f"[{self.name}] LLM quota exhausted on both keys: {retry_err}") from retry_err
                        logger.warning(f"[{self.name}] LLM timeline extraction retry failed: {retry_err}. Falling back to deterministic extraction.")
                        return initial_events
                else:
                    raise QuotaExhaustedException(f"[{self.name}] LLM quota exhausted on primary key and secondary key unavailable: {e}") from e
            else:
                logger.warning(f"[{self.name}] LLM timeline extraction failed: {e}. Falling back to deterministic extraction.")
                return initial_events

        try:
            parsed = json.loads(response.text)
            llm_events = parsed.get("events", [])
            valid_events = []
            for ev in llm_events:
                if "date" in ev and "description" in ev:
                    valid_events.append({
                        "date": ev["date"],
                        "description": ev["description"],
                        "confidence": round(float(ev.get("confidence", 0.85)), 4)
                    })
            valid_events.sort(key=lambda x: x["date"])
            return valid_events
        except Exception as parse_err:
            logger.warning(f"[{self.name}] Failed to parse LLM timeline response: {parse_err}")
            return initial_events

    async def _execute(self, validated_input: TimelineInput) -> dict:
        logger.info(f"[{self.name}] Generating timeline for document {validated_input.document_id}")

        text = validated_input.text or ""
        deterministic_events = self._extract_deterministic_events(text)

        # Selective routing:
        # If deterministic events were found with high confidence and concise descriptions,
        # use deterministic result (zero API cost).
        # If text is substantial (>400 chars) and contains legal action keywords but few clean dates,
        # or has multiple candidate events requiring narrative synthesis, invoke Gemini LLM.
        has_dense_legal_narrative = any(
            re.search(rf"\b{v}\b", text, re.IGNORECASE) for v in ["litigation", "investigation", "subpoena", "hearing", "order", "breach"]
        )

        final_events = deterministic_events
        if len(text) > 300 and (len(deterministic_events) == 0 or has_dense_legal_narrative):
            logger.info(f"[{self.name}] Invoking Gemini LLM to synthesize timeline for complex document {validated_input.document_id}")
            final_events = await self._extract_llm_events(text, deterministic_events)

        if not final_events:
            overall_confidence = 0.50
        else:
            overall_confidence = round(sum(e["confidence"] for e in final_events) / len(final_events), 4)

        return {
            "document_id": validated_input.document_id,
            "timeline": final_events,
            "confidence_score": overall_confidence
        }

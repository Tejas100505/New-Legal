"""
Privilege Detection Agent for the E-Discovery platform.

Two-pass detection architecture:
1. High-recall regex pattern matching for explicit headers and markers.
2. Contextual Gemini LLM reasoning (gemini-3.8-flash) for ambiguous cases
   (e.g., attorney names mentioned without explicit privilege markers,
   or commercial confidentiality language).

Safeguard: Explicit high-confidence regex matches cannot be discarded without
logged justification, prioritizing recall over precision for legal privilege.
"""

import json
import re
from typing import Any, Dict, List, Optional
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


class PrivilegeInput(BaseModel):
    document_id: str
    text: str


class PrivilegeDetection(BaseModel):
    privilege_type: str
    detected: bool
    explanation: str
    matched_phrases: List[str]
    evidence_spans: List[str] = Field(default_factory=list)


class PrivilegeOutput(BaseModel):
    document_id: str
    detections: List[PrivilegeDetection]
    is_privileged: bool
    confidence_score: float
    detection_method: str = Field(
        "regex_only",
        description="Detection method: 'regex_only', 'llm_only', or 'both'"
    )
    reasoning: str = Field(
        "",
        description="Detailed legal analysis explaining the privilege decision"
    )
    evidence_spans: List[str] = Field(
        default_factory=list,
        description="Direct quotes from the document supporting or informing the decision"
    )


PRIVILEGE_PATTERNS = {
    "Attorney-Client Privilege": {
        "patterns": [
            r"attorney[\s-]client\s+privilege",
            r"privileged\s+and\s+confidential",
            r"legal\s+advice",
            r"attorney[\s-]client\s+communication",
            r"seek(?:ing)?\s+legal\s+counsel",
            r"advice\s+of\s+counsel",
        ],
        "explanation_prefix": "Attorney-client privilege detected because the document",
    },
    "Work Product": {
        "patterns": [
            r"work\s+product",
            r"prepared\s+in\s+anticipation\s+of\s+litigation",
            r"litigation\s+strategy",
            r"trial\s+preparation",
            r"attorney\s+work\s+product",
        ],
        "explanation_prefix": "Work product doctrine applies because the document",
    },
    "Confidentiality": {
        "patterns": [
            r"confidential(?:ity)?",
            r"do\s+not\s+distribute",
            r"not\s+for\s+public\s+(?:release|disclosure)",
            r"proprietary\s+(?:information|and\s+confidential)",
            r"non[\s-]disclosure",
            r"trade\s+secret",
        ],
        "explanation_prefix": "Confidentiality language detected because the document",
    },
}

# High-confidence explicit markers that trigger conclusive regex detection
STRONG_PRIVILEGE_PATTERNS = [
    r"attorney[\s-]client\s+privilege",
    r"privileged\s+and\s+confidential",
    r"attorney[\s-]client\s+communication",
    r"prepared\s+in\s+anticipation\s+of\s+litigation",
    r"attorney\s+work\s+product",
]

# Ambiguous keywords: attorney/counsel references, law firm terms, and legal entity identifiers
AMBIGUOUS_LEGAL_TERMS = [
    r"\b(attorney|lawyer|counsel|counselor|esq|esquire|solicitor|in-house\s+counsel|outside\s+counsel|general\s+counsel)\b",
    r"\b(partner|associate|law\s+firm|llp|p\.c\.|legal\s+group|legal\s+department)\b",
]

DISCLAIMER_PATTERNS = [
    r"confidentiality\s+notice",
    r"this\s+transmission\s+may\s+contain",
    r"if\s+you\s+(?:have\s+)?received\s+this\s+(?:email|transmission|message)\s+in\s+error",
    r"strictly\s+prohibited",
    r"notify\s+the\s+sender\s+immediately",
    r"exempt\s+from\s+disclosure",
]


class PrivilegeAgent(BaseAgent[PrivilegeInput, PrivilegeOutput]):
    """
    Detects privilege markers in legal documents using a two-pass architecture:
    1. First pass: High-recall regex detection.
    2. Second pass: Gemini LLM contextual reasoning for ambiguous cases.
    """

    def __init__(self):
        super().__init__(
            name="PrivilegeAgent",
            prompt_version="2.1.0",
            input_model=PrivilegeInput,
            output_model=PrivilegeOutput,
        )

    def _extract_snippets(self, text: str, pattern: str, max_matches: int = 3) -> List[str]:
        """Extracts contextual text snippet around regex matches."""
        snippets = []
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(text) else ""
            snippet = f"{prefix}{text[start:end].strip()}{suffix}"
            snippets.append(snippet)
            if len(snippets) >= max_matches:
                break
        return snippets

    def _is_match_in_disclaimer_or_footer(self, text: str, match_phrase: str) -> bool:
        """
        Checks if the strong privilege match appears in a boilerplate disclaimer or footer block.
        """
        text_lower = text.lower()
        match_pos = text_lower.find(match_phrase.lower())
        if match_pos == -1:
            return False

        # Check if match is in the last 25% or last 400 characters of the document
        doc_len = len(text_lower)
        is_near_end = match_pos > (doc_len * 0.75) or (doc_len - match_pos < 450)

        # Check surrounding context (window of +/- 300 chars) for disclaimer boilerplate phrases
        win_start = max(0, match_pos - 250)
        win_end = min(doc_len, match_pos + 250)
        window_text = text_lower[win_start:win_end]

        has_disclaimer_marker = any(re.search(dp, window_text) for dp in DISCLAIMER_PATTERNS)

        return is_near_end and has_disclaimer_marker

    async def _execute(self, validated_input: PrivilegeInput) -> dict:
        logger.info(f"[{self.name}] Scanning document {validated_input.document_id} for privilege")

        text = validated_input.text or ""
        text_lower = text.lower()

        # ── Step 1: First-Pass Regex Evaluation ───────────────────────────────
        detections = []
        all_matched_phrases = []
        all_evidence_spans = []

        strong_matches = []
        ac_or_wp_detected = False

        for priv_type, config in PRIVILEGE_PATTERNS.items():
            matched_for_type = []
            spans_for_type = []

            for pattern in config["patterns"]:
                matches = re.findall(pattern, text_lower)
                if matches:
                    matched_for_type.extend(matches)
                    spans_for_type.extend(self._extract_snippets(text, pattern))

                    # Check if this pattern is in STRONG_PRIVILEGE_PATTERNS
                    if pattern in STRONG_PRIVILEGE_PATTERNS:
                        strong_matches.extend(matches)

            unique_matches = list(set(matched_for_type))
            detected = len(unique_matches) > 0
            if detected and priv_type in ["Attorney-Client Privilege", "Work Product"]:
                ac_or_wp_detected = True

            if detected:
                explanation = (
                    f"{config['explanation_prefix']} contains the following indicators: "
                    f"{', '.join(unique_matches)}."
                )
            else:
                explanation = f"No {priv_type.lower()} indicators found in the document."

            all_matched_phrases.extend(unique_matches)
            all_evidence_spans.extend(spans_for_type)

            detections.append({
                "privilege_type": priv_type,
                "detected": detected,
                "explanation": explanation,
                "matched_phrases": unique_matches,
                "evidence_spans": spans_for_type[:3],
            })

        has_strong_regex_match = len(strong_matches) > 0

        # Check if strong regex match is confined to a disclaimer/footer
        strong_match_in_disclaimer = False
        if has_strong_regex_match:
            strong_match_in_disclaimer = any(
                self._is_match_in_disclaimer_or_footer(text, sm) for sm in strong_matches
            )

        # Check for attorney mentions
        attorney_mentions = []
        for term_pat in AMBIGUOUS_LEGAL_TERMS:
            for m in re.finditer(term_pat, text_lower):
                attorney_mentions.append(m.group(0))
        attorney_mentions = list(set(attorney_mentions))
        has_attorney_mention = len(attorney_mentions) > 0

        # Determine ambiguity
        # Case A: Document mentions attorney/counsel/law firm but lacks explicit privilege header
        # Case B: Only matched generic confidentiality (commercial NDA vs legal privilege)
        # Case C: Matched weak legal advice phrase without clear context
        # Case D: Strong privilege phrase matched but appears in a boilerplate disclaimer/footer
        is_confidentiality_only = (
            not ac_or_wp_detected
            and any(d["detected"] for d in detections if d["privilege_type"] == "Confidentiality")
        )
        is_ambiguous = (
            (has_attorney_mention and not has_strong_regex_match)
            or is_confidentiality_only
            or (ac_or_wp_detected and not has_strong_regex_match)
            or strong_match_in_disclaimer
        )

        # ── Path 1: Clear Explicit Privilege Marker in Substantive Text (Regex Conclusive) ─────────
        if has_strong_regex_match and not strong_match_in_disclaimer:
            logger.info(f"[{self.name}] High-confidence substantive explicit privilege marker detected via regex: {strong_matches}")
            primary_phrases = ", ".join(set(strong_matches))
            reasoning = (
                f"Document contains explicit high-confidence privilege indicators ({primary_phrases}). "
                "Under e-discovery recall-first safeguards, explicit privilege headers and anticipation-of-litigation "
                "markers are classified as privileged without subjective discount."
            )
            return {
                "document_id": validated_input.document_id,
                "detections": detections,
                "is_privileged": True,
                "confidence_score": 0.98,
                "detection_method": "regex_only",
                "reasoning": reasoning,
                "evidence_spans": list(set(all_evidence_spans))[:5],
            }

        # ── Path 2: Clear Negative (Zero Signal) ──────────────────────────────
        if not is_ambiguous and not ac_or_wp_detected and not has_attorney_mention:
            logger.info(f"[{self.name}] Zero privilege signal detected (no regex matches, no attorney mentions)")
            return {
                "document_id": validated_input.document_id,
                "detections": detections,
                "is_privileged": False,
                "confidence_score": 0.99,
                "detection_method": "regex_only",
                "reasoning": "No privilege markers, work product references, confidentiality notices, or legal counsel mentions identified in document text.",
                "evidence_spans": [],
            }

        # ── Path 3: Ambiguous Context (Second-Pass Gemini LLM Reasoning) ───────
        logger.info(f"[{self.name}] Ambiguous privilege context detected (attorney mentions: {attorney_mentions}, confidentiality_only: {is_confidentiality_only}). Invoking Gemini LLM.")
        
        client = _get_gemini_client()
        settings = get_settings()
        model_name = settings.google_model or "gemini-3.5-flash-lite"

        prompt = f"""You are a senior litigation attorney conducting an e-discovery privilege review.
Evaluate whether the following document is legally protected by Attorney-Client Privilege or the Work Product Doctrine.

LEGAL STANDARDS FOR PRIVILEGE:
1. Attorney-Client Privilege requires that the communication be:
   - Between a client and legal counsel acting in a legal capacity,
   - Kept strictly confidential, AND
   - Made for the PRIMARY PURPOSE of seeking or providing legal advice.
   CRITICAL DISTINCTION: Mere business communications where an attorney is copied, or where an attorney is named as a notice contact, corporate officer, or contract signatory WITHOUT substantive legal advice, are NOT PRIVILEGED (hard negatives).
2. Work Product Doctrine requires documents prepared in reasonable anticipation of litigation or for trial preparation.
3. Commercial Confidentiality: Standard non-disclosure or proprietary commercial clauses do NOT constitute legal privilege.

DOCUMENT TEXT:
\"\"\"
{text[:10000]}
\"\"\"

AMBIGUITY FACTORS DETECTED:
- Attorney/Counsel Terms: {', '.join(attorney_mentions) if attorney_mentions else 'None'}
- Regex Matched Phrases: {', '.join(all_matched_phrases) if all_matched_phrases else 'None'}

ANALYSIS REQUIRED:
1. Is an attorney named or communicating? What is their exact capacity (legal advisor vs commercial contact/signatory)?
2. Is the primary purpose to obtain or render legal advice?
3. Was this created in anticipation of litigation?
4. Quote the exact text spans that inform your decision.

Respond strictly in JSON format matching this schema:
{{
  "is_privileged": false,
  "confidence_score": 0.95,
  "privilege_type": "None",
  "reasoning": "Thorough legal analysis explaining why privilege does or does not apply based on the context...",
  "evidence_spans": ["exact quoted text span from document"],
  "primary_purpose_legal_advice": false,
  "prepared_for_litigation": false
}}"""

        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
        except Exception as api_err:
            if is_quota_error(api_err):
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
                        raise retry_err
                else:
                    raise QuotaExhaustedException(f"[{self.name}] LLM quota exhausted on primary key and secondary key unavailable: {api_err}") from api_err
            else:
                fallback_model = settings.google_model_fallback or "gemini-3.8-flash"
                logger.warning(f"[{self.name}] Primary model {model_name} failed ({api_err}). Retrying with {fallback_model}...")
                try:
                    response = await client.aio.models.generate_content(
                        model=fallback_model,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                except Exception as fb_err:
                    if is_quota_error(fb_err):
                        raise QuotaExhaustedException(f"[{self.name}] LLM quota exhausted on fallback model: {fb_err}") from fb_err
                    raise fb_err

        try:
            llm_result = json.loads(response.text)
        except Exception as e:
            logger.error(f"[{self.name}] Failed to parse Gemini privilege response as JSON: {e}. Raw: {response.text}")
            raise AgentException(f"Failed to parse Gemini privilege reasoning output: {e}")

        llm_is_privileged = bool(llm_result.get("is_privileged", False))
        llm_confidence = float(llm_result.get("confidence_score", 0.90))
        llm_reasoning = llm_result.get("reasoning", "LLM privilege assessment completed.")
        llm_spans = llm_result.get("evidence_spans", [])
        llm_priv_type = llm_result.get("privilege_type", "None")

        # Safeguard (Rule 4): If regex detected a strong explicit privilege marker
        # in the substantive text (NOT just a boilerplate disclaimer/footer),
        # do NOT let the LLM override to non-privileged. Recall takes priority.
        if has_strong_regex_match and not strong_match_in_disclaimer and not llm_is_privileged:
            logger.warning(
                f"[{self.name}] LLM proposed non-privileged but explicit substantive regex match "
                f"({strong_matches}) stands under recall-first priority."
            )
            llm_is_privileged = True
            llm_confidence = 0.95
            llm_reasoning = (
                f"Explicit substantive regex privilege marker detected ({', '.join(set(strong_matches))}). "
                f"Preserved as privileged under recall-first safeguards. Context analysis: {llm_reasoning}"
            )

        # Determine detection method
        if all_matched_phrases and llm_is_privileged:
            detection_method = "both"
        elif llm_is_privileged:
            detection_method = "llm_only"
        elif all_matched_phrases:
            detection_method = "both"  # Regex flagged pattern, LLM analyzed and clarified
        else:
            detection_method = "llm_only"

        # Update detections list with LLM findings
        if llm_is_privileged and llm_priv_type in ["Attorney-Client Privilege", "Work Product"]:
            for d in detections:
                if d["privilege_type"] == llm_priv_type:
                    d["detected"] = True
                    d["explanation"] = f"LLM confirmed {llm_priv_type}: {llm_reasoning}"
                    d["evidence_spans"].extend(llm_spans)

        combined_spans = list(set(all_evidence_spans + llm_spans))

        return {
            "document_id": validated_input.document_id,
            "detections": detections,
            "is_privileged": llm_is_privileged,
            "confidence_score": round(llm_confidence, 4),
            "detection_method": detection_method,
            "reasoning": llm_reasoning,
            "evidence_spans": combined_spans[:5],
        }

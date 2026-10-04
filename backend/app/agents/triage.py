"""
Triage Orchestrator Agent for E-Discovery Platform.

Synthesizes multi-modal signals from all upstream pipeline stages:
- Relevance / Retrieval / Classification score
- Privilege detection (is_privileged, confidence, detection_method, evidence)
- Risk assessment (overall risk level, confidence, category assessments)
- Summarization confidence & Grounded Neural Cosine Similarity scores
- Extracted legal entities (Attorneys, Custodians, Regulators, Case References)

Agentic Decision Behavior:
1. Dynamic Composite Review Priority (0-100) and Tiering (CRITICAL, HIGH, MEDIUM, LOW)
2. Uncertainty-based Escalation: If privilege detection is borderline (0.45 <= conf < 0.75)
   on a relevant document, escalates to IMMEDIATE_HUMAN_REVIEW to prevent FRE 502 waiver.
3. Adaptive Second-Pass Reprocessing: Can trigger deep LLM re-analysis if regex markers
   were ambiguous or summarization grounding is degraded.
4. Human Oversight Guarantee: All decisions are advisory prioritization recommendations;
   nothing is auto-approved or auto-discarded.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from loguru import logger

from app.agents.base import BaseAgent, AgentException


# ── Deliberate, Documented E-Discovery Thresholds ──────────────────────────────
# Under FRE 502, inadvertent disclosure of privileged documents in discovery can
# waive attorney-client protection. When privilege confidence is in the borderline
# zone [0.45, 0.75), relevant documents must bypass routine queuing for immediate counsel review.
PRIVILEGE_HIGH_CONFIDENCE_THRESHOLD = 0.85
PRIVILEGE_BORDERLINE_MAX = 0.75
PRIVILEGE_BORDERLINE_MIN = 0.45

# Grounding fidelity threshold for neural cosine similarity
SUMMARIZATION_GROUNDING_THRESHOLD = 0.65

# Known regulatory enforcement entities that escalate compliance/legal exposure
REGULATORY_ENTITIES = {"sec", "cftc", "doj", "ferc", "epa", "ftc", "fbi", "irs", "finra"}


class TriageInput(BaseModel):
    document_id: str
    filename: Optional[str] = "unknown"
    text: str = ""
    relevance_score: Optional[float] = None
    classification: Optional[str] = None
    privilege_analysis: Optional[Dict[str, Any]] = None
    risk_analysis: Optional[Dict[str, Any]] = None
    summarization_data: Optional[Dict[str, Any]] = None
    entities_data: Optional[Dict[str, Any]] = None
    trigger_deep_analysis: bool = True


class TriageOutput(BaseModel):
    document_id: str
    priority_score: float = Field(..., description="Computed review priority score from 0.0 to 100.0")
    priority_tier: str = Field(..., description="Priority tier: CRITICAL, HIGH, MEDIUM, LOW")
    escalation_flag: bool = Field(..., description="True if document requires immediate escalated review")
    escalation_reason: Optional[str] = None
    recommended_action: str = Field(..., description="Recommended workflow action for human review team")
    triage_path: str = Field(..., description="Specific decision branch taken by the orchestrator")
    requires_reprocessing: bool = False
    reprocessing_details: Optional[Dict[str, Any]] = None
    reasoning: str = Field(..., description="Human-readable legal reasoning explaining the priority and routing")
    signal_summary: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0  # Populated at runtime; rule-based triage, not ML-calibrated
    human_oversight_mandatory: bool = True


class TriageOrchestratorAgent(BaseAgent[TriageInput, TriageOutput]):
    """
    Triage Orchestrator Agent that reasons over combined pipeline outputs and
    determines review priority, escalation, and adaptive processing paths.
    """

    def __init__(self):
        super().__init__(
            name="TriageOrchestratorAgent",
            prompt_version="1.0.0",
            input_model=TriageInput,
            output_model=TriageOutput,
        )

    async def _execute(self, validated_input: TriageInput) -> dict:
        doc_id = validated_input.document_id
        text = validated_input.text or ""
        text_lower = text.lower()
        logger.info(f"[{self.name}] Triaging signals for document {doc_id}")

        # ── 1. Signal Extraction & Normalization ──────────────────────────────
        priv = validated_input.privilege_analysis or {}
        risk = validated_input.risk_analysis or {}
        summ = validated_input.summarization_data or {}
        ents = validated_input.entities_data or {}

        # Privilege signals
        is_priv = bool(priv.get("is_privileged", False))
        priv_conf = float(priv.get("confidence_score", priv.get("confidence", 0.50)))
        detection_method = priv.get("detection_method", "unknown")

        # Risk signals
        raw_risk_level = str(risk.get("overall_risk", risk.get("risk_level", "LOW"))).upper()
        risk_level = raw_risk_level if raw_risk_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "LOW"
        risk_conf = float(risk.get("confidence_score", risk.get("confidence", 0.85)))

        # Relevance signals
        if validated_input.relevance_score is not None:
            relevance = float(validated_input.relevance_score)
        else:
            # Derive default relevance from document type & presence of substantive legal terms
            doc_type = (validated_input.classification or "").lower()
            if any(k in doc_type for k in ["contract", "litigation", "pleading", "regulatory", "compliance"]):
                relevance = 0.80
            elif any(k in doc_type for k in ["memorandum", "audit", "investigation"]):
                relevance = 0.70
            elif any(k in doc_type for k in ["email", "correspondence"]):
                relevance = 0.50
            else:
                relevance = 0.40

        # Summarization grounding signals
        sem_scores = summ.get("semantic_similarity_scores", [])
        if isinstance(sem_scores, dict):
            sem_scores = list(sem_scores.values())
        avg_cosine_sim = (
            sum(float(x) for x in sem_scores) / len(sem_scores)
            if sem_scores else 0.80
        )
        has_grounding_issue = avg_cosine_sim < SUMMARIZATION_GROUNDING_THRESHOLD

        # Entity signals
        orgs = [str(o).lower() for o in ents.get("organizations", [])]
        lawyers = ents.get("lawyers", []) or ents.get("attorneys", [])
        custodians = ents.get("custodians", [])
        case_refs = ents.get("case_numbers", []) or ents.get("case_references", [])
        has_regulator = any(r in org or any(r in word for word in org.split()) for r in REGULATORY_ENTITIES for org in orgs)
        has_case_citation = len(case_refs) > 0 or " v. " in text or " vs. " in text

        # ── 2. Adaptive Reprocessing Check ────────────────────────────────────
        requires_reprocessing = False
        reprocessing_details = None

        # If privilege was evaluated only via regex, but the confidence is borderline (0.45 - 0.75),
        # or it's a relevant document with attorney mentions but uncertain privilege status:
        if (
            validated_input.trigger_deep_analysis
            and detection_method == "regex_only"
            and (PRIVILEGE_BORDERLINE_MIN <= priv_conf <= PRIVILEGE_BORDERLINE_MAX or (lawyers and not is_priv))
            and relevance >= 0.45
        ):
            try:
                logger.info(f"[{self.name}] Triggering adaptive second-pass LLM privilege reasoning for {doc_id}")
                from app.agents.privilege import PrivilegeAgent, PrivilegeInput
                priv_agent = PrivilegeAgent()
                escalated_priv = await priv_agent.run(PrivilegeInput(document_id=doc_id, text=text))
                
                requires_reprocessing = True
                reprocessing_details = {
                    "stage": "privilege_llm_escalation",
                    "original_method": detection_method,
                    "original_confidence": priv_conf,
                    "refined_method": escalated_priv.detection_method,
                    "refined_is_privileged": escalated_priv.is_privileged,
                    "refined_confidence": escalated_priv.confidence_score,
                    "trigger_reason": "Borderline regex confidence with substantive legal relevance triggered adaptive LLM pass.",
                }
                # Update with refined second-pass results
                is_priv = escalated_priv.is_privileged
                priv_conf = escalated_priv.confidence_score
                detection_method = f"orchestrator_escalated_{escalated_priv.detection_method}"
            except Exception as e:
                logger.warning(f"[{self.name}] Second-pass LLM privilege reasoning failed: {e}")

        # ── 3. Branching Decision Logic & Triage Paths ─────────────────────────
        priority_score = 50.0
        escalation_flag = False
        escalation_reason = None
        triage_path = "ROUTINE_REVIEW"
        reasoning_parts = []

        # PATH A: Borderline Privilege Uncertainty on Relevant Evidence (FRE 502 Waiver Risk)
        if PRIVILEGE_BORDERLINE_MIN <= priv_conf < PRIVILEGE_BORDERLINE_MAX and relevance >= 0.45:
            triage_path = "BORDERLINE_PRIVILEGE_ESCALATION"
            escalation_flag = True
            escalation_reason = (
                f"Escalated: privilege confidence {priv_conf:.2f} below threshold {PRIVILEGE_BORDERLINE_MAX:.2f} "
                f"on a relevant document (relevance: {relevance:.2f}) — recommend immediate legal review before further processing."
            )
            # High priority between 88.0 and 96.0 depending on risk and relevance
            priority_score = 88.0 + (relevance * 5.0) + (3.0 if risk_level in ["HIGH", "CRITICAL"] else 0.0)
            recommended_action = "IMMEDIATE_HUMAN_REVIEW"
            reasoning_parts.append(
                f"[ESCALATED]: Privilege confidence {priv_conf:.2f} below threshold {PRIVILEGE_BORDERLINE_MAX:.2f} "
                f"on a relevant document (relevance: {relevance:.2f}) — recommend immediate legal review before further processing "
                f"(FRE 502 subject-matter waiver prevention)."
            )

        # PATH B: Critical/High Risk Compliance & Adverse Litigation Exposure
        elif risk_level in ["CRITICAL", "HIGH"]:
            triage_path = "CRITICAL_RISK_EXPOSURE"
            is_critical = risk_level == "CRITICAL"
            base_score = 92.0 if is_critical else 82.0
            
            # Boost for regulatory involvement or active litigation citations
            reg_boost = 6.0 if has_regulator else 0.0
            lit_boost = 4.0 if has_case_citation else 0.0
            priority_score = min(100.0, base_score + reg_boost + lit_boost)
            
            if is_critical or has_regulator:
                escalation_flag = True
                escalation_reason = (
                    f"Document exhibits {risk_level} operational/legal risk exposure"
                    f"{' with regulatory authority involvement (' + ', '.join(r.upper() for r in REGULATORY_ENTITIES if any(r in o for o in orgs)) + ')' if has_regulator else ''}."
                )
                recommended_action = "IMMEDIATE_HUMAN_REVIEW"
            else:
                recommended_action = "PRIORITY_LEGAL_QUEUE"

            reasoning_parts.append(
                f"[HIGH RISK EXPOSURE] ({risk_level}): Document exhibits substantial liability or regulatory exposure. "
                f"{'Active regulatory involvement detected (' + ', '.join(r.upper() for r in REGULATORY_ENTITIES if any(r in o for o in orgs)) + '). ' if has_regulator else ''}"
                f"{'Litigation citations identified (' + ', '.join(case_refs[:2]) + '). ' if case_refs else ''}"
                f"Assigned priority {priority_score:.1f}."
            )

        # PATH C: Confirmed High-Confidence Privilege (Clean Segregation & Privilege Log)
        elif is_priv and priv_conf >= PRIVILEGE_BORDERLINE_MAX:
            triage_path = "CONFIRMED_PRIVILEGE_LOG"
            # Definitively privileged documents are high priority for logging, but not an emergency crisis
            priority_score = 75.0 + (relevance * 10.0)
            escalation_flag = False
            recommended_action = "PRIORITY_PRIVILEGE_LOG"
            reasoning_parts.append(
                f"[CONFIRMED PRIVILEGE] (Confidence: {priv_conf:.2f}): Document verified as attorney-client communication or work product. "
                f"Assigned priority {priority_score:.1f} for formal privilege log preparation and withholding from production."
            )

        # PATH D: Substantive Responsive Document (Non-Privileged Commercial Substance)
        elif relevance >= 0.70:
            triage_path = "HIGH_RELEVANCE_COMMERCIAL"
            priority_score = 60.0 + (relevance * 15.0)
            escalation_flag = False
            recommended_action = "PRIORITY_LEGAL_QUEUE"
            reasoning_parts.append(
                f"[HIGH RELEVANCE] (Score: {relevance:.2f}): Key responsive transaction, agreement, or operational communication. "
                f"Privilege not claimed ({priv_conf:.2f} confidence non-privileged). Placed in standard priority queue."
            )

        # PATH E: Routine Low-Risk / Low-Relevance Material
        else:
            triage_path = "ROUTINE_BENIGN"
            priority_score = max(5.0, (relevance * 30.0) + (10.0 if risk_level == "MEDIUM" else 0.0))
            escalation_flag = False
            recommended_action = "ROUTINE_QUEUE"
            reasoning_parts.append(
                f"[ROUTINE / LOW RELEVANCE]: Standard operational communication or low-impact administrative text. "
                f"Risk is {risk_level}, relevance is {relevance:.2f}. Queued for routine review."
            )

        # ── 4. Grounding & Fidelity Review Adjustments ────────────────────────
        if has_grounding_issue:
            priority_score = min(100.0, priority_score + 5.0)
            reasoning_parts.append(
                f"[GROUNDING ADVISORY]: Multi-perspective summary neural cosine similarity is {avg_cosine_sim:.2f} "
                f"(below {SUMMARIZATION_GROUNDING_THRESHOLD:.2f} grounding threshold). "
                f"Automated summaries may exhibit semantic drift; reviewing attorney must verify raw source text."
            )

        # ── 5. Determine Final Priority Tier ──────────────────────────────────
        final_priority = round(priority_score, 1)
        if final_priority >= 85.0 or escalation_flag:
            tier = "CRITICAL"
        elif final_priority >= 70.0:
            tier = "HIGH"
        elif final_priority >= 45.0:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        # Mandatory human oversight assurance
        reasoning_parts.append(
            "[MANDATORY HUMAN OVERSIGHT]: This triage prioritization is an advisory recommendation. "
            "Final privilege determination and production approval remain the sole responsibility of reviewing legal counsel."
        )

        full_reasoning = "\n\n".join(reasoning_parts)

        signal_summary = {
            "relevance_score": round(relevance, 3),
            "is_privileged": is_priv,
            "privilege_confidence": round(priv_conf, 3),
            "privilege_method": detection_method,
            "risk_level": risk_level,
            "risk_confidence": round(risk_conf, 3),
            "summarization_cosine_similarity": round(avg_cosine_sim, 3),
            "has_regulatory_entity": has_regulator,
            "has_litigation_citation": has_case_citation,
            "attorney_count": len(lawyers),
            "custodian_count": len(custodians),
        }

        return {
            "document_id": doc_id,
            "priority_score": final_priority,
            "priority_tier": tier,
            "escalation_flag": escalation_flag,
            "escalation_reason": escalation_reason,
            "recommended_action": recommended_action,
            "triage_path": triage_path,
            "requires_reprocessing": requires_reprocessing,
            "reprocessing_details": reprocessing_details,
            "reasoning": full_reasoning,
            "signal_summary": signal_summary,
            "confidence_score": 0.70,  # Rule-based deterministic triage; not ML-calibrated
            "human_oversight_mandatory": True,
        }

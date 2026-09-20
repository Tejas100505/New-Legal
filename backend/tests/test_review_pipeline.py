"""
Tests for the Review Pipeline (Part 2D).
Covers: summaries, citations, hallucination, privilege, PII, risk, review map, reports.
"""

import pytest
from app.agents.summarization import SummarizationAgent, SummarizationInput
from app.agents.privilege import PrivilegeAgent, PrivilegeInput
from app.agents.pii import PIIAgent, PIIInput
from app.agents.risk import RiskAgent, RiskInput
from app.agents.verification import VerificationAgent, VerificationInput
from app.agents.review import ReviewAgent, ReviewInput
from app.agents.report import ReportAgent, ReportInput


@pytest.fixture
def summarization_agent():
    return SummarizationAgent()

@pytest.fixture
def privilege_agent():
    return PrivilegeAgent()

@pytest.fixture
def pii_agent():
    return PIIAgent()

@pytest.fixture
def risk_agent():
    return RiskAgent()

@pytest.fixture
def verification_agent():
    return VerificationAgent()

@pytest.fixture
def review_agent():
    return ReviewAgent()

@pytest.fixture
def report_agent():
    return ReportAgent()


# ── 1. Summaries with citations ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summaries_with_citations(summarization_agent):
    text = (
        "The contract agreement was signed on 2023-01-15. "
        "Evidence exhibit A shows the defendant was present. "
        "The court issued a legal ruling under the statute."
    )
    chunks = [
        {"section": "Introduction", "page": 1},
        {"section": "Evidence", "page": 3},
    ]
    input_data = SummarizationInput(document_id="doc1", text=text, chunks=chunks)
    result = await summarization_agent.run(input_data)

    assert len(result.summaries) == 4
    types = [s.type for s in result.summaries]
    assert "Executive" in types
    assert "Legal" in types
    assert "Evidence" in types
    assert "Clause" in types

    # Every summary must have citations
    for s in result.summaries:
        assert len(s.citations) > 0

    # ROUGE scores must be present for all types
    assert "Executive" in result.rouge_scores
    assert result.rouge_scores["Executive"].rouge_1 > 0


# ── 2. Citation validity ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_citation_validity(verification_agent):
    input_data = VerificationInput(
        document_id="doc1",
        summary_text="The contract was signed by Acme Corp.",
        source_text="The contract was signed by Acme Corp on 2023-01-15.",
        citations=["[Chunk 1, § Intro, p. 1]", "INVALID_NO_BRACKETS"],
    )
    result = await verification_agent.run(input_data)

    # Should flag the malformed citation
    citation_issues = [i for i in result.issues if i.issue_type == "citation_invalid"]
    assert len(citation_issues) == 1
    assert "INVALID_NO_BRACKETS" in citation_issues[0].evidence


# ── 3. Hallucination detection ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hallucination_detection(verification_agent):
    input_data = VerificationInput(
        document_id="doc1",
        summary_text="The quantum blockchain synergy disrupted the metaverse paradigm.",
        source_text="The contract was signed by Acme Corp.",
        citations=[],
    )
    result = await verification_agent.run(input_data)

    assert result.hallucination_score > 0.5
    hall_issues = [i for i in result.issues if i.issue_type == "hallucination"]
    assert len(hall_issues) > 0
    assert hall_issues[0].severity == "CRITICAL"


# ── 4. Privilege detection ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_privilege_detection(privilege_agent):
    text = (
        "This document is privileged and confidential. "
        "It was prepared in anticipation of litigation as attorney work product. "
        "Do not distribute."
    )
    input_data = PrivilegeInput(document_id="doc1", text=text)
    result = await privilege_agent.run(input_data)

    assert result.is_privileged is True
    assert len(result.detections) == 3

    detected_types = [d.privilege_type for d in result.detections if d.detected]
    assert "Attorney-Client Privilege" in detected_types
    assert "Work Product" in detected_types
    assert "Confidentiality" in detected_types

    # Each detection must have an explanation
    for d in result.detections:
        assert len(d.explanation) > 0

    # Regression guards: confidence_score must always be populated and numeric
    assert result.confidence_score is not None
    assert isinstance(result.confidence_score, (int, float))
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.detection_method in ("regex_only", "zero_signal", "hybrid_llm", "llm_fallback")


# ── 5. PII redaction ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pii_redaction(pii_agent):
    text = "Contact john@example.com or call 555-123-4567. SSN: 123-45-6789. Card: 4111 1111 1111 1111."
    input_data = PIIInput(document_id="doc1", text=text)
    result = await pii_agent.run(input_data)

    # Ensure originals are redacted
    assert "john@example.com" not in result.redacted_text
    assert "[EMAIL_REDACTED]" in result.redacted_text
    assert "123-45-6789" not in result.redacted_text
    assert "[SSN_REDACTED]" in result.redacted_text
    assert "4111 1111 1111 1111" not in result.redacted_text
    assert "[CC_REDACTED]" in result.redacted_text

    # Check entity types found
    entity_types = [e.type for e in result.entities_found]
    assert "Email" in entity_types
    assert "SSN" in entity_types
    assert "Credit Card" in entity_types


# ── 6. Risk analysis ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_risk_analysis(risk_agent):
    text = "The lawsuit alleges breach of contract and fraud. The audit failure triggered regulatory action. Bankruptcy proceedings began."
    input_data = RiskInput(document_id="doc1", text=text)
    result = await risk_agent.run(input_data)

    assert len(result.assessments) == 3

    categories = {a.category: a for a in result.assessments}
    assert categories["Legal Risk"].risk_level == "CRITICAL"  # "fraud"
    assert categories["Compliance Risk"].risk_level == "HIGH"  # "audit failure"
    assert categories["Financial Risk"].risk_level == "CRITICAL"  # "bankruptcy"
    assert result.overall_risk == "CRITICAL"


# ── 7. Review Map ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_map(review_agent):
    documents = [
        {"document_id": "doc1", "classification": "Contracts", "risk": "HIGH"},
        {"document_id": "doc2", "classification": "Emails", "risk": "LOW"},
        {"document_id": "doc3", "classification": "Evidence", "risk": "MEDIUM"},
    ]
    clusters = [
        {"document_ids": ["doc1", "doc2"], "label": "Financial Fraud"},
    ]
    relationships = [
        {"source": "doc2", "target": "doc3"},
    ]

    input_data = ReviewInput(documents=documents, relationships=relationships, clusters=clusters)
    result = await review_agent.run(input_data)

    review_map = result.review_map
    assert "nodes" in review_map
    assert "links" in review_map

    node_ids = [n["id"] for n in review_map["nodes"]]
    assert "doc1" in node_ids
    assert "doc2" in node_ids
    assert "doc3" in node_ids

    # Should have cluster edge (doc1-doc2) + similarity edge (doc2-doc3)
    assert len(review_map["links"]) == 2

    # Review JSON should have all documents merged
    assert result.review_json["total_documents"] == 3


# ── 8. Report generation ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_generation(report_agent):
    timeline = [
        {"date": "2023-01-15", "description": "Contract signed"},
        {"date": "2023-06-01", "description": "Breach alleged"},
    ]
    risks = [
        {"category": "Legal Risk", "risk_level": "HIGH", "reason": "Breach of contract"},
    ]
    recommendations = ["Engage external counsel", "Preserve all documents"]

    # Test Markdown
    md_input = ReportInput(
        document_id="doc1",
        format="markdown",
        timeline=timeline,
        risks=risks,
        recommendations=recommendations,
    )
    md_result = await report_agent.run(md_input)
    assert md_result.format == "markdown"
    assert "# E-Discovery Review Report" in md_result.content
    assert "Contract signed" in md_result.content
    assert "Breach of contract" in md_result.content
    assert "Engage external counsel" in md_result.content

    # Test JSON
    json_input = ReportInput(
        document_id="doc1",
        format="json",
        timeline=timeline,
        risks=risks,
        recommendations=recommendations,
    )
    json_result = await report_agent.run(json_input)
    assert json_result.format == "json"
    assert '"document_id": "doc1"' in json_result.content

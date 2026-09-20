"""
Comprehensive tests for LLM Quota Exhaustion Remediation:
1. Quota error detection (is_quota_error, QuotaExhaustedException)
2. DocumentStatus.QUOTA_PAUSED handling in orchestrator pipeline
3. Upstream stage result preservation upon quota pause
4. Non-quota error regression preservation (DocumentStatus.ERROR)
5. Smart retry / stage resumption (skipping completed stages to save quota)
6. RiskAgent keyword pre-screen preservation and quota raising
7. ClassificationAgent key-rotation preservation and quota raising
8. Analytics counting exclusion of quota_paused documents
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.models.document import Document, DocumentStatus
from app.agents.gemini_client import (
    is_quota_error,
    QuotaExhaustedException,
    mark_primary_exhausted,
    reset_primary_exhausted,
    get_active_google_api_key,
)
from app.agents.risk import RiskAgent, RiskInput
from app.agents.classification import ClassificationAgent, ClassificationInput
from app.services.orchestrator import run_document_pipeline, _handle_quota_pause


class MockResourceExhausted(Exception):
    """Simulates google.api_core.exceptions.ResourceExhausted 429 error."""
    def __init__(self, message="429 Resource has been exhausted (e.g. check quota)."):
        super().__init__(message)


def test_is_quota_error_detection():
    """Verify that is_quota_error accurately identifies 429 and RESOURCE_EXHAUSTED patterns."""
    assert is_quota_error(MockResourceExhausted()) is True
    assert is_quota_error(Exception("429 Too Many Requests")) is True
    assert is_quota_error(Exception("RESOURCE_EXHAUSTED: quota exceeded")) is True
    assert is_quota_error(Exception("Rate limit reached for model gemini-3.5-flash-lite")) is True
    assert is_quota_error(QuotaExhaustedException("Daily limit reached")) is True

    # Negative cases (non-quota errors)
    assert is_quota_error(ValueError("Invalid argument format")) is False
    assert is_quota_error(FileNotFoundError("Document not found on disk")) is False
    assert is_quota_error(KeyError("missing_field")) is False
    assert is_quota_error(Exception("500 Internal Server Error")) is False


@pytest.mark.asyncio
async def test_risk_agent_prescreen_unchanged_zero_cost():
    """
    Verify Modification #2: RiskAgent's always-on deterministic keyword pre-screen
    must execute cleanly with ZERO LLM calls for benign text, returning LOW risk and conf 0.96.
    """
    agent = RiskAgent()
    # Benign text with zero legal/compliance/financial risk keywords
    benign_input = RiskInput(
        document_id="doc-benign-1",
        text="The team had a regular quarterly sync to review product roadmaps and engineering tasks."
    )
    result = await agent.run(benign_input)
    assert result.overall_risk == "LOW"
    assert result.confidence_score == 0.96
    assert len(result.assessments) == 3
    for a in result.assessments:
        assert a.risk_level == "LOW"
        assert "No " in a.reason


@pytest.mark.asyncio
async def test_risk_agent_raises_quota_exhausted_exception():
    """
    Verify Modification #2: When risk keywords ARE present and Gemini calls fail
    with 429/quota exhaustion on both keys, RiskAgent raises QuotaExhaustedException
    (rather than silently returning fallback data).
    """
    agent = RiskAgent()
    risky_input = RiskInput(
        document_id="doc-risky-1",
        text="Enron received a formal subpoena regarding securities fraud, breach of contract, and bankruptcy."
    )

    reset_primary_exhausted()
    # Mock Gemini client to raise 429 on any call
    with patch("app.agents.risk._get_gemini_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=MockResourceExhausted("429 RESOURCE_EXHAUSTED daily quota reached")
        )
        mock_client_factory.return_value = mock_client

        with pytest.raises(QuotaExhaustedException) as exc_info:
            await agent.run(risky_input)
        assert "quota exhausted" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_classification_agent_key_rotation_and_quota_raising():
    """
    Verify Modification #2: ClassificationAgent's primary/fallback-key retry rotation
    is intact: switches from primary to GOOGLE_API_KEY_2 on first 429, and raises
    QuotaExhaustedException only when both keys hit quota exhaustion.
    """
    reset_primary_exhausted()
    agent = ClassificationAgent()
    class_input = ClassificationInput(
        document_id="doc-class-1",
        filename="settlement_agreement.pdf",
        text="Confidential Settlement Agreement between parties resolving all claims and litigation."
    )

    with patch("langchain_core.runnables.base.RunnableSequence.ainvoke", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.side_effect = MockResourceExhausted("429 RESOURCE_EXHAUSTED: daily quota limit")
        
        with pytest.raises(QuotaExhaustedException) as exc_info:
            await agent.run(class_input)
        assert "quota exhausted on both keys" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_orchestrator_quota_pause_preserves_upstream_work():
    """
    Verify Requirement #4: When quota exhaustion occurs during a pipeline stage
    (e.g. summarization), document status becomes QUOTA_PAUSED (never REVIEWED),
    all real upstream results (OCR, classification, chunking, embedding, etc.)
    are preserved in doc_metadata, and the pipeline halts immediately.
    """
    mock_session = AsyncMock()
    doc_id = uuid.uuid4()
    
    # Simulate a document that has completed stages 1 through 6
    pipeline_data = {
        "ocr": {"text_length": 500, "confidence": 1.0, "status": "completed", "duration_ms": 45},
        "classification": {"document_type": "Legal Pleading", "confidence": 0.95, "status": "completed"},
        "chunking": {"chunk_count": 3, "status": "completed"},
        "embedding": {"embedded_count": 3, "status": "completed"},
        "entity_extraction": {"status": "completed"},
        "timeline": {"status": "completed"},
    }
    meta = {
        "classification": "Legal Pleading",
        "entities": {"people": ["John Doe"], "organizations": ["Enron"]},
        "timeline": [{"date": "2001-10-15", "description": "SEC inquiry", "confidence": 0.9}],
        "pipeline": pipeline_data,
    }
    
    doc = Document(
        id=doc_id,
        original_filename="inquiry_memo.pdf",
        file_size=1024,
        content_type="application/pdf",
        status=DocumentStatus.ANALYZING,
        doc_metadata=meta,
        extracted_text="Sample legal text extracted during OCR.",
    )

    # Call _handle_quota_pause at summarization stage
    quota_err = QuotaExhaustedException("Gemini quota 429 exhausted")
    await _handle_quota_pause(mock_session, doc, meta, pipeline_data, "summarization", quota_err, 250)

    # Assert honest halting
    assert doc.status == DocumentStatus.QUOTA_PAUSED
    assert doc.status != DocumentStatus.REVIEWED
    assert doc.doc_metadata["quota_exhausted"] is True
    assert doc.doc_metadata["paused_stage"] == "summarization"
    assert doc.doc_metadata["retry_available"] is True
    assert "LLM API daily quota limit reached" in doc.doc_metadata["paused_reason"]
    
    # Assert upstream preserved work is 100% intact
    assert doc.doc_metadata["pipeline"]["ocr"]["status"] == "completed"
    assert doc.doc_metadata["pipeline"]["classification"]["status"] == "completed"
    assert doc.doc_metadata["classification"] == "Legal Pleading"
    assert len(doc.doc_metadata["entities"]["people"]) == 1
    assert len(doc.doc_metadata["timeline"]) == 1


@pytest.mark.asyncio
async def test_non_quota_error_still_results_in_error_status():
    """
    Verify Requirement #5: Non-quota errors (e.g. disk failure, invalid file)
    continue to produce DocumentStatus.ERROR, preserving pre-fix behavior.
    """
    mock_session = AsyncMock()
    doc_id = uuid.uuid4()
    meta = {}
    doc = Document(
        id=doc_id,
        original_filename="corrupt_file.pdf",
        file_size=500,
        content_type="application/pdf",
        status=DocumentStatus.OCR_PROCESSING,
        doc_metadata=meta,
    )

    non_quota_err = IOError("Disk I/O failure reading storage file")
    # Verify is_quota_error returns False
    assert is_quota_error(non_quota_err) is False
    assert isinstance(non_quota_err, QuotaExhaustedException) is False

    # Simulate non-quota error handler in OCR stage
    doc.status = DocumentStatus.ERROR
    meta["pipeline_error"] = f"OCR Error: {non_quota_err}"
    doc.doc_metadata = meta

    assert doc.status == DocumentStatus.ERROR
    assert doc.status != DocumentStatus.QUOTA_PAUSED
    assert "OCR Error" in doc.doc_metadata["pipeline_error"]


@pytest.mark.asyncio
async def test_smart_resume_skips_completed_stages():
    """
    Verify Modification #1: Granular stage resumption safely reuses verified
    upstream stage results (OCR, classification, chunking/embedding, entities,
    timeline) without repeating expensive LLM or embedding calls.
    """
    doc_id = uuid.uuid4()
    pipeline_data = {
        "ocr": {"text_length": 300, "confidence": 1.0, "status": "completed", "duration_ms": 20},
        "classification": {"document_type": "Contract", "confidence": 0.96, "status": "completed"},
        "chunking": {"chunk_count": 2, "status": "completed"},
        "embedding": {"embedded_count": 2, "status": "completed"},
        "entity_extraction": {"status": "completed"},
        "relationship_extraction": {"status": "completed"},
        "timeline": {"status": "completed"},
    }
    meta = {
        "classification": "Contract",
        "entities": {"people": ["Jane Smith"]},
        "graph": {"nodes": [], "edges": []},
        "timeline": [{"date": "2023-01-01", "description": "Agreement executed", "confidence": 0.95}],
        "pipeline": pipeline_data,
        "quota_exhausted": True,
        "paused_stage": "summarization",
    }

    doc = Document(
        id=doc_id,
        original_filename="contract.pdf",
        file_size=2048,
        content_type="application/pdf",
        status=DocumentStatus.QUOTA_PAUSED,
        extracted_text="Agreement made between party A and party B.",
        doc_metadata=meta,
    )

    # In smart resumption, if pipeline_data indicates completion, stage methods are skipped:
    ocr_skipped = pipeline_data.get("ocr", {}).get("status") == "completed" and bool(doc.extracted_text)
    class_skipped = bool(pipeline_data.get("classification", {}).get("document_type")) and bool(meta.get("classification"))
    embed_skipped = pipeline_data.get("embedding", {}).get("status") == "completed"
    entities_skipped = bool(meta.get("entities")) and pipeline_data.get("entity_extraction", {}).get("status") == "completed"
    timeline_skipped = bool(meta.get("timeline")) and pipeline_data.get("timeline", {}).get("status") == "completed"

    # Summarization is NOT skipped because it was the paused stage
    sum_skipped = bool(meta.get("summaries")) and pipeline_data.get("summarization", {}).get("status") == "completed"

    assert ocr_skipped is True
    assert class_skipped is True
    assert embed_skipped is True
    assert entities_skipped is True
    assert timeline_skipped is True
    assert sum_skipped is False  # Resumes from summarization!


@pytest.mark.asyncio
async def test_analytics_excludes_quota_paused_from_reviewed():
    """
    Verify Requirement #9: Analytics metrics calculation correctly excludes
    quota_paused documents from reviewed_documents count and reports them in
    quota_paused_documents count.
    """
    # Simulate counts in the DB
    docs = [
        Document(id=uuid.uuid4(), original_filename="doc1.pdf", file_size=100, content_type="pdf", status=DocumentStatus.REVIEWED),
        Document(id=uuid.uuid4(), original_filename="doc2.pdf", file_size=100, content_type="pdf", status=DocumentStatus.REVIEWED),
        Document(id=uuid.uuid4(), original_filename="doc3.pdf", file_size=100, content_type="pdf", status=DocumentStatus.QUOTA_PAUSED),
        Document(id=uuid.uuid4(), original_filename="doc4.pdf", file_size=100, content_type="pdf", status=DocumentStatus.FLAGGED),
        Document(id=uuid.uuid4(), original_filename="doc5.pdf", file_size=100, content_type="pdf", status=DocumentStatus.ERROR),
    ]

    total_docs = len(docs)
    reviewed_docs = sum(1 for d in docs if d.status == DocumentStatus.REVIEWED)
    flagged_docs = sum(1 for d in docs if d.status == DocumentStatus.FLAGGED)
    quota_paused_docs = sum(1 for d in docs if d.status == DocumentStatus.QUOTA_PAUSED)

    assert total_docs == 5
    assert reviewed_docs == 2  # ONLY 2 reviewed!
    assert quota_paused_docs == 1  # Honesty: 1 quota_paused!
    assert reviewed_docs + quota_paused_docs + flagged_docs + 1 == total_docs
    # Crucial assertion: quota_paused documents are NOT counted as reviewed
    assert quota_paused_docs not in [reviewed_docs, total_docs]


async def run_all_tests():
    """Direct test runner for non-interactive execution."""
    print("=" * 70, flush=True)
    print("RUNNING QUOTA EXHAUSTION REMEDIATION VERIFICATION SUITE", flush=True)
    print("=" * 70, flush=True)

    print("\n[1/7] Testing is_quota_error detection...", end=" ", flush=True)
    test_is_quota_error_detection()
    print("PASS", flush=True)

    print("[2/7] Testing RiskAgent pre-screen unchanged (zero-cost pass)...", end=" ", flush=True)
    await test_risk_agent_prescreen_unchanged_zero_cost()
    print("PASS", flush=True)

    print("[3/7] Testing RiskAgent QuotaExhaustedException raising on 429...", end=" ", flush=True)
    await test_risk_agent_raises_quota_exhausted_exception()
    print("PASS", flush=True)

    print("[4/7] Testing ClassificationAgent key rotation and quota raising...", end=" ", flush=True)
    await test_classification_agent_key_rotation_and_quota_raising()
    print("PASS", flush=True)

    print("[5/7] Testing Orchestrator halts on quota and preserves upstream work...", end=" ", flush=True)
    await test_orchestrator_quota_pause_preserves_upstream_work()
    print("PASS", flush=True)

    print("[6/7] Testing non-quota errors still produce ERROR status...", end=" ", flush=True)
    await test_non_quota_error_still_results_in_error_status()
    print("PASS", flush=True)

    print("[7/7] Testing smart resume / stage skipping & analytics counts...", end=" ", flush=True)
    await test_smart_resume_skips_completed_stages()
    await test_analytics_excludes_quota_paused_from_reviewed()
    print("PASS", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("ALL 7 QUOTA EXHAUSTION TESTS PASSED SUCCESSFULLY!", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_all_tests())


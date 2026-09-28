import pytest
from app.agents.ocr import (
    OCRAgent,
    OCRInput,
    OCREngineResult,
    BaseOCREngine,
    OCREngineException,
    AgentException
)

class MockFailingEngine(BaseOCREngine):
    def __init__(self, name):
        self.name = name
    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        raise OCREngineException(f"{self.name} failed to process")


class MockSuccessfulEngine(BaseOCREngine):
    def __init__(self, name, text):
        self.name = name
        self.text = text
    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        return OCREngineResult(
            text=self.text,
            confidence=0.95,
            page_number=page_number,
            layout={"type": "text"},
            bounding_boxes=[{"box": [0,0,10,10]}],
            reading_order=[0]
        )


@pytest.fixture
def mock_pdf():
    return "dummy/path/to/doc.pdf"


@pytest.mark.asyncio
async def test_ocr_extracts_text(mock_pdf):
    # Test that the first engine succeeds
    engines = [MockSuccessfulEngine("PaddleOCR", "Extracted Text")]
    agent = OCRAgent(engines=engines)
    
    input_data = OCRInput(
        file_path=mock_pdf,
        document_type="PDF",
        page_number=1
    )
    
    result = await agent.run(input_data)
    assert result.text == "Extracted Text"
    assert result.engine_used == "PaddleOCR"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_ocr_fallback_works(mock_pdf):
    # Test that it falls back if earlier engines fail
    engines = [
        MockFailingEngine("PaddleOCR"),
        MockFailingEngine("DocTR"),
        MockSuccessfulEngine("Tesseract", "Fallback Text"),
        MockSuccessfulEngine("EasyOCR", "Should Not Reach Here")
    ]
    agent = OCRAgent(engines=engines)
    
    input_data = OCRInput(
        file_path=mock_pdf,
        document_type="PDF",
        page_number=1
    )
    
    result = await agent.run(input_data)
    assert result.text == "Fallback Text"
    assert result.engine_used == "Tesseract"


@pytest.mark.asyncio
async def test_ocr_all_engines_fail(mock_pdf):
    # Test that it raises an error if all fail
    engines = [
        MockFailingEngine("PaddleOCR"),
        MockFailingEngine("DocTR")
    ]
    agent = OCRAgent(engines=engines)
    
    input_data = OCRInput(
        file_path=mock_pdf,
        document_type="PDF",
        page_number=1
    )
    
    with pytest.raises(AgentException, match="All OCR engines failed"):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_heuristic_fallback_raises_honestly_without_mock_text(tmp_path):
    from app.agents.ocr import HeuristicFallbackEngine
    engine = HeuristicFallbackEngine()

    # 1. Test empty file named with old trigger keywords
    empty_meridian = tmp_path / "meridian_agreement.pdf"
    empty_meridian.write_text("", encoding="utf-8")
    with pytest.raises(OCREngineException, match="Heuristic fallback failed:"):
        engine.process(str(empty_meridian), 1)

    # 2. Test binary non-text file named with old SEC trigger keywords
    binary_sec = tmp_path / "sec_filing.bin"
    binary_sec.write_bytes(b"\x00\x01\x02\x03\x04\xff\xfe")
    with pytest.raises(OCREngineException, match="Heuristic fallback failed:"):
        engine.process(str(binary_sec), 1)


@pytest.mark.asyncio
async def test_llm_ocr_engine_raises_honestly_when_unconfigured(tmp_path):
    from app.agents.ocr import LLMOCREngine
    engine = LLMOCREngine()
    engine.llm = None

    test_file = tmp_path / "sample_doc.txt"
    test_file.write_text("Some text content", encoding="utf-8")

    with pytest.raises(OCREngineException, match="LLM client is not configured or initialized"):
        engine.process(str(test_file), 1)


@pytest.mark.asyncio
async def test_default_ocr_cascade_corrupt_file_honest_failure(tmp_path):
    # Tests the full default cascade on an unreadable binary file
    agent = OCRAgent()
    corrupt_file = tmp_path / "corrupt_document.bin"
    corrupt_file.write_bytes(b"\x00\x01\x02\x03\x04\xff\xfe")

    input_data = OCRInput(
        file_path=str(corrupt_file),
        document_type="application/octet-stream",
        page_number=1
    )

    with pytest.raises(AgentException) as exc_info:
        await agent.run(input_data)

    err_msg = str(exc_info.value)
    assert "All OCR engines failed for 'corrupt_document.bin'" in err_msg
    assert "PlainText" in err_msg
    assert "pypdf" in err_msg
    assert "Heuristic-Fallback" in err_msg
    # Ensure no fabricated names in error message
    assert "meridian" not in err_msg.lower()
    assert "whitfield" not in err_msg.lower()


@pytest.mark.asyncio
async def test_real_plain_text_success_path(tmp_path):
    agent = OCRAgent()
    text_file = tmp_path / "real_legal_notice.txt"
    expected_content = "Notice of Deposition in Case 2026-CV-001. All parties shall appear on September 15."
    text_file.write_text(expected_content, encoding="utf-8")

    input_data = OCRInput(
        file_path=str(text_file),
        document_type="text/plain",
        page_number=1
    )

    result = await agent.run(input_data)
    assert result.text == expected_content
    assert result.engine_used == "PlainText"
    assert result.confidence == 1.0
    assert result.ocr_status == "completed"
    assert result.error is None


@pytest.mark.asyncio
async def test_real_pypdf_success_path():
    import os
    pdf_path = "backend/uploads/210e3b36e9e2474d92a42744ddd9b461.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip(f"Test PDF not present at {pdf_path}")

    agent = OCRAgent()
    input_data = OCRInput(
        file_path=pdf_path,
        document_type="application/pdf",
        page_number=1
    )

    result = await agent.run(input_data)
    assert len(result.text) > 100
    assert "Lease Deed" in result.text or "rent" in result.text.lower()
    assert result.engine_used == "pypdf"
    assert result.confidence == 1.0
    assert result.ocr_status == "completed"
    assert result.error is None


@pytest.mark.asyncio
async def test_ocr_both_deterministic_and_llm_fail_returns_honest_agent_exception(tmp_path):
    engines = [
        MockFailingEngine("pypdf"),
        MockFailingEngine("Tesseract"),
        MockFailingEngine("LLM-OCR"),
        MockFailingEngine("Heuristic-Fallback"),
    ]
    agent = OCRAgent(engines=engines)
    test_pdf = tmp_path / "scanned_brief.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 dummy non-extractable content")

    input_data = OCRInput(
        file_path=str(test_pdf),
        document_type="application/pdf",
        page_number=1
    )

    with pytest.raises(AgentException) as exc_info:
        await agent.run(input_data)

    err = str(exc_info.value)
    assert "All OCR engines failed for 'scanned_brief.pdf'" in err
    assert "pypdf" in err
    assert "LLM-OCR" in err
    assert "meridian" not in err.lower()
    assert "whitfield" not in err.lower()


@pytest.mark.asyncio
async def test_heuristic_fallback_rejects_binary_pdf(tmp_path):
    from app.agents.ocr import HeuristicFallbackEngine
    engine = HeuristicFallbackEngine()
    test_pdf = tmp_path / "sample_scanned.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 1 0 obj << /Type /Catalog >> endobj")

    with pytest.raises(OCREngineException, match="Cannot extract text from binary or scanned format"):
        engine.process(str(test_pdf), 1)


@pytest.mark.asyncio
async def test_orchestrator_ocr_failure_routes_to_error_status_with_status_history(tmp_path):
    import uuid
    from unittest.mock import AsyncMock, patch
    from app.models.document import Document, DocumentStatus
    from app.models.status_history import StatusHistory
    from app.services.orchestrator import run_document_pipeline
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from app.db.base import Base
    import app.db.session as db_session_module

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    SessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    orig_session_local = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = SessionLocal

    try:
        user_id = uuid.uuid4()
        doc_id = uuid.uuid4()
        test_file = tmp_path / "corrupted_scan.pdf"
        test_file.write_bytes(b"\x00\x01\x02\x03\x04")

        async with SessionLocal() as session:
            doc = Document(
                id=doc_id,
                uploaded_by=user_id,
                filename="corrupted_scan.pdf",
                original_filename="corrupted_scan.pdf",
                file_size=5,
                content_type="application/pdf",
                storage_path=str(test_file),
                status=DocumentStatus.UPLOADED,
                doc_metadata={},
            )
            session.add(doc)
            await session.commit()

        class MockStorageCtx:
            def __init__(self, path):
                self.path = path
            async def __aenter__(self):
                return self.path
            async def __aexit__(self, *args):
                pass

        class MockStorageService:
            def get_local_filepath(self, storage_path):
                return MockStorageCtx(storage_path)

        with patch("app.services.orchestrator.AsyncSessionLocal", SessionLocal), \
             patch("app.services.storage_service.get_storage_service", return_value=MockStorageService()):
            await run_document_pipeline(str(doc_id))

        async with SessionLocal() as session:
            from sqlalchemy import select
            res_doc = await session.execute(select(Document).where(Document.id == doc_id))
            saved_doc = res_doc.scalar_one()

            # Verify document routed to ERROR status and extracted_text is None
            assert saved_doc.status == DocumentStatus.ERROR
            assert saved_doc.extracted_text is None

            # Verify status_history records ocr_extraction_failed_both_engines transition
            res_hist = await session.execute(
                select(StatusHistory).where(StatusHistory.document_id == doc_id).order_by(StatusHistory.changed_at.asc())
            )
            history_rows = res_hist.scalars().all()
            assert len(history_rows) >= 2
            error_transition = history_rows[-1]
            assert error_transition.new_status == DocumentStatus.ERROR.value
            assert error_transition.reason == "ocr_extraction_failed_both_engines"
    finally:
        db_session_module.AsyncSessionLocal = orig_session_local
        await test_engine.dispose()



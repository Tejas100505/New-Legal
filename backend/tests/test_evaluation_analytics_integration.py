import pytest
import uuid
import time
from unittest.mock import AsyncMock, MagicMock

from app.models.evaluation import EvaluationMetric
from app.repositories.evaluation_repository import EvaluationRepository
from app.agents.ocr import OCRAgent, OCRInput
from app.agents.embedding import EmbeddingAgent, EmbeddingInput, ChunkData
from app.agents.report import ReportAgent, ReportInput

# ── 1. OCR Cascade & Traceability Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_ocr_fallback_cascade_and_logging():
    # Verify the fallback cascade operates as expected and logs the engine used
    agent = OCRAgent()
    
    # We will pass a plain text file that triggers the heuristic fallback engine
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write("Case details: Meridian Corp vs Miller. Signed 2023-05-14.")
        temp_file_path = temp_file.name
        
    try:
        input_data = OCRInput(
            file_path=temp_file_path,
            document_type="TXT",
            page_number=1
        )
        
        result = await agent.run(input_data)
        assert result.text is not None
        assert "meridian" in result.text.lower()
        # Should have fallen back to Heuristic-Fallback or Plain-Text
        assert result.engine_used in ["PlainText", "Heuristic-Fallback", "LLM-OCR", "Tesseract", "pypdf"]
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# ── 2. Embedding Model Vector Unit Projection Tests ─────────────────────────

@pytest.mark.asyncio
async def test_local_embedding_projection_determinism():
    agent = EmbeddingAgent()
    
    chunk1 = ChunkData(
        chunk_id="chunk_1",
        document_id="doc_1",
        page=1,
        section="header",
        text="Semiconductor planarization patent infringement.",
        metadata={}
    )
    chunk2 = ChunkData(
        chunk_id="chunk_2",
        document_id="doc_1",
        page=1,
        section="header",
        text="Semiconductor planarization patent infringement.",
        metadata={}
    )
    chunk3 = ChunkData(
        chunk_id="chunk_3",
        document_id="doc_1",
        page=2,
        section="footer",
        text="A completely unrelated sentence about corporate taxes.",
        metadata={}
    )
    
    res = await agent.run(EmbeddingInput(chunks=[chunk1, chunk2, chunk3]))
    
    vec1 = res.embedded_chunks[0].embedding
    vec2 = res.embedded_chunks[1].embedding
    vec3 = res.embedded_chunks[2].embedding
    
    # Assert dimension is 1024
    assert len(vec1) == 1024
    
    # Assert valid non-zero embedding
    import math
    norm1 = math.sqrt(sum(x * x for x in vec1))
    assert norm1 > 0
    
    # Assert determinism (same text = same vector)
    assert vec1 == vec2
    
    # Assert cosine similarity behaves logically
    dot_product_same = sum(x * y for x, y in zip(vec1, vec2))
    dot_product_diff = sum(x * y for x, y in zip(vec1, vec3))
    
    assert dot_product_same > dot_product_diff


# ── 3. Report Exports Base64 Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_exports_format_encoding():
    from app.agents.report import REPORTLAB_AVAILABLE
    if not REPORTLAB_AVAILABLE:
        pytest.skip("ReportLab is not installed or available.")

    agent = ReportAgent()
    
    inp = ReportInput(
        document_id="doc_123",
        format="pdf",
        timeline=[{"date": "2023-05-14", "description": "Contract Signed"}],
        risks=[{"category": "NDA Breach", "risk_level": "High", "reason": "Confidential info leaked"}],
        recommendations=["File immediate injunction"]
    )
    
    # Test PDF base64 format
    pdf_res = await agent.run(inp)
    assert pdf_res.format == "pdf"
    # Should be valid base64 string
    import base64
    try:
        decoded_pdf = base64.b64decode(pdf_res.content)
        assert len(decoded_pdf) > 0
    except Exception:
        pytest.fail("PDF output is not valid base64")

    # Test DOCX base64 format
    inp.format = "docx"
    docx_res = await agent.run(inp)
    assert docx_res.format == "docx"
    try:
        decoded_docx = base64.b64decode(docx_res.content)
        assert len(decoded_docx) > 0
    except Exception:
        pytest.fail("DOCX output is not valid base64")


# ── 4. Repository & Database Aggregation Tests ──────────────────────────────

@pytest.mark.asyncio
async def test_evaluation_repository_and_aggregations():
    # Setup mock session to check SQL execution
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()
    
    repo = EvaluationRepository(mock_session)
    
    case_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    
    # Test Create
    await repo.create(
        case_id=case_id,
        document_id=doc_id,
        metric_type="review",
        ocr_accuracy=0.98,
        hallucination_rate=0.05,
        latency_ms=1200.0,
        token_usage={"total_tokens": 300}
    )
    
    assert mock_session.add.call_count == 1
    
    # Test aggregate calculations mock return
    mock_result = MagicMock()
    # Mocking row returned from fetchone query
    mock_result.fetchone = MagicMock(return_value=MagicMock(
        avg_ocr_accuracy=0.98,
        avg_retrieval_precision=None,
        avg_retrieval_recall=None,
        avg_semantic_similarity=None,
        avg_hallucination_rate=0.05,
        latency_ms=1200.0,
        avg_graph_generation_time_ms=None,
        avg_privilege_accuracy=None,
        total_records=1
    ))
    
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    aggs = await repo.get_aggregates_by_case(case_id)
    assert aggs["total_records"] == 1
    assert aggs["avg_ocr_accuracy"] == 0.98


# ── 5. Analytics Endpoint Real-Data Integration Tests ───────────────────────

TEST_ANALYTICS_DB_URL = "sqlite+aiosqlite:///./test_analytics_eval.db"
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient

analytics_engine = create_async_engine(TEST_ANALYTICS_DB_URL, echo=False)
AnalyticsSessionLocal = async_sessionmaker(bind=analytics_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module
from app.db.session import get_db
from app.db.base import Base
from app.main import app
from app.models.case import Case, CaseStatus, CasePriority
from app.models.document import Document, DocumentStatus
from app.auth.dependencies import create_access_token, UserRole


async def override_analytics_get_db():
    async with AnalyticsSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.mark.asyncio
async def test_analytics_endpoint_honest_metrics_and_tenant_isolation():
    """
    Integration test for GET /api/v1/analytics verifying:
    1. total_entities_detected matches an independently computed sum from fixture data.
    2. avg_review_time_seconds is None (asserted with `is None`).
    3. avg_confidence_score is None (asserted with `is None`).
    4. QUOTA_PAUSED documents with doc_metadata['entities'] are strictly excluded.
    5. Two-user/two-case tenant isolation: User A cannot see User B's entities.
    6. Admin role can aggregate across all tenants honestly.
    """
    # Initialize SQLite database schema
    async with analytics_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Set dependency override
    app.dependency_overrides[get_db] = override_analytics_get_db
    original_session_local = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = AnalyticsSessionLocal

    client = TestClient(app)

    try:
        user_a_id = str(uuid.uuid4())
        user_b_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())

        token_a = create_access_token(user_id=user_a_id, email="alice@firm-a.com", role=UserRole.LAWYER)
        token_b = create_access_token(user_id=user_b_id, email="bob@firm-b.com", role=UserRole.LAWYER)
        token_admin = create_access_token(user_id=admin_id, email="admin@corp.com", role=UserRole.ADMIN)

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        case_a_id = uuid.uuid4()
        case_b_id = uuid.uuid4()

        # Helper to independently count entities across both production dict-of-categories and list formats
        def count_entities(entities_data):
            if isinstance(entities_data, dict):
                return sum(len(v) for v in entities_data.values() if isinstance(v, list))
            elif isinstance(entities_data, list):
                return len(entities_data)
            return 0

        # Define fixture documents for User A:
        # Mix of production dict-of-categories format and list format to verify both shapes
        fixture_docs_a = [
            {
                "id": uuid.uuid4(),
                "case_id": case_a_id,
                "status": DocumentStatus.REVIEWED,
                "filename": "contract_a.pdf",
                # Production dict-of-categories shape (3 entities)
                "entities": {
                    "organizations": ["Acme Corp"],
                    "people": ["John Doe"],
                    "dates": ["2023-01-01"],
                },
            },
            {
                "id": uuid.uuid4(),
                "case_id": case_a_id,
                "status": DocumentStatus.FLAGGED,
                "filename": "email_a.pdf",
                # List of objects shape (2 entities)
                "entities": [{"name": "Secret Project"}, {"name": "Jane Smith"}],
            },
            {
                # Must be EXCLUDED from total_entities_detected
                "id": uuid.uuid4(),
                "case_id": case_a_id,
                "status": DocumentStatus.QUOTA_PAUSED,
                "filename": "paused_doc.pdf",
                # Production dict-of-categories shape (3 entities)
                "entities": {
                    "people": ["PausedEntity1", "PausedEntity2"],
                    "locations": ["Houston"],
                },
            },
            {
                # Must be EXCLUDED from total_entities_detected
                "id": uuid.uuid4(),
                "case_id": case_a_id,
                "status": DocumentStatus.UPLOADED,
                "filename": "uploaded_doc.pdf",
                # Flat list format (1 entity)
                "entities": [{"name": "UploadedEntity1"}],
            },
            {
                # Must be EXCLUDED from total_entities_detected
                "id": uuid.uuid4(),
                "case_id": case_a_id,
                "status": DocumentStatus.ERROR,
                "filename": "error_doc.pdf",
                # Production dict-of-categories shape (1 entity)
                "entities": {"money": ["$1,000,000"]},
            },
        ]

        # Define fixture documents for User B
        fixture_docs_b = [
            {
                "id": uuid.uuid4(),
                "case_id": case_b_id,
                "status": DocumentStatus.REVIEWED,
                "filename": "beta_filing.pdf",
                # Production dict-of-categories shape (4 entities)
                "entities": {
                    "organizations": ["Beta Corp"],
                    "case_numbers": ["ENRON-2001-B"],
                    "locations": ["California", "Washington"],
                },
            },
        ]

        # Independently calculate expected entity counts using python logic
        # Negative exclude-list of statuses:
        excluded_statuses = {
            DocumentStatus.UPLOADED,
            DocumentStatus.VALIDATING,
            DocumentStatus.OCR_PROCESSING,
            DocumentStatus.CHUNKING,
            DocumentStatus.EMBEDDING,
            DocumentStatus.ANALYZING,
            DocumentStatus.QUOTA_PAUSED,
            DocumentStatus.ERROR,
        }

        expected_user_a_entities = sum(
            count_entities(doc["entities"]) for doc in fixture_docs_a
            if doc["status"] not in excluded_statuses
        )
        quota_paused_entities_user_a = sum(
            count_entities(doc["entities"]) for doc in fixture_docs_a
            if doc["status"] == DocumentStatus.QUOTA_PAUSED
        )
        expected_user_b_entities = sum(
            count_entities(doc["entities"]) for doc in fixture_docs_b
            if doc["status"] not in excluded_statuses
        )
        expected_admin_entities = expected_user_a_entities + expected_user_b_entities

        # Independently calculate expected storage bytes
        expected_user_a_storage = sum(
            1024 for doc in fixture_docs_a
            if doc["status"] not in excluded_statuses
        )
        expected_user_b_storage = sum(
            2048 for doc in fixture_docs_b
            if doc["status"] not in excluded_statuses
        )
        expected_admin_storage = expected_user_a_storage + expected_user_b_storage

        # Persist cases and documents to SQLite
        async with AnalyticsSessionLocal() as session:
            case_a = Case(
                id=case_a_id,
                name="Case Alpha",
                case_number="ALPHA-001",
                status=CaseStatus.CREATED,
                priority=CasePriority.MEDIUM,
                created_by=user_a_id,
            )
            case_b = Case(
                id=case_b_id,
                name="Case Beta",
                case_number="BETA-001",
                status=CaseStatus.CREATED,
                priority=CasePriority.HIGH,
                created_by=user_b_id,
            )
            session.add(case_a)
            session.add(case_b)

            for doc_info in fixture_docs_a:
                d = Document(
                    id=doc_info["id"],
                    case_id=doc_info["case_id"],
                    uploaded_by=uuid.UUID(user_a_id),
                    filename=doc_info["filename"],
                    original_filename=doc_info["filename"],
                    content_type="application/pdf",
                    file_size=1024,
                    storage_path=f"/tmp/{doc_info['filename']}",
                    status=doc_info["status"],
                    doc_metadata={"entities": doc_info["entities"]},
                )
                session.add(d)

            for doc_info in fixture_docs_b:
                d = Document(
                    id=doc_info["id"],
                    case_id=doc_info["case_id"],
                    uploaded_by=uuid.UUID(user_b_id),
                    filename=doc_info["filename"],
                    original_filename=doc_info["filename"],
                    content_type="application/pdf",
                    file_size=2048,
                    storage_path=f"/tmp/{doc_info['filename']}",
                    status=doc_info["status"],
                    doc_metadata={"entities": doc_info["entities"]},
                )
                session.add(d)

            await session.commit()

        # ── Test 1: User A Analytics Query ──
        res_a = client.get("/api/v1/analytics", headers=headers_a)
        assert res_a.status_code == 200, f"User A query failed: {res_a.text}"
        data_a = res_a.json()
        assert "metrics" in data_a, f"Malformed response: {data_a}"
        metrics_a = data_a["metrics"]

        # 1a. Assert total_entities_detected matches independently-computed sum
        assert metrics_a["total_entities_detected"] == expected_user_a_entities, (
            f"Expected {expected_user_a_entities} entities for User A, got {metrics_a['total_entities_detected']}"
        )

        # 1b. Assert QUOTA_PAUSED entities are strictly excluded
        assert metrics_a["total_entities_detected"] != (expected_user_a_entities + quota_paused_entities_user_a), (
            "QUOTA_PAUSED entities were incorrectly included in total_entities_detected!"
        )

        # 1c. Assert avg_review_time_seconds is None
        assert metrics_a["avg_review_time_seconds"] is None, (
            f"Expected None for avg_review_time_seconds, got {metrics_a['avg_review_time_seconds']}"
        )

        # 1d. Assert avg_confidence_score is None
        assert metrics_a["avg_confidence_score"] is None, (
            f"Expected None for avg_confidence_score, got {metrics_a['avg_confidence_score']}"
        )

        # 1e. Assert User B's entities are NOT included (tenant isolation)
        assert metrics_a["total_entities_detected"] != (expected_user_a_entities + expected_user_b_entities), (
            "Cross-tenant leak: User A received entities from User B!"
        )

        # 1f. Assert total_storage_bytes matches independently-computed sum
        assert metrics_a["total_storage_bytes"] == expected_user_a_storage, (
            f"Expected {expected_user_a_storage} bytes for User A, got {metrics_a['total_storage_bytes']}"
        )

        # ── Test 2: User B Analytics Query ──
        res_b = client.get("/api/v1/analytics", headers=headers_b)
        assert res_b.status_code == 200, f"User B query failed: {res_b.text}"
        data_b = res_b.json()
        metrics_b = data_b["metrics"]

        assert metrics_b["total_entities_detected"] == expected_user_b_entities, (
            f"Expected {expected_user_b_entities} entities for User B, got {metrics_b['total_entities_detected']}"
        )
        assert metrics_b["total_storage_bytes"] == expected_user_b_storage, (
            f"Expected {expected_user_b_storage} bytes for User B, got {metrics_b['total_storage_bytes']}"
        )
        assert metrics_b["avg_review_time_seconds"] is None
        assert metrics_b["avg_confidence_score"] is None

        # ── Test 3: Admin Override Analytics Query ──
        res_admin = client.get("/api/v1/analytics", headers=headers_admin)
        assert res_admin.status_code == 200, f"Admin query failed: {res_admin.text}"
        data_admin = res_admin.json()
        metrics_admin = data_admin["metrics"]

        assert metrics_admin["total_entities_detected"] == expected_admin_entities, (
            f"Expected {expected_admin_entities} entities for Admin override, got {metrics_admin['total_entities_detected']}"
        )
        assert metrics_admin["total_storage_bytes"] == expected_admin_storage, (
            f"Expected {expected_admin_storage} bytes for Admin override, got {metrics_admin['total_storage_bytes']}"
        )
        assert metrics_admin["avg_review_time_seconds"] is None
        assert metrics_admin["avg_confidence_score"] is None

        # ── Test 4: Case Scoping & Tenant Security ──
        # User A requesting own case:
        res_case_a = client.get(f"/api/v1/analytics?case_id={case_a_id}", headers=headers_a)
        assert res_case_a.status_code == 200
        assert res_case_a.json()["metrics"]["total_entities_detected"] == expected_user_a_entities
        assert res_case_a.json()["metrics"]["total_storage_bytes"] == expected_user_a_storage

        # User A attempting to request User B's case:
        res_cross = client.get(f"/api/v1/analytics?case_id={case_b_id}", headers=headers_a)
        assert res_cross.status_code == 403, (
            f"Expected 403 Forbidden on cross-tenant case analytics, got {res_cross.status_code}"
        )

    finally:
        app.dependency_overrides.pop(get_db, None)
        db_session_module.AsyncSessionLocal = original_session_local


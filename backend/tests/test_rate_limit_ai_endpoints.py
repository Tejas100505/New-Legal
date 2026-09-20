"""
Integration tests verifying SlowAPI rate limiting across all AI and expensive endpoints.

Endpoints verified:
- POST /api/v1/documents/upload          (60/min)
- POST /api/v1/documents/upload-multiple (10/min)
- POST /api/v1/documents/{id}/retry      (10/min)
- POST /api/v1/search                    (20/min)
- POST /api/v1/embed                     (10/min)
- POST /api/v1/review                    (5/min)
- POST /api/v1/clusters                  (10/min)
- POST /api/v1/classify                  (15/min)
- POST /api/v1/timeline                  (15/min)
- POST /api/v1/entities                  (20/min)
- POST /api/v1/relationships             (20/min)
- POST /api/v1/ocr                       (20/min)
"""

import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_rate_limit_ai.db"
rate_engine = create_async_engine(TEST_DB_URL, echo=False)
RateSessionLocal = async_sessionmaker(bind=rate_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module
db_session_module.AsyncSessionLocal = RateSessionLocal

from app.main import app
from app.db.base import Base
from app.core.rate_limit import limiter
from app.auth.dependencies import create_access_token, UserRole


from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from app.schemas.document import DocumentUploadResponse, DocumentStatus

@pytest.fixture(autouse=True)
def mock_background_pipeline_and_upload():
    mock_resp = DocumentUploadResponse(
        id=uuid.uuid4(),
        filename="mock.txt",
        content_type="text/plain",
        file_size=100,
        status=DocumentStatus.UPLOADED,
        created_at=datetime.now(timezone.utc),
    )
    with patch("app.api.v1.documents.run_document_pipeline", new_callable=AsyncMock), \
         patch("app.api.v1.documents.DocumentService.upload_document", new_callable=AsyncMock, return_value=mock_resp):
        yield


async def init_test_db():
    limiter.reset()
    db_session_module.AsyncSessionLocal = RateSessionLocal
    async with rate_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_auth_headers(user_id: str = None) -> dict[str, str]:
    uid = user_id or str(uuid.uuid4())
    token = create_access_token(user_id=uid, email=f"user_{uid[:6]}@lawfirm.com", role=UserRole.LAWYER)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_documents_upload_batch_safety_20_requests():
    """
    Demonstrates batch-safety: A normal legal document review batch upload
    of 20 files in a loop from the same IP succeeds well under the 60/min ceiling.
    """
    await init_test_db()
    headers = get_auth_headers()
    client = TestClient(app, client=("192.168.100.1", 50000))

    for i in range(1, 21):
        file_content = f"Test document content {i}".encode("utf-8")
        files = {"file": (f"test_batch_{i}.txt", io.BytesIO(file_content), "text/plain")}
        res = client.post("/api/v1/documents/upload", files=files, headers=headers)
        assert res.status_code == 201, f"Request {i} unexpectedly failed with status {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_documents_upload_rate_limiting_60_per_minute():
    """
    Verify /api/v1/documents/upload enforces 60 requests per minute per IP:
    Requests 1-60 succeed, request 61 receives HTTP 429, and a second client IP is not blocked.
    """
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.100.10", 50000))
    client2 = TestClient(app, client=("192.168.100.11", 50000))

    for i in range(1, 61):
        file_content = f"Doc content {i}".encode("utf-8")
        files = {"file": (f"doc_{i}.txt", io.BytesIO(file_content), "text/plain")}
        res = client1.post("/api/v1/documents/upload", files=files, headers=headers)
        assert res.status_code == 201, f"Expected 201 on attempt {i}, got {res.status_code}"

    # 61st request from client 1 -> 429
    file_content_61 = b"Doc content 61"
    res61 = client1.post(
        "/api/v1/documents/upload",
        files={"file": ("doc_61.txt", io.BytesIO(file_content_61), "text/plain")},
        headers=headers,
    )
    assert res61.status_code == 429
    assert "rate limit exceeded" in str(res61.json()).lower()

    # Cross-client check: client 2 (different IP) is not blocked
    res_c2 = client2.post(
        "/api/v1/documents/upload",
        files={"file": ("c2_doc.txt", io.BytesIO(b"C2 doc"), "text/plain")},
        headers=headers,
    )
    assert res_c2.status_code == 201


@pytest.mark.asyncio
async def test_documents_upload_multiple_rate_limiting_10_per_minute():
    """Verify /api/v1/documents/upload-multiple enforces 10 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.101.1", 50000))
    client2 = TestClient(app, client=("192.168.101.2", 50000))

    for i in range(1, 11):
        files = [
            ("files", (f"multi_{i}_a.txt", io.BytesIO(b"File A"), "text/plain")),
            ("files", (f"multi_{i}_b.txt", io.BytesIO(b"File B"), "text/plain")),
        ]
        res = client1.post("/api/v1/documents/upload-multiple", files=files, headers=headers)
        assert res.status_code == 201, f"Expected 201 on attempt {i}, got {res.status_code}"

    # 11th request -> 429
    files11 = [("files", ("multi_11.txt", io.BytesIO(b"File 11"), "text/plain"))]
    res11 = client1.post("/api/v1/documents/upload-multiple", files=files11, headers=headers)
    assert res11.status_code == 429
    assert "rate limit exceeded" in str(res11.json()).lower()

    # Cross-client check
    res_c2 = client2.post("/api/v1/documents/upload-multiple", files=files11, headers=headers)
    assert res_c2.status_code == 201


@pytest.mark.asyncio
async def test_documents_retry_rate_limiting_10_per_minute():
    """Verify /api/v1/documents/{id}/retry enforces 10 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.102.1", 50000))
    client2 = TestClient(app, client=("192.168.102.2", 50000))

    fake_id = str(uuid.uuid4())
    # 10 requests allowed to reach business logic (returns 404 for nonexistent document)
    for i in range(1, 11):
        res = client1.post(f"/api/v1/documents/{fake_id}/retry", headers=headers)
        assert res.status_code == 404, f"Expected 404 on attempt {i}, got {res.status_code}"

    # 11th request returns 429 (limiter triggers before route logic)
    res11 = client1.post(f"/api/v1/documents/{fake_id}/retry", headers=headers)
    assert res11.status_code == 429
    assert "rate limit exceeded" in str(res11.json()).lower()

    # Cross-client check
    res_c2 = client2.post(f"/api/v1/documents/{fake_id}/retry", headers=headers)
    assert res_c2.status_code == 404


@pytest.mark.asyncio
async def test_search_rate_limiting_20_per_minute():
    """Verify /api/v1/search enforces 20 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.103.1", 50000))
    client2 = TestClient(app, client=("192.168.103.2", 50000))

    search_payload = {"query": "contract dispute", "top_k": 5}
    # Requests 1 to 20 are allowed (200 with empty results for empty DB)
    for i in range(1, 21):
        res = client1.post("/api/v1/search", json=search_payload, headers=headers)
        assert res.status_code == 200, f"Expected 200 on attempt {i}, got {res.status_code}"

    # 21st request returns 429
    res21 = client1.post("/api/v1/search", json=search_payload, headers=headers)
    assert res21.status_code == 429
    assert "rate limit exceeded" in str(res21.json()).lower()

    # Cross-client check
    res_c2 = client2.post("/api/v1/search", json=search_payload, headers=headers)
    assert res_c2.status_code == 200


@pytest.mark.asyncio
async def test_embed_rate_limiting_10_per_minute():
    """Verify /api/v1/embed enforces 10 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.104.1", 50000))
    client2 = TestClient(app, client=("192.168.104.2", 50000))

    embed_payload = {"document_id": str(uuid.uuid4()), "embedding_provider": "sentence_transformers"}
    # Requests 1 to 10 allowed (returns 404 for nonexistent document)
    for i in range(1, 11):
        res = client1.post("/api/v1/embed", json=embed_payload, headers=headers)
        assert res.status_code == 404, f"Expected 404 on attempt {i}, got {res.status_code}"

    # 11th request returns 429
    res11 = client1.post("/api/v1/embed", json=embed_payload, headers=headers)
    assert res11.status_code == 429
    assert "rate limit exceeded" in str(res11.json()).lower()

    # Cross-client check
    res_c2 = client2.post("/api/v1/embed", json=embed_payload, headers=headers)
    assert res_c2.status_code == 404


@pytest.mark.asyncio
async def test_review_rate_limiting_5_per_minute():
    """Verify /api/v1/review enforces 5 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.105.1", 50000))
    client2 = TestClient(app, client=("192.168.105.2", 50000))

    review_payload = {"document_ids": []}
    # Requests 1 to 5 allowed (returns 200 with empty review result)
    for i in range(1, 6):
        res = client1.post("/api/v1/review", json=review_payload, headers=headers)
        assert res.status_code == 200, f"Expected 200 on attempt {i}, got {res.status_code}"

    # 6th request returns 429
    res6 = client1.post("/api/v1/review", json=review_payload, headers=headers)
    assert res6.status_code == 429
    assert "rate limit exceeded" in str(res6.json()).lower()

    # Cross-client check
    res_c2 = client2.post("/api/v1/review", json=review_payload, headers=headers)
    assert res_c2.status_code == 200


@pytest.mark.asyncio
async def test_clusters_rate_limiting_10_per_minute():
    """Verify /api/v1/clusters enforces 10 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.106.1", 50000))
    client2 = TestClient(app, client=("192.168.106.2", 50000))

    cluster_payload = {"document_ids": []}
    for i in range(1, 11):
        res = client1.post("/api/v1/clusters", json=cluster_payload, headers=headers)
        assert res.status_code == 200, f"Expected 200 on attempt {i}, got {res.status_code}"

    res11 = client1.post("/api/v1/clusters", json=cluster_payload, headers=headers)
    assert res11.status_code == 429
    assert "rate limit exceeded" in str(res11.json()).lower()

    res_c2 = client2.post("/api/v1/clusters", json=cluster_payload, headers=headers)
    assert res_c2.status_code == 200


@pytest.mark.asyncio
async def test_classify_rate_limiting_15_per_minute():
    """Verify /api/v1/classify enforces 15 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.107.1", 50000))
    client2 = TestClient(app, client=("192.168.107.2", 50000))

    payload = {"document_id": str(uuid.uuid4())}
    for i in range(1, 16):
        res = client1.post("/api/v1/classify", json=payload, headers=headers)
        assert res.status_code == 404, f"Expected 404 on attempt {i}, got {res.status_code}"

    res16 = client1.post("/api/v1/classify", json=payload, headers=headers)
    assert res16.status_code == 429
    assert "rate limit exceeded" in str(res16.json()).lower()

    res_c2 = client2.post("/api/v1/classify", json=payload, headers=headers)
    assert res_c2.status_code == 404


@pytest.mark.asyncio
async def test_timeline_rate_limiting_15_per_minute():
    """Verify /api/v1/timeline POST enforces 15 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.108.1", 50000))
    client2 = TestClient(app, client=("192.168.108.2", 50000))

    payload = {"document_id": str(uuid.uuid4())}
    for i in range(1, 16):
        res = client1.post("/api/v1/timeline", json=payload, headers=headers)
        assert res.status_code == 404, f"Expected 404 on attempt {i}, got {res.status_code}"

    res16 = client1.post("/api/v1/timeline", json=payload, headers=headers)
    assert res16.status_code == 429
    assert "rate limit exceeded" in str(res16.json()).lower()

    res_c2 = client2.post("/api/v1/timeline", json=payload, headers=headers)
    assert res_c2.status_code == 404


@pytest.mark.asyncio
async def test_entities_rate_limiting_20_per_minute():
    """Verify /api/v1/entities POST enforces 20 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.109.1", 50000))
    client2 = TestClient(app, client=("192.168.109.2", 50000))

    payload = {"document_id": str(uuid.uuid4())}
    for i in range(1, 21):
        res = client1.post("/api/v1/entities", json=payload, headers=headers)
        assert res.status_code == 404, f"Expected 404 on attempt {i}, got {res.status_code}"

    res21 = client1.post("/api/v1/entities", json=payload, headers=headers)
    assert res21.status_code == 429
    assert "rate limit exceeded" in str(res21.json()).lower()

    res_c2 = client2.post("/api/v1/entities", json=payload, headers=headers)
    assert res_c2.status_code == 404


@pytest.mark.asyncio
async def test_relationships_rate_limiting_20_per_minute():
    """Verify /api/v1/relationships POST enforces 20 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.110.1", 50000))
    client2 = TestClient(app, client=("192.168.110.2", 50000))

    payload = {"document_id": str(uuid.uuid4())}
    for i in range(1, 21):
        res = client1.post("/api/v1/relationships", json=payload, headers=headers)
        assert res.status_code == 404, f"Expected 404 on attempt {i}, got {res.status_code}"

    res21 = client1.post("/api/v1/relationships", json=payload, headers=headers)
    assert res21.status_code == 429
    assert "rate limit exceeded" in str(res21.json()).lower()

    res_c2 = client2.post("/api/v1/relationships", json=payload, headers=headers)
    assert res_c2.status_code == 404


@pytest.mark.asyncio
async def test_ocr_rate_limiting_20_per_minute():
    """Verify /api/v1/ocr enforces 20 requests per minute per IP."""
    await init_test_db()
    headers = get_auth_headers()
    client1 = TestClient(app, client=("192.168.111.1", 50000))
    client2 = TestClient(app, client=("192.168.111.2", 50000))

    payload = {"document_id": str(uuid.uuid4()), "page_number": 1}
    for i in range(1, 21):
        res = client1.post("/api/v1/ocr", json=payload, headers=headers)
        assert res.status_code == 404, f"Expected 404 on attempt {i}, got {res.status_code}"

    res21 = client1.post("/api/v1/ocr", json=payload, headers=headers)
    assert res21.status_code == 429
    assert "rate limit exceeded" in str(res21.json()).lower()

    res_c2 = client2.post("/api/v1/ocr", json=payload, headers=headers)
    assert res_c2.status_code == 404

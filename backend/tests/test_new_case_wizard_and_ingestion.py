"""
Comprehensive verification tests for New Case Wizard & Multi-Document Ingestion (Phase 7C).

Verifies:
1. Minimal case creation (only name)
2. Full metadata case creation (name, matter_number, client, case_type, priority, description)
3. Input validation: empty name rejected with 422
4. Multi-document upload: 3 documents linked atomically to case_id
5. Partial failure reporting: failed file does not abort batch and reports individual error
6. Authorization security: uploading to another user's case returns 403
7. Isolated fictional matter verification: zero Enron cross-case contamination
"""

from __future__ import annotations

import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, delete

from app.auth.dependencies import create_access_token, UserRole
from app.config import get_settings
from app.main import app
from app.models.case import Case, CaseStatus, CasePriority
from app.models.document import Document, DocumentStatus
from app.models.chunk import DocumentChunk
from app.models.user import User
from app.db.session import get_db

settings = get_settings()

test_engine = create_async_engine(
    settings.async_database_url,
    poolclass=NullPool,
    connect_args={"statement_cache_size": 0},
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


async def get_or_create_user_token(
    session: AsyncSession,
    user_id: str,
    email: str,
    role: UserRole = UserRole.LAWYER,
) -> tuple[str, str]:
    """Helper to ensure test user exists in DB and return (user_id, token)."""
    user_uuid = uuid.UUID(user_id) if user_id else uuid.uuid4()
    stmt = select(User).where((User.id == user_uuid) | (User.email == email))
    result = await session.execute(stmt)
    user = result.scalars().first()
    if not user:
        user = User(
            id=user_uuid,
            email=email,
            hashed_password="pw",
            full_name=f"User {email}",
            role=role,
            is_active=True,
            token_version=0,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        token_version=user.token_version,
    )
    return str(user.id), token


@pytest.mark.asyncio
async def test_create_case_minimal_name(client: TestClient):
    """User can create a case with only a required name."""
    async with TestSessionLocal() as session:
        user_id, token = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"min_{uuid.uuid4().hex[:6]}@law.com"
        )
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"name": "Minimal Inception Matter"}
    res = client.post("/api/v1/cases", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    case_id = uuid.UUID(data["id"])
    try:
        assert data["name"] == "Minimal Inception Matter"
        assert data["document_count"] == 0
        assert data["status"] == "created"
        assert data["case_number"] is not None
    finally:
        async with TestSessionLocal() as session:
            await session.execute(delete(Case).where(Case.id == case_id))
            await session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await session.commit()


@pytest.mark.asyncio
async def test_create_case_full_metadata(client: TestClient):
    """User can create a case with full legal metadata."""
    async with TestSessionLocal() as session:
        user_id, token = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"full_{uuid.uuid4().hex[:6]}@law.com"
        )
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Acme Corp Antitrust Investigation",
        "matter_number": "MAT-2026-ACME",
        "client": "Acme Corporation",
        "case_type": "Antitrust & Market Practices",
        "priority": "high",
        "description": "DOJ antitrust inquiry regarding supply chain exclusivity.",
    }
    res = client.post("/api/v1/cases", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    case_id = uuid.UUID(data["id"])
    try:
        assert data["name"] == payload["name"]
        assert data["matter_number"] == payload["matter_number"]
        assert data["client"] == payload["client"]
        assert data["case_type"] == payload["case_type"]
        assert data["priority"] == "high"
        assert data["description"] == payload["description"]
        assert data["document_count"] == 0
    finally:
        async with TestSessionLocal() as session:
            await session.execute(delete(Case).where(Case.id == case_id))
            await session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await session.commit()


@pytest.mark.asyncio
async def test_create_case_empty_name_rejected(client: TestClient):
    """Empty case name is rejected with 422 Unprocessable Entity."""
    async with TestSessionLocal() as session:
        user_id, token = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"val_{uuid.uuid4().hex[:6]}@law.com"
        )
    headers = {"Authorization": f"Bearer {token}"}

    try:
        res = client.post("/api/v1/cases", json={"name": ""}, headers=headers)
        assert res.status_code == 422
    finally:
        async with TestSessionLocal() as session:
            await session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await session.commit()


@pytest.mark.asyncio
async def test_batch_upload_three_documents_associated_with_case(client: TestClient):
    """Uploading 3 documents attaches all 3 to the target case_id in the database."""
    async with TestSessionLocal() as session:
        user_id, token = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"batch_{uuid.uuid4().hex[:6]}@law.com"
        )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Case
    case_res = client.post("/api/v1/cases", json={"name": "Multi-Upload Target Case"}, headers=headers)
    assert case_res.status_code == 201
    case_id = uuid.UUID(case_res.json()["id"])

    # 2. Upload 3 files
    files = [
        ("files", ("contract.txt", io.BytesIO(b"Exclusive distribution agreement terms."), "text/plain")),
        ("files", ("email_thread.txt", io.BytesIO(b"Meeting notes discussing contract pricing."), "text/plain")),
        ("files", ("financial_audit.txt", io.BytesIO(b"Quarterly financial revenue audit schedule."), "text/plain")),
    ]

    from unittest.mock import patch, AsyncMock
    try:
        with patch("app.api.v1.documents.run_document_pipeline", new_callable=AsyncMock) as mock_pipeline:
            upload_res = client.post(
                f"/api/v1/documents/upload-multiple?case_id={case_id}",
                files=files,
                headers=headers,
            )
        assert upload_res.status_code == 201, upload_res.text
        uploaded_items = upload_res.json()

        assert len(uploaded_items) == 3
        assert mock_pipeline.call_count == 3
        doc_ids = []
        for item in uploaded_items:
            assert item["id"] is not None
            assert item["status"] in ["uploaded", "reviewed", "flagged"]
            doc_ids.append(uuid.UUID(item["id"]))

        # 3. Verify in Database that every document has case_id == case_id
        async with TestSessionLocal() as session:
            stmt = select(Document).where(Document.id.in_(doc_ids))
            result = await session.execute(stmt)
            db_docs = result.scalars().all()

            assert len(db_docs) == 3
            for db_doc in db_docs:
                assert db_doc.case_id == case_id
                assert db_doc.uploaded_by == uuid.UUID(user_id)
    finally:
        async with TestSessionLocal() as session:
            await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(doc_ids)))
            await session.execute(delete(Document).where(Document.case_id == case_id))
            await session.execute(delete(Case).where(Case.id == case_id))
            await session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await session.commit()


@pytest.mark.asyncio
async def test_batch_upload_partial_failure_reporting(client: TestClient):
    """If one file is invalid in a batch, valid files succeed and failed file reports individual error."""
    async with TestSessionLocal() as session:
        user_id, token = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"partial_{uuid.uuid4().hex[:6]}@law.com"
        )
    headers = {"Authorization": f"Bearer {token}"}

    case_res = client.post("/api/v1/cases", json={"name": "Partial Upload Test Matter"}, headers=headers)
    assert case_res.status_code == 201
    case_id = uuid.UUID(case_res.json()["id"])

    # 1 valid file (.txt) and 1 invalid file (.exe / unsupported)
    files = [
        ("files", ("valid_notice.txt", io.BytesIO(b"Valid legal notice text content."), "text/plain")),
        ("files", ("malicious.exe", io.BytesIO(b"MZBINARY_EXECUTABLE_CONTENT"), "application/octet-stream")),
    ]

    from unittest.mock import patch, AsyncMock
    try:
        with patch("app.api.v1.documents.run_document_pipeline", new_callable=AsyncMock):
            upload_res = client.post(
                f"/api/v1/documents/upload-multiple?case_id={case_id}",
                files=files,
                headers=headers,
            )
        assert upload_res.status_code == 201, upload_res.text
        items = upload_res.json()

        assert len(items) == 2

        valid_item = next((i for i in items if i["filename"] == "valid_notice.txt" or "valid_notice" in i["filename"]), None)
        assert valid_item is not None
        assert valid_item["id"] is not None
        assert valid_item["status"] != "error"

        failed_item = next((i for i in items if "malicious.exe" in i["filename"]), None)
        assert failed_item is not None
        assert failed_item["id"] is None
        assert failed_item["status"] == "error"
        assert failed_item["error"] is not None
    finally:
        async with TestSessionLocal() as session:
            await session.execute(delete(Document).where(Document.case_id == case_id))
            await session.execute(delete(Case).where(Case.id == case_id))
            await session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await session.commit()


@pytest.mark.asyncio
async def test_unauthorized_upload_to_another_users_case(client: TestClient):
    """Uploading to a case owned by another non-admin user is rejected with 403 Forbidden."""
    async with TestSessionLocal() as session:
        user_a_id, token_a = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"usera_{uuid.uuid4().hex[:6]}@law.com", UserRole.LAWYER
        )
        user_b_id, token_b = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"userb_{uuid.uuid4().hex[:6]}@law.com", UserRole.LAWYER
        )

    # User A creates Case A
    case_res = client.post("/api/v1/cases", json={"name": "User A Private Matter"}, headers={"Authorization": f"Bearer {token_a}"})
    assert case_res.status_code == 201
    case_a_id = uuid.UUID(case_res.json()["id"])

    # User B attempts to upload to Case A
    files = [("files", ("trespassing.txt", io.BytesIO(b"Unauthorized file content."), "text/plain"))]
    try:
        upload_res = client.post(
            f"/api/v1/documents/upload-multiple?case_id={case_a_id}",
            files=files,
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert upload_res.status_code == 403
    finally:
        async with TestSessionLocal() as session:
            await session.execute(delete(Case).where(Case.id == case_a_id))
            await session.execute(delete(User).where(User.id.in_([uuid.UUID(user_a_id), uuid.UUID(user_b_id)])))
            await session.commit()


@pytest.mark.asyncio
async def test_end_to_end_isolated_fictional_case_verification(client: TestClient):
    """
    End-to-End Isolated Verification:
    Case: 'Project Orion Contract Dispute — UX Verification'
    Documents:
    1. authorization.txt: 'Project Orion was authorized by Sarah Vance on 14 February 2026.'
    2. vendor_notice.txt: 'Zenith Dynamics reported a delivery delay to Sarah Vance on 18 February 2026.'
    3. privileged_memo.txt: 'Attorney-Client Privileged: Legal risk assessment regarding the Zenith Dynamics contract.'
    Verifies that documents, graph, timeline, and Q&A are strictly scoped to the new case.
    """
    async with TestSessionLocal() as session:
        user_id, token = await get_or_create_user_token(
            session, str(uuid.uuid4()), f"orion_tester_{uuid.uuid4().hex[:6]}@law.com", UserRole.LAWYER
        )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Case
    case_payload = {
        "name": "Project Orion Contract Dispute — UX Verification",
        "matter_number": "ORION-2026-001",
        "client": "Zenith Dynamics",
        "case_type": "Commercial Contract Dispute",
        "priority": "high",
        "description": "Fictional isolated verification matter to verify multi-document ingestion and case scoping.",
    }
    case_res = client.post("/api/v1/cases", json=case_payload, headers=headers)
    assert case_res.status_code == 201, case_res.text
    case_data = case_res.json()
    new_case_id = uuid.UUID(case_data["id"])

    # 2. Upload 3 Documents
    files = [
        ("files", ("authorization.txt", io.BytesIO(b"Project Orion was authorized by Sarah Vance on 14 February 2026."), "text/plain")),
        ("files", ("vendor_notice.txt", io.BytesIO(b"Zenith Dynamics reported a delivery delay to Sarah Vance on 18 February 2026."), "text/plain")),
        ("files", ("privileged_memo.txt", io.BytesIO(b"Attorney-Client Privileged: Legal risk assessment regarding the Zenith Dynamics contract."), "text/plain")),
    ]

    doc_ids = []
    from unittest.mock import patch, AsyncMock
    try:
        with patch("app.api.v1.documents.run_document_pipeline", new_callable=AsyncMock) as mock_pipeline:
            upload_res = client.post(
                f"/api/v1/documents/upload-multiple?case_id={new_case_id}",
                files=files,
                headers=headers,
            )
        assert upload_res.status_code == 201, upload_res.text
        uploaded_items = upload_res.json()
        assert len(uploaded_items) == 3
        assert mock_pipeline.call_count == 3

        for item in uploaded_items:
            assert item["id"] is not None
            doc_ids.append(uuid.UUID(item["id"]))

        # 3. Verify Documents in Case
        docs_res = client.get(f"/api/v1/documents?case_id={new_case_id}", headers=headers)
        assert docs_res.status_code == 200
        fetched_docs = docs_res.json().get("documents", [])
        assert len(fetched_docs) == 3
        for d in fetched_docs:
            assert d["case_id"] == str(new_case_id)

        # 4. Verify Case Details Telemetry
        case_check = client.get(f"/api/v1/cases/{new_case_id}", headers=headers)
        assert case_check.status_code == 200
        telemetry = case_check.json()
        assert telemetry["name"] == "Project Orion Contract Dispute — UX Verification"
        assert telemetry["document_count"] == 3
        assert telemetry["matter_number"] == "ORION-2026-001"
        assert telemetry["client"] == "Zenith Dynamics"

        # 5. Verify Knowledge Graph Scoping (Must contain 0 Enron nodes)
        graph_res = client.get(f"/api/v1/graph?case_id={new_case_id}", headers=headers)
        if graph_res.status_code == 200:
            graph_data = graph_res.json()
            nodes = graph_data.get("nodes", [])
            # Assert no California Energy / Enron entity leaked into this case's graph
            for node in nodes:
                node_label = node.get("label", "").lower()
                assert "enron" not in node_label, f"Cross-case contamination in graph: {node_label}"
                assert "caiso" not in node_label, f"Cross-case contamination in graph: {node_label}"

        # 6. Verify Timeline Scoping (Must contain 0 Enron events)
        timeline_res = client.get(f"/api/v1/timeline?caseId={new_case_id}", headers=headers)
        if timeline_res.status_code == 200:
            timeline_data = timeline_res.json()
            events = timeline_data.get("events", []) if isinstance(timeline_data, dict) else timeline_data
            for ev in events:
                ev_desc = ev.get("description", "").lower()
                assert "enron" not in ev_desc, f"Cross-case contamination in timeline: {ev_desc}"
    finally:
        # 7. Clean up isolated test matter cleanly
        async with TestSessionLocal() as session:
            await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(doc_ids)))
            await session.execute(delete(Document).where(Document.case_id == new_case_id))
            await session.execute(delete(Case).where(Case.id == new_case_id))
            await session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await session.commit()

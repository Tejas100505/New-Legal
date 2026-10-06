"""
Comprehensive tests for Case Metadata and Real Case Telemetry (Phase 7B).

Verifies:
1. Empty case telemetry (all 0s, valid last_activity)
2. Multiple documents with exact state matching
3. Mixed document states (reviewed, flagged, processing, privileged, high risk)
4. Cross-case isolation (Case A vs Case B)
5. Non-admin ownership scoping and privacy (403 on other user's case)
6. Admin visibility across all cases
7. Backward compatibility and CRUD for matter_number, client, and case_type
8. Null / missing doc_metadata resilience
9. Primary protected case read-only telemetry comparison
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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

PRIMARY_CASE_ID = uuid.UUID("8d8389d4-2534-452d-85b4-65efe5b8e1c3")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


async def get_or_create_user_token(
    session: AsyncSession,
    user_id: str,
    email: str,
    role: UserRole = UserRole.LAWYER,
) -> tuple[str, str]:
    """Helper to ensure a test user exists in the database and return (user_id, jwt_token)."""
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
async def test_empty_case_telemetry(client: TestClient):
    """An empty case returns document_count=0 and all telemetry counts as 0."""
    case_id = uuid.uuid4()

    async with TestSessionLocal() as db_session:
        user_id, token = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"empty_test_{uuid.uuid4().hex[:6]}@law.com"
        )
        headers = {"Authorization": f"Bearer {token}"}

        case = Case(
            id=case_id,
            name="Empty Test Case",
            case_number="CASE-EMPTY-01",
            matter_number="MAT-EMPTY-01",
            client="Acme Corp",
            case_type="Litigation",
            status=CaseStatus.CREATED,
            priority=CasePriority.MEDIUM,
            created_by=user_id,
        )
        db_session.add(case)
        await db_session.commit()

    try:
        res = client.get(f"/api/v1/cases/{case_id}", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["id"] == str(case_id)
        assert data["name"] == "Empty Test Case"
        assert data["case_number"] == "CASE-EMPTY-01"
        assert data["matter_number"] == "MAT-EMPTY-01"
        assert data["client"] == "Acme Corp"
        assert data["case_type"] == "Litigation"
        assert data["document_count"] == 0
        assert data["reviewed_count"] == 0
        assert data["flagged_count"] == 0
        assert data["privileged_count"] == 0
        assert data["high_risk_count"] == 0
        assert data["processing_count"] == 0
        assert data["last_activity"] is not None
    finally:
        async with TestSessionLocal() as db_session:
            await db_session.execute(delete(Case).where(Case.id == case_id))
            await db_session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await db_session.commit()


@pytest.mark.asyncio
async def test_mixed_document_states_telemetry(client: TestClient):
    """Case with 5 documents in mixed states accurately reports all telemetry metrics."""
    case_id = uuid.uuid4()

    async with TestSessionLocal() as db_session:
        user_id, token = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"mixed_test_{uuid.uuid4().hex[:6]}@law.com"
        )
        headers = {"Authorization": f"Bearer {token}"}

        case = Case(
            id=case_id,
            name="Telemetry Verification Case",
            case_number="CASE-TELEM-01",
            matter_number="MAT-TELEM-01",
            client="Initech Global",
            case_type="Antitrust",
            status=CaseStatus.IN_PROGRESS,
            created_by=user_id,
        )
        db_session.add(case)
        await db_session.flush()

        # 1. Reviewed, Non-privileged, Low risk
        d1 = Document(
            id=uuid.uuid4(),
            case_id=case_id,
            filename="doc1.pdf",
            original_filename="doc1.pdf",
            content_type="application/pdf",
            file_size=1024,
            storage_path="/docs/1.pdf",
            status=DocumentStatus.REVIEWED,
            doc_metadata={
                "review_status": "reviewed",
                "privilege": {"is_privileged": False},
                "risk": {"overall_risk": "LOW"},
            },
        )
        # 2. Reviewed, Privileged, Medium risk
        d2 = Document(
            id=uuid.uuid4(),
            case_id=case_id,
            filename="doc2.pdf",
            original_filename="doc2.pdf",
            content_type="application/pdf",
            file_size=2048,
            storage_path="/docs/2.pdf",
            status=DocumentStatus.REVIEWED,
            doc_metadata={
                "review_status": "reviewed",
                "privilege": {"is_privileged": True},
                "risk": {"overall_risk": "MEDIUM"},
            },
        )
        # 3. Flagged, High risk, Non-privileged
        d3 = Document(
            id=uuid.uuid4(),
            case_id=case_id,
            filename="doc3.pdf",
            original_filename="doc3.pdf",
            content_type="application/pdf",
            file_size=3072,
            storage_path="/docs/3.pdf",
            status=DocumentStatus.FLAGGED,
            doc_metadata={
                "review_status": "flagged",
                "privilege": {"is_privileged": False},
                "risk": {"overall_risk": "HIGH"},
            },
        )
        # 4. Processing (Chunking)
        d4 = Document(
            id=uuid.uuid4(),
            case_id=case_id,
            filename="doc4.pdf",
            original_filename="doc4.pdf",
            content_type="application/pdf",
            file_size=4096,
            storage_path="/docs/4.pdf",
            status=DocumentStatus.CHUNKING,
            doc_metadata=None,
        )
        # 5. Processing (Uploaded)
        d5 = Document(
            id=uuid.uuid4(),
            case_id=case_id,
            filename="doc5.pdf",
            original_filename="doc5.pdf",
            content_type="application/pdf",
            file_size=5120,
            storage_path="/docs/5.pdf",
            status=DocumentStatus.UPLOADED,
            doc_metadata={},
        )
        db_session.add_all([d1, d2, d3, d4, d5])
        await db_session.commit()

    try:
        res = client.get(f"/api/v1/cases/{case_id}", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["document_count"] == 5
        assert data["reviewed_count"] == 2
        assert data["flagged_count"] == 1
        assert data["privileged_count"] == 1
        assert data["high_risk_count"] == 1
        assert data["processing_count"] == 2
        assert data["last_activity"] is not None

        # Verify listing returns the same aggregated telemetry
        list_res = client.get("/api/v1/cases", headers=headers)
        assert list_res.status_code == 200
        cases_list = list_res.json()["cases"]
        target = next((c for c in cases_list if c["id"] == str(case_id)), None)
        assert target is not None
        assert target["document_count"] == 5
        assert target["reviewed_count"] == 2
        assert target["flagged_count"] == 1
        assert target["privileged_count"] == 1
        assert target["high_risk_count"] == 1
        assert target["processing_count"] == 2
    finally:
        async with TestSessionLocal() as db_session:
            await db_session.execute(delete(Document).where(Document.case_id == case_id))
            await db_session.execute(delete(Case).where(Case.id == case_id))
            await db_session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await db_session.commit()


@pytest.mark.asyncio
async def test_case_isolation_telemetry(client: TestClient):
    """Telemetry for Case A is completely isolated from documents in Case B."""
    case_a_id = uuid.uuid4()
    case_b_id = uuid.uuid4()

    async with TestSessionLocal() as db_session:
        user_id, token = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"iso_test_{uuid.uuid4().hex[:6]}@law.com"
        )
        headers = {"Authorization": f"Bearer {token}"}

        case_a = Case(id=case_a_id, name="Case A", created_by=user_id)
        case_b = Case(id=case_b_id, name="Case B", created_by=user_id)
        db_session.add_all([case_a, case_b])
        await db_session.flush()

        # Case A has 1 document: Reviewed
        doc_a = Document(
            id=uuid.uuid4(),
            case_id=case_a_id,
            filename="a.txt",
            original_filename="a.txt",
            content_type="text/plain",
            file_size=100,
            storage_path="/a.txt",
            status=DocumentStatus.REVIEWED,
            doc_metadata={"review_status": "reviewed"},
        )
        # Case B has 2 documents: 2 flagged, 1 privileged, 1 high-risk
        doc_b1 = Document(
            id=uuid.uuid4(),
            case_id=case_b_id,
            filename="b1.txt",
            original_filename="b1.txt",
            content_type="text/plain",
            file_size=100,
            storage_path="/b1.txt",
            status=DocumentStatus.FLAGGED,
            doc_metadata={"review_status": "flagged", "privilege": {"is_privileged": True}},
        )
        doc_b2 = Document(
            id=uuid.uuid4(),
            case_id=case_b_id,
            filename="b2.txt",
            original_filename="b2.txt",
            content_type="text/plain",
            file_size=100,
            storage_path="/b2.txt",
            status=DocumentStatus.FLAGGED,
            doc_metadata={"review_status": "flagged", "risk": {"overall_risk": "HIGH"}},
        )
        db_session.add_all([doc_a, doc_b1, doc_b2])
        await db_session.commit()

    try:
        res_a = client.get(f"/api/v1/cases/{case_a_id}", headers=headers)
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["document_count"] == 1
        assert data_a["reviewed_count"] == 1
        assert data_a["flagged_count"] == 0
        assert data_a["privileged_count"] == 0
        assert data_a["high_risk_count"] == 0

        res_b = client.get(f"/api/v1/cases/{case_b_id}", headers=headers)
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["document_count"] == 2
        assert data_b["reviewed_count"] == 0
        assert data_b["flagged_count"] == 2
        assert data_b["privileged_count"] == 1
        assert data_b["high_risk_count"] == 1
    finally:
        async with TestSessionLocal() as db_session:
            await db_session.execute(delete(Document).where(Document.case_id.in_([case_a_id, case_b_id])))
            await db_session.execute(delete(Case).where(Case.id.in_([case_a_id, case_b_id])))
            await db_session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await db_session.commit()


@pytest.mark.asyncio
async def test_case_ownership_and_admin_visibility(client: TestClient):
    """Non-admin user cannot see another user's case telemetry; Admin sees all cases."""
    case_id = uuid.uuid4()

    async with TestSessionLocal() as db_session:
        owner_id, token_owner = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"owner_{uuid.uuid4().hex[:6]}@law.com", UserRole.LAWYER
        )
        stranger_id, token_stranger = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"stranger_{uuid.uuid4().hex[:6]}@law.com", UserRole.LAWYER
        )
        admin_id, token_admin = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"admin_{uuid.uuid4().hex[:6]}@law.com", UserRole.ADMIN
        )

        case = Case(id=case_id, name="Confidential Case", created_by=owner_id)
        db_session.add(case)
        await db_session.commit()

    try:
        # Stranger gets 403 on direct get
        res_stranger = client.get(f"/api/v1/cases/{case_id}", headers={"Authorization": f"Bearer {token_stranger}"})
        assert res_stranger.status_code == 403

        # Stranger list does not include the case
        res_stranger_list = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_stranger}"})
        assert res_stranger_list.status_code == 200
        stranger_ids = [c["id"] for c in res_stranger_list.json()["cases"]]
        assert str(case_id) not in stranger_ids

        # Owner gets 200
        res_owner = client.get(f"/api/v1/cases/{case_id}", headers={"Authorization": f"Bearer {token_owner}"})
        assert res_owner.status_code == 200

        # Admin gets 200
        res_admin = client.get(f"/api/v1/cases/{case_id}", headers={"Authorization": f"Bearer {token_admin}"})
        assert res_admin.status_code == 200
    finally:
        async with TestSessionLocal() as db_session:
            await db_session.execute(delete(Case).where(Case.id == case_id))
            await db_session.execute(delete(User).where(User.id.in_([uuid.UUID(owner_id), uuid.UUID(stranger_id), uuid.UUID(admin_id)])))
            await db_session.commit()


@pytest.mark.asyncio
async def test_case_metadata_crud(client: TestClient):
    """Case creation and update persist matter_number, client, and case_type properly."""
    async with TestSessionLocal() as db_session:
        user_id, token = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"crud_test_{uuid.uuid4().hex[:6]}@law.com"
        )
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "name": "Securities Investigation Matter",
        "case_number": "SEC-2026-009",
        "matter_number": "MAT-9988-SEC",
        "client": "Sterling Cooper Financial",
        "case_type": "Regulatory Defense",
        "description": "SEC compliance inquiry regarding energy derivatives.",
        "priority": "high",
    }
    create_res = client.post("/api/v1/cases", json=create_payload, headers=headers)
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    case_id = uuid.UUID(created["id"])

    try:
        assert created["name"] == "Securities Investigation Matter"
        assert created["case_number"] == "SEC-2026-009"
        assert created["matter_number"] == "MAT-9988-SEC"
        assert created["client"] == "Sterling Cooper Financial"
        assert created["case_type"] == "Regulatory Defense"
        assert created["document_count"] == 0

        # Update metadata
        update_payload = {
            "client": "Sterling Cooper Draper Pryce",
            "case_type": "Corporate Governance",
        }
        update_res = client.put(f"/api/v1/cases/{case_id}", json=update_payload, headers=headers)
        assert update_res.status_code == 200, update_res.text
        updated = update_res.json()
        assert updated["client"] == "Sterling Cooper Draper Pryce"
        assert updated["case_type"] == "Corporate Governance"
        assert updated["matter_number"] == "MAT-9988-SEC"
    finally:
        async with TestSessionLocal() as db_session:
            await db_session.execute(delete(Case).where(Case.id == case_id))
            await db_session.execute(delete(User).where(User.id == uuid.UUID(user_id)))
            await db_session.commit()


@pytest.mark.asyncio
async def test_primary_case_read_only_telemetry(client: TestClient):
    """The protected 423-document primary case returns its known verified legal telemetry."""
    async with TestSessionLocal() as db_session:
        admin_id, admin_token = await get_or_create_user_token(
            db_session, str(uuid.uuid4()), f"prim_admin_{uuid.uuid4().hex[:6]}@law.com", UserRole.ADMIN
        )
    headers = {"Authorization": f"Bearer {admin_token}"}

    try:
        res = client.get(f"/api/v1/cases/{PRIMARY_CASE_ID}", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()

        # Verify against known primary case metrics
        assert data["id"] == str(PRIMARY_CASE_ID)
        assert data["document_count"] == 423
        assert data["reviewed_count"] == 420
        assert data["flagged_count"] == 3
        assert data["privileged_count"] == 33
        assert data["high_risk_count"] == 7
        assert data["processing_count"] == 0
        assert data["last_activity"] is not None
    finally:
        async with TestSessionLocal() as db_session:
            await db_session.execute(delete(User).where(User.id == uuid.UUID(admin_id)))
            await db_session.commit()

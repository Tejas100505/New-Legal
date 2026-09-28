"""
Unit & Integration Tests for Case-Scoped & Document-Scoped Pipeline Status.

Validates:
1. Owner can retrieve real pipeline status for own document in own case.
2. Stranger cannot retrieve pipeline status for a document in another tenant's case (403 Forbidden).
3. Admin override allows access across tenants.
4. Nonexistent case returns 403 to unauthorized users (403-before-404 existence privacy).
5. Nonexistent document in owned case returns 404.
6. Pipeline status response accurately derives stages and progress from real Document status and status_history rows (no fake ETAs, estimated_completion_at is None).
7. Quota pause status is honestly reflected (isQuotaPaused=True, pausedStage, pausedReason).
8. Legacy GET /api/v1/agents/pipeline endpoint eliminates hardcoded 'case_001' and supports caseId and documentId query parameters.
9. Direct GET /api/v1/documents/{document_id}/pipeline-status endpoint works identically.
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_pipeline_status.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
PipelineSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

import app.db.session as db_session_module
_orig_session_local = db_session_module.AsyncSessionLocal

@pytest.fixture(scope="module", autouse=True)
def manage_session_local():
    db_session_module.AsyncSessionLocal = PipelineSessionLocal
    yield
    db_session_module.AsyncSessionLocal = _orig_session_local

from app.main import app
from app.db.base import Base
from app.models.case import Case
from app.models.document import Document, DocumentStatus
from app.models.status_history import StatusHistory
from app.models.user import User
from app.auth.dependencies import create_access_token, UserRole
from app.services.status_history_service import record_status_transition

client = TestClient(app)


async def init_test_db():
    db_session_module.AsyncSessionLocal = PipelineSessionLocal
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def seed_user(user_id: uuid.UUID, email: str, role: UserRole = UserRole.LAWYER) -> str:
    async with PipelineSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            hashed_password="hashed_pw_test",
            full_name=f"User {email}",
            role=role,
            is_active=True,
            token_version=0,
        )
        session.add(user)
        await session.commit()
    return create_access_token(user_id=str(user_id), email=email, role=role, token_version=0)


from app.models.case import Case, CaseStatus, CasePriority


async def seed_case(case_id: uuid.UUID, owner_id: uuid.UUID, title: str = "Test Matter") -> Case:
    async with PipelineSessionLocal() as session:
        case = Case(
            id=case_id,
            name=title,
            description="Matter for testing pipeline status",
            status=CaseStatus.CREATED,
            priority=CasePriority.MEDIUM,
            created_by=str(owner_id),
        )
        session.add(case)
        await session.commit()
        return case


async def seed_document(
    doc_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    case_id: uuid.UUID | None = None,
    filename: str = "doc.pdf",
    status: DocumentStatus = DocumentStatus.UPLOADED,
    doc_metadata: dict | None = None,
) -> Document:
    async with PipelineSessionLocal() as session:
        doc = Document(
            id=doc_id,
            uploaded_by=uploaded_by,
            case_id=case_id,
            filename=filename,
            original_filename=filename,
            content_type="application/pdf",
            file_size=2048,
            storage_path=f"/test/{filename}",
            status=status,
            doc_metadata=doc_metadata or {},
        )
        session.add(doc)
        await session.commit()
        return doc


@pytest.mark.asyncio
async def test_owner_can_get_pipeline_status_with_matching_history():
    """Verify owner can retrieve pipeline status and that stages match status_history rows."""
    await init_test_db()
    owner_id = uuid.uuid4()
    owner_token = await seed_user(owner_id, "attorney@law.com")
    case_id = uuid.uuid4()
    await seed_case(case_id, owner_id)
    doc_id = uuid.uuid4()
    await seed_document(doc_id, owner_id, case_id=case_id, status=DocumentStatus.UPLOADED)

    # Transition document through OCR and ANALYZING
    async with PipelineSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        await record_status_transition(session, doc, DocumentStatus.OCR_PROCESSING, reason="ocr_pipeline_start")
        await record_status_transition(session, doc, DocumentStatus.ANALYZING, reason="legal_analysis_start")
        await session.commit()

    # Query via documents endpoint
    res = client.get(
        f"/api/v1/documents/{doc_id}/pipeline-status",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["caseId"] == str(case_id)
    assert data["documentId"] == str(doc_id)
    assert data["status"] == "analyzing"
    assert data["currentStage"] == "legal_review"
    assert data["isQuotaPaused"] is False
    assert data["estimatedCompletionAt"] is None  # honest: no fabricated ETA
    assert len(data["history"]) == 2
    assert data["history"][0]["new_status"] == "ocr_processing"
    assert data["history"][1]["new_status"] == "analyzing"
    assert data["lastReason"] == "legal_analysis_start"

    # Query via agents endpoint with query params
    res_agents = client.get(
        f"/api/v1/agents/pipeline?caseId={case_id}&documentId={doc_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_agents.status_code == 200
    data_agents = res_agents.json()
    assert data_agents["caseId"] == str(case_id)
    assert data_agents["documentId"] == str(doc_id)
    assert data_agents["caseId"] != "case_001"  # Not hardcoded!


@pytest.mark.asyncio
async def test_cross_tenant_isolation_forbidden():
    """Verify unauthorized user cannot access another user's document pipeline status (403)."""
    await init_test_db()
    owner_id = uuid.uuid4()
    stranger_id = uuid.uuid4()
    await seed_user(owner_id, "firmA@law.com")
    stranger_token = await seed_user(stranger_id, "firmB@law.com")

    case_id = uuid.uuid4()
    await seed_case(case_id, owner_id)
    doc_id = uuid.uuid4()
    await seed_document(doc_id, owner_id, case_id=case_id)

    # 1. Documents endpoint -> 403 Forbidden
    res = client.get(
        f"/api/v1/documents/{doc_id}/pipeline-status",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert res.status_code == 403

    # 2. Agents endpoint with stranger's token -> 403 Forbidden
    res_agents = client.get(
        f"/api/v1/agents/pipeline?caseId={case_id}&documentId={doc_id}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert res_agents.status_code == 403


@pytest.mark.asyncio
async def test_admin_override_access():
    """Verify admin role can access any document's pipeline status across tenants."""
    await init_test_db()
    owner_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    await seed_user(owner_id, "lawyer@law.com", UserRole.LAWYER)
    admin_token = await seed_user(admin_id, "admin@law.com", UserRole.ADMIN)

    case_id = uuid.uuid4()
    await seed_case(case_id, owner_id)
    doc_id = uuid.uuid4()
    await seed_document(doc_id, owner_id, case_id=case_id)

    res = client.get(
        f"/api/v1/documents/{doc_id}/pipeline-status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["documentId"] == str(doc_id)


@pytest.mark.asyncio
async def test_existence_privacy_403_before_404():
    """Verify nonexistent or unowned case returns 403 to unauthorized users (Batch 3 pattern)."""
    await init_test_db()
    stranger_id = uuid.uuid4()
    stranger_token = await seed_user(stranger_id, "stranger@law.com")

    nonexistent_case = uuid.uuid4()
    nonexistent_doc = uuid.uuid4()

    # Querying a case that doesn't exist or isn't owned returns 403 for non-admin
    res = client.get(
        f"/api/v1/agents/pipeline?caseId={nonexistent_case}&documentId={nonexistent_doc}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_nonexistent_document_in_owned_case_returns_404():
    """Verify nonexistent document in user's own case returns 404 Not Found."""
    await init_test_db()
    owner_id = uuid.uuid4()
    owner_token = await seed_user(owner_id, "owner@law.com")

    case_id = uuid.uuid4()
    await seed_case(case_id, owner_id)
    nonexistent_doc = uuid.uuid4()

    res = client.get(
        f"/api/v1/agents/pipeline?caseId={case_id}&documentId={nonexistent_doc}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_quota_paused_representation():
    """Verify quota paused document honestly reports isQuotaPaused and paused stage."""
    await init_test_db()
    owner_id = uuid.uuid4()
    owner_token = await seed_user(owner_id, "quota_owner@law.com")

    case_id = uuid.uuid4()
    await seed_case(case_id, owner_id)
    doc_id = uuid.uuid4()
    metadata = {
        "paused_stage": "legal_review",
        "paused_reason": "Gemini API 429 ResourceExhausted: rate limit exceeded",
    }
    await seed_document(
        doc_id,
        owner_id,
        case_id=case_id,
        status=DocumentStatus.QUOTA_PAUSED,
        doc_metadata=metadata,
    )

    async with PipelineSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        await record_status_transition(
            session,
            doc,
            DocumentStatus.QUOTA_PAUSED,
            reason="Gemini API 429 ResourceExhausted",
        )
        await session.commit()

    res = client.get(
        f"/api/v1/documents/{doc_id}/pipeline-status",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["isQuotaPaused"] is True
    assert data["pausedStage"] == "legal_review"
    assert "429" in data["pausedReason"]
    assert data["currentStage"] == "legal_review"
    # Find paused stage
    paused_stage = next(s for s in data["stages"] if s["id"] == "legal_review")
    assert paused_stage["status"] == "paused"


@pytest.mark.asyncio
async def test_agents_pipeline_unparameterized_eliminates_case_001():
    """Verify GET /api/v1/agents/pipeline without params returns 200 and no hardcoded case_001."""
    await init_test_db()
    user_id = uuid.uuid4()
    user_token = await seed_user(user_id, "clean_user@law.com")

    res = client.get(
        "/api/v1/agents/pipeline",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["caseId"] is None  # Hardcoded 'case_001' is gone!
    assert "stages" in data
    assert len(data["stages"]) == 10
    assert data["estimatedCompletionAt"] is None

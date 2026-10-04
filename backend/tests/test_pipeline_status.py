"""
Unit & Integration Tests for Case-Scoped & Document-Scoped Pipeline Status.

Validates:
1. Owner can retrieve real pipeline status for own document in own case.
2. Honest evidence attribution:
   - When history rows exist, stages derive status and timestamps from status_history (evidence="status_history").
   - When history rows do NOT exist, terminal documents have document-level stages marked "completed" with evidence="current_status_inference", and case-level stages marked "unknown" with evidence="none".
   - Invariant: Never return "completed" with evidence "none".
3. historyAvailable flag (True when status_history rows exist, False when none).
4. stagesWithEvidence and totalStages counts.
5. overallProgress returns None (tolerated by frontend, no fabricated progress).
6. completedAt and durationMs only populated from real timestamps, else None. estimatedCompletionAt is None.
7. Stranger cannot retrieve pipeline status for a document in another tenant's case (403 Forbidden).
8. Admin override allows access across tenants.
9. Nonexistent case returns 403 to unauthorized users (403-before-404 existence privacy).
10. Nonexistent document in owned case returns 404.
11. Quota pause status is honestly reflected (isQuotaPaused=True, pausedStage, pausedReason).
12. Legacy GET /api/v1/agents/pipeline endpoint eliminates hardcoded 'case_001' and supports caseId and documentId query parameters.
13. Tracked fixtures with safety validation and strict cleanup.
"""

from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.dependencies import create_access_token, UserRole
from app.config import get_settings
from app.main import app
from app.models.case import Case, CaseStatus, CasePriority
from app.models.document import Document, DocumentStatus
from app.models.status_history import StatusHistory
from app.models.user import User
from app.db.session import get_db
from app.services.status_history_service import record_status_transition

settings = get_settings()

test_engine = create_async_engine(
    settings.async_database_url,
    poolclass=NullPool,
    connect_args={"statement_cache_size": 0},
)
TestSession = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


PRIMARY_CASE_ID = uuid.UUID("8d8389d4-2534-452d-85b4-65efe5b8e1c3")
PROTECTED_CASE_IDS = {
    uuid.UUID("685b2574-bda0-43aa-b1ec-b75ff3faee3e"),
    uuid.UUID("83969a81-07ab-40f6-8e6a-3bdb3a1377de"),
}
ALL_PROTECTED_CASE_IDS = PROTECTED_CASE_IDS | {PRIMARY_CASE_ID}
RESTORED_DOC_ID = uuid.UUID("8539d172-7a46-4eec-95ea-af627211766e")

_tracked_case_ids: set[uuid.UUID] = set()
_tracked_doc_ids: set[uuid.UUID] = set()
_tracked_user_ids: set[uuid.UUID] = set()

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def override_db():
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _async_cleanup():
    overlap = _tracked_case_ids.intersection(ALL_PROTECTED_CASE_IDS)
    if overlap:
        raise ValueError(f"SAFETY VIOLATION: Protected case ID in tracked cases: {overlap}")
    if RESTORED_DOC_ID in _tracked_doc_ids:
        raise ValueError(f"SAFETY VIOLATION: Restored doc ID in tracked docs: {RESTORED_DOC_ID}")

    async with TestSession() as session:
        if _tracked_doc_ids:
            # Delete status history records for tracked docs
            await session.execute(
                delete(StatusHistory).where(StatusHistory.document_id.in_(list(_tracked_doc_ids)))
            )
            await session.execute(
                delete(Document).where(Document.id.in_(list(_tracked_doc_ids)))
            )
        if _tracked_case_ids:
            await session.execute(
                delete(Case).where(Case.id.in_(list(_tracked_case_ids)))
            )
        if _tracked_user_ids:
            await session.execute(
                delete(User).where(User.id.in_(list(_tracked_user_ids)))
            )
        await session.commit()


@pytest.fixture(scope="module", autouse=True)
def cleanup_tracked_fixtures():
    yield
    import asyncio
    asyncio.run(_async_cleanup())


async def seed_user(session: AsyncSession, email: str, role: UserRole = UserRole.LAWYER) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
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
    _tracked_user_ids.add(user_id)
    token = create_access_token(user_id=str(user_id), email=email, role=role, token_version=0)
    return user_id, token


async def seed_case(session: AsyncSession, owner_id: uuid.UUID, title: str = "Test Matter") -> Case:
    case_id = uuid.uuid4()
    case = Case(
        id=case_id,
        name=f"{title} {uuid.uuid4().hex[:6]}",
        description="Matter for testing pipeline status",
        status=CaseStatus.IN_PROGRESS,
        priority=CasePriority.MEDIUM,
        created_by=str(owner_id),
    )
    session.add(case)
    await session.commit()
    _tracked_case_ids.add(case_id)
    return case


async def seed_document(
    session: AsyncSession,
    uploaded_by: uuid.UUID,
    case_id: uuid.UUID | None = None,
    filename: str = "test_doc.pdf",
    status: DocumentStatus = DocumentStatus.UPLOADED,
    doc_metadata: dict | None = None,
) -> Document:
    doc_id = uuid.uuid4()
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
    _tracked_doc_ids.add(doc_id)
    return doc


@pytest.mark.asyncio
async def test_owner_can_get_pipeline_status_with_matching_history():
    """Verify owner can retrieve pipeline status and that stages match status_history rows honestly."""
    async with TestSession() as session:
        owner_id, owner_token = await seed_user(session, f"attorney_{uuid.uuid4().hex[:6]}@law.com")
        case = await seed_case(session, owner_id)
        doc = await seed_document(session, owner_id, case_id=case.id, status=DocumentStatus.UPLOADED)

        # Transition document through OCR and ANALYZING
        await record_status_transition(session, doc, DocumentStatus.OCR_PROCESSING, reason="ocr_pipeline_start")
        await record_status_transition(session, doc, DocumentStatus.ANALYZING, reason="legal_analysis_start")
        await session.commit()

    # Query via documents endpoint
    res = client.get(
        f"/api/v1/documents/{doc.id}/pipeline-status",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["caseId"] == str(case.id)
    assert data["documentId"] == str(doc.id)
    assert data["status"] == "analyzing"
    assert data["currentStage"] == "legal_review"
    assert data["isQuotaPaused"] is False
    assert data["historyAvailable"] is True
    assert data["stagesWithEvidence"] >= 2
    assert data["totalStages"] == 10
    assert data["overallProgress"] is None  # honest: frontend tolerates null
    assert data["estimatedCompletionAt"] is None  # honest: no fabricated ETA
    assert len(data["history"]) == 2
    assert data["history"][0]["new_status"] == "ocr_processing"
    assert data["history"][1]["new_status"] == "analyzing"
    assert data["lastReason"] == "legal_analysis_start"

    # Verify stage-level evidence
    stages_by_id = {s["id"]: s for s in data["stages"]}
    assert stages_by_id["document_upload"]["status"] == "completed"
    assert stages_by_id["document_upload"]["evidence"] == "status_history"
    assert stages_by_id["ocr"]["status"] == "completed"
    assert stages_by_id["ocr"]["evidence"] == "status_history"
    assert stages_by_id["legal_review"]["status"] == "running"
    assert stages_by_id["legal_review"]["evidence"] == "status_history"

    # Case-level stages with no records must be unknown with evidence none
    for case_stage_id in ["retrieval", "graph_generation", "timeline_generation", "final_report"]:
        assert stages_by_id[case_stage_id]["status"] == "unknown"
        assert stages_by_id[case_stage_id]["evidence"] == "none"

    # Invariant: Never return completed with evidence none
    for s in data["stages"]:
        if s["status"] == "completed":
            assert s["evidence"] != "none", f"Stage {s['id']} has status=completed but evidence=none!"

    # Query via agents endpoint with query params
    res_agents = client.get(
        f"/api/v1/agents/pipeline?caseId={case.id}&documentId={doc.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res_agents.status_code == 200
    data_agents = res_agents.json()
    assert data_agents["caseId"] == str(case.id)
    assert data_agents["documentId"] == str(doc.id)
    assert data_agents["historyAvailable"] is True


@pytest.mark.asyncio
async def test_pipeline_status_without_history_honesty():
    """
    Verify document without status_history rows (e.g., legacy/pre-existing doc)
    honestly reports historyAvailable=False, derives document stages with
    evidence='current_status_inference', marks case stages 'unknown' with evidence='none',
    and leaves completedAt=None.
    """
    async with TestSession() as session:
        owner_id, owner_token = await seed_user(session, f"legacy_{uuid.uuid4().hex[:6]}@law.com")
        case = await seed_case(session, owner_id)
        # Seed directly with terminal status REVIEWED and NO status_history rows
        doc = await seed_document(session, owner_id, case_id=case.id, status=DocumentStatus.REVIEWED)

    res = client.get(
        f"/api/v1/documents/{doc.id}/pipeline-status",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["historyAvailable"] is False
    assert data["history"] == []
    assert data["completedAt"] is None  # honest: no real timestamp in status_history
    assert data["overallProgress"] is None

    stages_by_id = {s["id"]: s for s in data["stages"]}

    # Document-level stages inferred from terminal REVIEWED status
    assert stages_by_id["document_upload"]["status"] == "completed"
    assert stages_by_id["document_upload"]["evidence"] == "current_status_inference"
    assert stages_by_id["ocr"]["status"] == "completed"
    assert stages_by_id["ocr"]["evidence"] == "current_status_inference"
    assert stages_by_id["indexing"]["status"] == "completed"
    assert stages_by_id["indexing"]["evidence"] == "current_status_inference"
    assert stages_by_id["legal_review"]["status"] == "completed"
    assert stages_by_id["legal_review"]["evidence"] == "current_status_inference"

    # Case-level stages must be unknown with evidence none
    for case_stage_id in ["case_creation", "retrieval", "graph_generation", "timeline_generation", "evidence_linking", "final_report"]:
        assert stages_by_id[case_stage_id]["status"] == "unknown"
        assert stages_by_id[case_stage_id]["evidence"] == "none"

    # Invariant: Never return completed with evidence none
    for s in data["stages"]:
        if s["status"] == "completed":
            assert s["evidence"] != "none"


@pytest.mark.asyncio
async def test_cross_tenant_isolation_forbidden():
    """Verify unauthorized user cannot access another user's document pipeline status (403)."""
    async with TestSession() as session:
        owner_id, _ = await seed_user(session, f"firmA_{uuid.uuid4().hex[:6]}@law.com")
        stranger_id, stranger_token = await seed_user(session, f"firmB_{uuid.uuid4().hex[:6]}@law.com")
        case = await seed_case(session, owner_id)
        doc = await seed_document(session, owner_id, case_id=case.id)

    # 1. Documents endpoint -> 403 Forbidden
    res = client.get(
        f"/api/v1/documents/{doc.id}/pipeline-status",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert res.status_code == 403

    # 2. Agents endpoint with stranger's token -> 403 Forbidden
    res_agents = client.get(
        f"/api/v1/agents/pipeline?caseId={case.id}&documentId={doc.id}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert res_agents.status_code == 403


@pytest.mark.asyncio
async def test_admin_override_access():
    """Verify admin role can access any document's pipeline status across tenants."""
    async with TestSession() as session:
        owner_id, _ = await seed_user(session, f"lawyer_{uuid.uuid4().hex[:6]}@law.com", UserRole.LAWYER)
        admin_id, admin_token = await seed_user(session, f"admin_{uuid.uuid4().hex[:6]}@law.com", UserRole.ADMIN)
        case = await seed_case(session, owner_id)
        doc = await seed_document(session, owner_id, case_id=case.id)

    res = client.get(
        f"/api/v1/documents/{doc.id}/pipeline-status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200
    assert res.json()["documentId"] == str(doc.id)


@pytest.mark.asyncio
async def test_existence_privacy_403_before_404():
    """Verify nonexistent or unowned case returns 403 to unauthorized users (Batch 3 pattern)."""
    async with TestSession() as session:
        stranger_id, stranger_token = await seed_user(session, f"stranger_{uuid.uuid4().hex[:6]}@law.com")

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
    async with TestSession() as session:
        owner_id, owner_token = await seed_user(session, f"owner_{uuid.uuid4().hex[:6]}@law.com")
        case = await seed_case(session, owner_id)

    nonexistent_doc = uuid.uuid4()
    res = client.get(
        f"/api/v1/agents/pipeline?caseId={case.id}&documentId={nonexistent_doc}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_quota_paused_representation():
    """Verify quota paused document honestly reports isQuotaPaused and paused stage."""
    metadata = {
        "paused_stage": "legal_review",
        "paused_reason": "Gemini API 429 ResourceExhausted: rate limit exceeded",
    }
    async with TestSession() as session:
        owner_id, owner_token = await seed_user(session, f"quota_{uuid.uuid4().hex[:6]}@law.com")
        case = await seed_case(session, owner_id)
        doc = await seed_document(
            session,
            owner_id,
            case_id=case.id,
            status=DocumentStatus.QUOTA_PAUSED,
            doc_metadata=metadata,
        )
        await record_status_transition(
            session,
            doc,
            DocumentStatus.QUOTA_PAUSED,
            reason="Gemini API 429 ResourceExhausted",
        )
        await session.commit()

    res = client.get(
        f"/api/v1/documents/{doc.id}/pipeline-status",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["isQuotaPaused"] is True
    assert data["pausedStage"] == "legal_review"
    assert "429" in data["pausedReason"]
    assert data["currentStage"] == "legal_review"
    paused_stage = next(s for s in data["stages"] if s["id"] == "legal_review")
    assert paused_stage["status"] == "paused"
    assert paused_stage["evidence"] == "status_history"


@pytest.mark.asyncio
async def test_agents_pipeline_unparameterized_eliminates_case_001():
    """Verify GET /api/v1/agents/pipeline without params returns 200 and no hardcoded case_001."""
    async with TestSession() as session:
        user_id, user_token = await seed_user(session, f"clean_{uuid.uuid4().hex[:6]}@law.com")

    res = client.get(
        "/api/v1/agents/pipeline",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["caseId"] is None  # Hardcoded 'case_001' is gone!
    assert "stages" in data
    assert len(data["stages"]) == 10
    assert data["historyAvailable"] is False
    assert data["stagesWithEvidence"] == 0
    assert data["overallProgress"] is None
    assert data["estimatedCompletionAt"] is None

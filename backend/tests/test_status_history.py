"""
Unit & Integration Tests for Document Status Audit Trail (status_history table).

Validates:
1. Single transition creates exactly one history row with correct old/new status.
2. Multiple transitions create a chronologically ordered history.
3. changed_by is populated for human-driven review actions and null for system pipeline transitions.
4. Contextual transition reasons are accurately stored.
5. Read endpoint (GET /documents/{id}/status-history) enforces creator-only + admin-override authorization (403 for non-owners).
6. Cascade delete removes all status_history rows when the parent document is deleted.
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_status_history.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
StatusSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

# Enable foreign key cascade delete enforcement in SQLite
@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

import app.db.session as db_session_module
_orig_session_local = db_session_module.AsyncSessionLocal

@pytest.fixture(scope="module", autouse=True)
def manage_session_local():
    db_session_module.AsyncSessionLocal = StatusSessionLocal
    try:
        yield
    finally:
        db_session_module.AsyncSessionLocal = _orig_session_local


from app.main import app
from app.db.base import Base
from app.models.document import Document, DocumentStatus
from app.models.status_history import StatusHistory
from app.models.user import User
from app.auth.dependencies import create_access_token, UserRole
from app.services.status_history_service import record_status_transition

client = TestClient(app)


async def init_test_db():
    db_session_module.AsyncSessionLocal = StatusSessionLocal
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def seed_user(user_id: uuid.UUID, email: str, role: UserRole = UserRole.LAWYER) -> str:
    async with StatusSessionLocal() as session:
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


async def seed_document(doc_id: uuid.UUID, uploaded_by: uuid.UUID, filename: str = "brief.pdf") -> Document:
    async with StatusSessionLocal() as session:
        doc = Document(
            id=doc_id,
            uploaded_by=uploaded_by,
            filename=filename,
            original_filename=filename,
            content_type="application/pdf",
            file_size=1024,
            storage_path=f"/tmp/{filename}",
            status=DocumentStatus.UPLOADED,
        )
        session.add(doc)
        await session.commit()
        return doc


@pytest.mark.asyncio
async def test_single_transition_creates_exact_history_row():
    """Verify a single transition records exactly one row with accurate old/new statuses."""
    await init_test_db()
    owner_id = uuid.uuid4()
    await seed_user(owner_id, "owner@firm.com")
    doc_id = uuid.uuid4()
    await seed_document(doc_id, owner_id)

    async with StatusSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        assert doc.status == DocumentStatus.UPLOADED

        # Transition UPLOADED -> OCR_PROCESSING
        history = await record_status_transition(
            session,
            doc,
            DocumentStatus.OCR_PROCESSING,
            reason="pipeline_stage_ocr",
        )
        await session.commit()

        assert doc.status == DocumentStatus.OCR_PROCESSING
        assert history.id is not None
        assert history.document_id == doc_id
        assert history.old_status == "uploaded"
        assert history.new_status == "ocr_processing"
        assert history.changed_by is None
        assert history.reason == "pipeline_stage_ocr"
        assert isinstance(history.changed_at, datetime)

        # Query database directly
        res = await session.execute(
            select(StatusHistory).where(StatusHistory.document_id == doc_id)
        )
        rows = res.scalars().all()
        assert len(rows) == 1
        assert rows[0].old_status == "uploaded"
        assert rows[0].new_status == "ocr_processing"


@pytest.mark.asyncio
async def test_multiple_transitions_ordered_history():
    """Verify multiple pipeline transitions create a chronologically ordered audit trail."""
    await init_test_db()
    owner_id = uuid.uuid4()
    await seed_user(owner_id, "owner2@firm.com")
    doc_id = uuid.uuid4()
    await seed_document(doc_id, owner_id)

    stages = [
        (DocumentStatus.OCR_PROCESSING, "pipeline_stage_ocr"),
        (DocumentStatus.CHUNKING, "pipeline_stage_chunking"),
        (DocumentStatus.EMBEDDING, "pipeline_stage_embedding"),
        (DocumentStatus.ANALYZING, "pipeline_stage_analyzing"),
        (DocumentStatus.REVIEWED, "pipeline_stage_review_completed"),
    ]

    async with StatusSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        for target_status, reason in stages:
            await record_status_transition(session, doc, target_status, reason=reason)
            await session.commit()

        # Query ordered history
        stmt = (
            select(StatusHistory)
            .where(StatusHistory.document_id == doc_id)
            .order_by(StatusHistory.changed_at.asc(), StatusHistory.created_at.asc())
        )
        res = await session.execute(stmt)
        history_rows = res.scalars().all()

        assert len(history_rows) == 5
        expected_transitions = [
            ("uploaded", "ocr_processing"),
            ("ocr_processing", "chunking"),
            ("chunking", "embedding"),
            ("embedding", "analyzing"),
            ("analyzing", "reviewed"),
        ]
        for row, (expected_old, expected_new) in zip(history_rows, expected_transitions):
            assert row.old_status == expected_old
            assert row.new_status == expected_new


@pytest.mark.asyncio
async def test_changed_by_attribution_system_vs_human():
    """Verify changed_by is null for system transitions and populated for human actions."""
    await init_test_db()
    reviewer_id = uuid.uuid4()
    await seed_user(reviewer_id, "reviewer@firm.com")
    doc_id = uuid.uuid4()
    await seed_document(doc_id, reviewer_id)

    async with StatusSessionLocal() as session:
        doc = await session.get(Document, doc_id)

        # 1. System transition
        await record_status_transition(
            session, doc, DocumentStatus.ANALYZING, reason="system_batch_pipeline"
        )
        # 2. Human override transition
        await record_status_transition(
            session,
            doc,
            DocumentStatus.FLAGGED,
            changed_by=reviewer_id,
            reason="human_review_override:privilege",
        )
        await session.commit()

        stmt = select(StatusHistory).where(StatusHistory.document_id == doc_id).order_by(StatusHistory.created_at.asc())
        rows = (await session.execute(stmt)).scalars().all()

        assert len(rows) == 2
        assert rows[0].changed_by is None
        assert rows[0].reason == "system_batch_pipeline"
        assert rows[1].changed_by == reviewer_id
        assert rows[1].reason == "human_review_override:privilege"


@pytest.mark.asyncio
async def test_read_endpoint_creator_only_and_admin_authorization():
    """Verify GET /api/v1/documents/{id}/status-history enforces creator-only + admin access."""
    await init_test_db()
    owner_id = uuid.uuid4()
    stranger_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    owner_token = await seed_user(owner_id, "owner3@firm.com", UserRole.LAWYER)
    stranger_token = await seed_user(stranger_id, "stranger@otherfirm.com", UserRole.LAWYER)
    admin_token = await seed_user(admin_id, "admin@firm.com", UserRole.ADMIN)

    doc_id = uuid.uuid4()
    await seed_document(doc_id, owner_id)

    # Add transitions
    async with StatusSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        await record_status_transition(session, doc, DocumentStatus.OCR_PROCESSING, reason="pipeline_ocr")
        await record_status_transition(session, doc, DocumentStatus.REVIEWED, changed_by=owner_id, reason="human_confirm")
        await session.commit()

    # 1. Unauthenticated request -> 401
    unauth_res = client.get(f"/api/v1/documents/{doc_id}/status-history")
    assert unauth_res.status_code == 401

    # 2. Stranger request -> 403 Forbidden
    stranger_res = client.get(
        f"/api/v1/documents/{doc_id}/status-history",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert stranger_res.status_code == 403

    # 3. Owner request -> 200 OK with ordered history
    owner_res = client.get(
        f"/api/v1/documents/{doc_id}/status-history",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_res.status_code == 200
    owner_data = owner_res.json()
    assert len(owner_data) == 2
    assert owner_data[0]["old_status"] == "uploaded"
    assert owner_data[0]["new_status"] == "ocr_processing"
    assert owner_data[0]["changed_by"] is None
    assert owner_data[1]["old_status"] == "ocr_processing"
    assert owner_data[1]["new_status"] == "reviewed"
    assert owner_data[1]["changed_by"] == str(owner_id)

    # 4. Admin request -> 200 OK (admin override)
    admin_res = client.get(
        f"/api/v1/documents/{doc_id}/status-history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    assert len(admin_res.json()) == 2

    # 5. Non-existent document -> 404
    missing_id = uuid.uuid4()
    missing_res = client.get(
        f"/api/v1/documents/{missing_id}/status-history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert missing_res.status_code == 404


@pytest.mark.asyncio
async def test_cascade_delete_removes_status_history():
    """Verify deleting a parent document cascade-deletes its status_history rows."""
    await init_test_db()
    owner_id = uuid.uuid4()
    await seed_user(owner_id, "owner4@firm.com")
    doc_id = uuid.uuid4()
    await seed_document(doc_id, owner_id)

    async with StatusSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        await record_status_transition(session, doc, DocumentStatus.VALIDATING, reason="retry_requested")
        await record_status_transition(session, doc, DocumentStatus.QUOTA_PAUSED, reason="quota_exhausted")
        await session.commit()

        # Confirm 2 history rows exist
        stmt = select(StatusHistory).where(StatusHistory.document_id == doc_id)
        res = await session.execute(stmt)
        assert len(res.scalars().all()) == 2

        # Delete the document
        await session.delete(doc)
        await session.commit()

        # Confirm status_history rows were CASCADE deleted
        res_after = await session.execute(stmt)
        assert len(res_after.scalars().all()) == 0

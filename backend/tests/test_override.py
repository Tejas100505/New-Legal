"""
Integration tests for Human Override endpoint and Audit Log persistence.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

TEST_DB_URL = "sqlite+aiosqlite:///./test_override.db"
override_engine = create_async_engine(TEST_DB_URL, echo=False)
OverrideSessionLocal = async_sessionmaker(bind=override_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module
db_session_module.AsyncSessionLocal = OverrideSessionLocal

from app.main import app
from app.db.base import Base
from app.models.document import Document, DocumentStatus
from app.models.audit_log import AuditLog
from app.auth.dependencies import create_access_token, UserRole
from app.schemas.document import OverrideField, OverrideAction

client = TestClient(app)


async def init_test_db():
    db_session_module.AsyncSessionLocal = OverrideSessionLocal
    async with override_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_override_requires_authentication():
    """Verify POST /documents/{id}/override requires a Bearer token."""
    fake_id = str(uuid.uuid4())
    res = client.post(f"/api/v1/documents/{fake_id}/override", json={
        "field": "privilege",
        "action": "override",
        "override_value": False,
        "reason": "Test reason"
    })
    assert res.status_code == 401
    assert "Missing authentication credentials" in res.json()["detail"]


@pytest.mark.asyncio
async def test_override_field_enum_validation():
    """Verify invalid free-text field strings are rejected by Pydantic validation (422)."""
    await init_test_db()
    token = create_access_token(user_id=str(uuid.uuid4()), email="lawyer@firm.com", role=UserRole.LAWYER)
    headers = {"Authorization": f"Bearer {token}"}
    fake_id = str(uuid.uuid4())

    # Invalid field name not in OverrideField enum
    res = client.post(f"/api/v1/documents/{fake_id}/override", json={
        "field": "invalid_random_field",
        "action": "override",
        "override_value": False,
        "reason": "Test reason"
    }, headers=headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_human_override_and_audit_log_flow():
    """Verify human override updates document metadata and writes a verifiable audit log entry."""
    await init_test_db()

    user_id = str(uuid.uuid4())
    reviewer_email = "senior_counsel@apexlegal.com"
    token = create_access_token(user_id=user_id, email=reviewer_email, role=UserRole.LAWYER)
    headers = {"Authorization": f"Bearer {token}"}

    # Create a test document in the DB
    doc_id = uuid.uuid4()
    async with OverrideSessionLocal() as session:
        test_doc = Document(
            id=doc_id,
            uploaded_by=uuid.UUID(user_id),
            filename="confidential_memo.txt",
            original_filename="confidential_memo.txt",
            content_type="text/plain",
            file_size=1024,
            storage_path="/tmp/confidential_memo.txt",
            status=DocumentStatus.ANALYZING,
            extracted_text="Sample text of legal memo.",
            doc_metadata={
                "privilege_analysis": {
                    "is_privileged": True,
                    "confidence_score": 0.95,
                    "reasoning": "Attorney-client privilege keywords detected."
                }
            }
        )
        session.add(test_doc)
        await session.commit()

    # Execute override: AI said privileged, human overrides to False
    override_payload = {
        "field": OverrideField.PRIVILEGE.value,
        "action": OverrideAction.OVERRIDE.value,
        "override_value": False,
        "original_ai_value": True,
        "ai_confidence": 0.95,
        "reason": "Draft internal memo; no legal advice requested or rendered."
    }

    res = client.post(f"/api/v1/documents/{doc_id}/override", json=override_payload, headers=headers)
    assert res.status_code == 200, res.text
    resp_data = res.json()

    # 1. Document metadata updated
    meta = resp_data["doc_metadata"]
    assert meta["review_status"] == "reviewed_by_human"
    assert meta["reviewed_by"] == reviewer_email
    assert meta["privilege_analysis"]["is_privileged"] is False
    assert meta["privilege_analysis"]["human_overridden"] is True
    assert len(meta["human_overrides"]) == 1
    assert meta["human_overrides"][0]["reason"] == "Draft internal memo; no legal advice requested or rendered."
    assert resp_data["status"] == "reviewed"

    # 2. AuditLog table record verified directly in database
    async with OverrideSessionLocal() as session:
        stmt = select(AuditLog).where(
            AuditLog.resource_id == str(doc_id),
            AuditLog.action == "DOCUMENT_HUMAN_OVERRIDE_PRIVILEGE"
        )
        result = await session.execute(stmt)
        log_entry = result.scalars().first()

        assert log_entry is not None
        assert log_entry.user_email == reviewer_email
        assert log_entry.resource_type == "document"
        assert log_entry.details["override_value"] is False
        assert log_entry.details["original_ai_value"] is True
        assert log_entry.details["reason"] == "Draft internal memo; no legal advice requested or rendered."

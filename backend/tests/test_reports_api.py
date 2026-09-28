"""
Tests for the Reports API and Case Scoping Service.

Verifies:
1. get_case_scoped_document_ids access model (creator-only ownership + admin override).
2. /api/v1/reports/export endpoint produces genuine DB-backed report data (not mock constants).
3. Cross-tenant access isolation returns 403 Forbidden for unauthorized users.
4. Report formats (JSON, Markdown, CSV) return real, consistent contents via ReportAgent.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_reports_db.db"
reports_engine = create_async_engine(TEST_DB_URL, echo=False)
ReportsSessionLocal = async_sessionmaker(bind=reports_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module
from app.main import app
from app.db.base import Base
from app.models.case import Case, CaseStatus, CasePriority
from app.models.document import Document, DocumentStatus
from app.auth.dependencies import create_access_token, UserRole
from app.services.case_scoping import get_case_scoped_document_ids


async def init_test_db():
    db_session_module.AsyncSessionLocal = ReportsSessionLocal
    async with reports_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


from app.models.user import User


client = TestClient(app)


@pytest.mark.asyncio
async def test_case_scoping_helper_and_report_export():
    """Verify shared case-scoping helper and report export endpoint with real DB data."""
    await init_test_db()

    user_owner_id = str(uuid.uuid4())
    user_stranger_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())

    async with ReportsSessionLocal() as session:
        session.add(User(
            id=uuid.UUID(user_owner_id),
            email="owner@firm.com",
            hashed_password="pw",
            full_name="Owner Lawyer",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        ))
        session.add(User(
            id=uuid.UUID(user_stranger_id),
            email="stranger@firm.com",
            hashed_password="pw",
            full_name="Stranger Lawyer",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        ))
        session.add(User(
            id=uuid.UUID(admin_id),
            email="admin@corp.com",
            hashed_password="pw",
            full_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
            token_version=0,
        ))
        await session.commit()

    token_owner = create_access_token(user_id=user_owner_id, email="owner@firm.com", role=UserRole.LAWYER, token_version=0)
    token_stranger = create_access_token(user_id=user_stranger_id, email="stranger@firm.com", role=UserRole.LAWYER, token_version=0)
    token_admin = create_access_token(user_id=admin_id, email="admin@corp.com", role=UserRole.ADMIN, token_version=0)

    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_stranger = {"Authorization": f"Bearer {token_stranger}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    case_id = uuid.uuid4()
    doc1_id = uuid.uuid4()
    doc2_id = uuid.uuid4()

    async with ReportsSessionLocal() as session:
        case = Case(
            id=case_id,
            name="Solaria Photovoltaics Litigation",
            case_number="SOLARIA-2026-001",
            status=CaseStatus.IN_PROGRESS,
            priority=CasePriority.HIGH,
            created_by=user_owner_id,
        )
        doc1 = Document(
            id=doc1_id,
            case_id=case_id,
            uploaded_by=uuid.UUID(user_owner_id),
            filename="solaria_cell_spec.pdf",
            original_filename="solaria_cell_spec.pdf",
            content_type="application/pdf",
            file_size=2048,
            storage_path="/tmp/solaria_cell_spec.pdf",
            status=DocumentStatus.REVIEWED,
            extracted_text="Confidential attorney-client memo regarding solar cell manufacturing claims.",
            doc_metadata={
                "privilege_analysis": {"is_privileged": True, "confidence_score": 0.98},
                "risk_analysis": {
                    "assessments": [
                        {"category": "Patent Infringement", "risk_level": "HIGH", "reason": "Claim overlap identified"}
                    ]
                },
                "timeline": [
                    {"date": "2024-03-15", "description": "Patent claim filed with USPTO"}
                ]
            },
        )
        doc2 = Document(
            id=doc2_id,
            case_id=case_id,
            uploaded_by=uuid.UUID(user_owner_id),
            filename="unrelated_invoice.pdf",
            original_filename="unrelated_invoice.pdf",
            content_type="application/pdf",
            file_size=1024,
            storage_path="/tmp/unrelated_invoice.pdf",
            status=DocumentStatus.REVIEWED,
            extracted_text="Standard vendor invoice for office supplies.",
            doc_metadata={
                "privilege_analysis": {"is_privileged": False},
                "risk_analysis": {"assessments": []},
                "timeline": [
                    {"date": "2024-05-01", "description": "Invoice payment processed"}
                ]
            },
        )
        session.add(case)
        session.add(doc1)
        session.add(doc2)
        await session.commit()

    # 1. Test shared case-scoping helper directly
    from app.auth.dependencies import TokenPayload
    payload_owner = TokenPayload(sub=user_owner_id, email="owner@firm.com", role=UserRole.LAWYER)
    payload_stranger = TokenPayload(sub=user_stranger_id, email="stranger@firm.com", role=UserRole.LAWYER)
    payload_admin = TokenPayload(sub=admin_id, email="admin@corp.com", role=UserRole.ADMIN)

    async with ReportsSessionLocal() as session:
        # Owner sees both docs
        scoped_docs = await get_case_scoped_document_ids(session, case_id, payload_owner)
        assert len(scoped_docs) == 2
        assert doc1_id in scoped_docs
        assert doc2_id in scoped_docs

        # Admin sees both docs
        admin_docs = await get_case_scoped_document_ids(session, case_id, payload_admin)
        assert len(admin_docs) == 2

        # Stranger is denied with 403
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_case_scoped_document_ids(session, case_id, payload_stranger)
        assert exc_info.value.status_code == 403

    # 2. Test JSON report export for real case
    res_json = client.post(f"/api/v1/reports/export?case_id={case_id}&format=json", headers=headers_owner)
    assert res_json.status_code == 200
    data = res_json.json()
    assert data["case_id"] == str(case_id)
    assert data["case_name"] == "Solaria Photovoltaics Litigation"
    assert data["key_metrics"]["documents_analyzed"] == 2
    assert data["key_metrics"]["privileged_documents"] == 1
    assert data["key_metrics"]["high_risk_flags"] == 1
    assert len(data["timeline"]) == 2
    assert len(data["risks"]) == 1
    assert data["risks"][0]["category"] == "Patent Infringement"

    # 3. Test Markdown report export
    res_md = client.post(f"/api/v1/reports/export?case_id={case_id}&format=markdown", headers=headers_owner)
    assert res_md.status_code == 200
    assert "# E-Discovery Review Report" in res_md.text
    assert "Solaria Photovoltaics Litigation" in res_md.text or str(case_id) in res_md.text
    assert "Patent claim filed with USPTO" in res_md.text
    assert "Patent Infringement" in res_md.text

    # 4. Test CSV report export
    res_csv = client.post(f"/api/v1/reports/export?case_id={case_id}&format=csv", headers=headers_owner)
    assert res_csv.status_code == 200
    assert "Timeline,2024-03-15,Patent claim filed with USPTO" in res_csv.text

    # 5. Test PDF export format status
    from app.agents.report import REPORTLAB_AVAILABLE, DOCX_AVAILABLE
    res_pdf = client.post(f"/api/v1/reports/export?case_id={case_id}&format=pdf", headers=headers_owner)
    if REPORTLAB_AVAILABLE:
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert len(res_pdf.content) > 0
    else:
        assert res_pdf.status_code == 400
        assert "ReportLab is not installed or available" in res_pdf.json()["detail"]

    # 6. Test DOCX export format status
    res_docx = client.post(f"/api/v1/reports/export?case_id={case_id}&format=docx", headers=headers_owner)
    if DOCX_AVAILABLE:
        assert res_docx.status_code == 200
        assert "officedocument.wordprocessingml" in res_docx.headers["content-type"]
        assert len(res_docx.content) > 0
    else:
        assert res_docx.status_code == 400
        assert "python-docx is not installed or available" in res_docx.json()["detail"]

    # 7. Test Stranger access is forbidden
    res_stranger = client.post(f"/api/v1/reports/export?case_id={case_id}&format=json", headers=headers_stranger)
    assert res_stranger.status_code == 403
    assert "Access denied" in res_stranger.json()["detail"]

    # 8. Test Admin override succeeds
    res_admin = client.post(f"/api/v1/reports/export?case_id={case_id}&format=json", headers=headers_admin)
    assert res_admin.status_code == 200
    assert res_admin.json()["key_metrics"]["documents_analyzed"] == 2

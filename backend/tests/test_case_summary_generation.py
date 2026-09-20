"""
Comprehensive Tests for Case Summary Generation (Batch 2).

Verifies:
1. Security Authorization:
   - test_summary_generate_stranger_403
   - test_summary_generate_cross_case_403
   - test_summary_generate_admin_override_ok
   - test_summary_get_stranger_403
   - test_summary_get_cross_case_403
2. State Machine (6 rows):
   - row 1: No summary exists -> GET returns 404
   - row 2: Generating -> POST sets GENERATING, GET returns previous COMPLETE with generating:true
   - row 3: Success -> status COMPLETE, atomic update with summary_json, generated_at, model_version
   - row 4: Failure (non-quota) -> status FAILED, GET serves previous COMPLETE with failed_last_generation:true
   - row 5: Quota exhausted -> status QUOTA_PAUSED, HTTP 503, previous COMPLETE remains served
   - row 6: Stale -> live hash mismatch on GET returns stale:true without triggering regeneration
3. Concurrency Guard:
   - Near-simultaneous POST /generate returns 409 Conflict, exactly 1 LLM call executes
4. Rate Limiting:
   - Shared limiter allows 2/min, 3rd call returns 429
5. Real 423-document Case Generation & LLM Call Count Instrumentation:
   - Generates summary on real case 8d8389d4-2534-452d-85b4-65efe5b8e1c3
   - Asserts total LLM call count <= 5 (achieved <= 3)
   - Validates all 5 required sections
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.dependencies import create_access_token, UserRole
from app.agents.gemini_client import QuotaExhaustedException
from app.config import get_settings
from app.core.rate_limit import limiter
from app.main import app
from app.models.case import Case, CaseStatus, CasePriority
from app.models.case_summary import CaseSummary, CaseSummaryStatus
from app.models.document import Document, DocumentStatus
from app.repositories.case_summary_repository import CaseSummaryRepository
from app.services.case_intelligence_service import (
    generate_case_summary,
    get_case_summary_llm_call_count,
    reset_case_summary_llm_call_count,
    compute_case_data_hash,
)

settings = get_settings()

# NullPool prevents event-loop binding issues on Windows / Python 3.13
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

from app.db.session import get_db

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

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

MOCK_SUMMARY_PAYLOAD = {
    "case_id": "",
    "case_name": "Test Litigation",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "metrics": {
        "total_documents": 2,
        "privileged_documents_count": 1,
        "high_or_critical_risk_count": 1,
        "flagged_documents_count": 0,
        "timeline_span": {
            "start_date": "2024-01-01",
            "end_date": "2024-06-01",
            "total_events": 2
        }
    },
    "sections": {
        "executive": "Executive summary of the case findings and evidentiary landscape.",
        "legal": "Legal framing and posture regarding regulatory scrutiny and breach claims.",
        "notable_provisions_and_findings": "Notable provisions include indemnification and confidentiality restrictions.",
        "evidence": "Evidence highlights key communications from senior leadership regarding pricing.",
        "key_people_and_relationships": "Key entities include Shelley Corman and Enron Corporation."
    },
    "top_entities": [{"name": "Enron", "type": "company", "document_mentions_count": 5}],
    "key_dates": [{"date": "2024-01-01", "title": "Contract signing"}]
}


@pytest.fixture(autouse=True)
def reset_limiter_and_tracker():
    limiter.reset()
    reset_case_summary_llm_call_count()
    yield
    limiter.reset()
    reset_case_summary_llm_call_count()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_fixture_case(session: AsyncSession, creator_sub: str, name: str = "Test Case") -> Case:
    case = Case(
        id=uuid.uuid4(),
        name=f"{name} {uuid.uuid4().hex[:6]}",
        case_number=f"CASE-{uuid.uuid4().hex[:6].upper()}",
        status=CaseStatus.IN_PROGRESS,
        priority=CasePriority.MEDIUM,
        created_by=creator_sub,
    )
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


async def create_fixture_doc(
    session: AsyncSession,
    case_id: uuid.UUID,
    filename: str = "doc.txt",
    is_priv: bool = False,
    risk: str = "low",
) -> Document:
    priv_data = {
        "is_privileged": is_priv,
        "detections": [{"privilege_type": "Attorney-Client Privilege", "detected": is_priv}] if is_priv else [],
        "reasoning": "Legal consultation." if is_priv else "Standard business communication."
    }
    risk_data = {"risk_level": risk, "risk_factors": [f"Risk factor {risk}"]}
    meta = {
        "privilege_analysis": priv_data,
        "risk_analysis": risk_data,
        "summary": {"executive_summary": f"Executive summary for {filename}."},
        "timeline": [{"date": "2024-03-01", "title": f"Event in {filename}"}],
        "entities": {"company": ["Enron Corp"], "person": ["Shelley Corman"]},
    }
    doc = Document(
        id=uuid.uuid4(),
        case_id=case_id,
        filename=filename,
        original_filename=filename,
        storage_path=f"/test/{filename}",
        file_size=1024,
        content_type="text/plain",
        status=DocumentStatus.REVIEWED,
        doc_metadata=meta,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


# ===========================================================================
# 1. Five Security Tests (Section 1 of Checklist)
# ===========================================================================

@pytest.mark.asyncio
async def test_summary_generate_stranger_403():
    """Stranger attempting to generate summary on an unowned case receives 403."""
    async with TestSession() as session:
        owner_sub = str(uuid.uuid4())
        stranger_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, owner_sub, "Owner Secret Case")
        await create_fixture_doc(session, case.id)

    token_stranger = create_access_token(user_id=stranger_sub, email="stranger@law.com", role=UserRole.LAWYER)
    resp = client.post(
        f"/api/v1/cases/{case.id}/summary/generate",
        headers={"Authorization": f"Bearer {token_stranger}"},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_summary_generate_cross_case_403():
    """User who owns Case A attempting to generate summary on Case B receives 403."""
    async with TestSession() as session:
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())
        case_a = await create_fixture_case(session, user_a, "Case A")
        case_b = await create_fixture_case(session, user_b, "Case B")
        await create_fixture_doc(session, case_b.id)

    token_a = create_access_token(user_id=user_a, email="user_a@law.com", role=UserRole.LAWYER)
    resp = client.post(
        f"/api/v1/cases/{case_b.id}/summary/generate",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_summary_generate_admin_override_ok():
    """Admin is permitted to generate summary on any case regardless of ownership."""
    async with TestSession() as session:
        owner_sub = str(uuid.uuid4())
        admin_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, owner_sub, "Admin Accessible Case")
        await create_fixture_doc(session, case.id)

    token_admin = create_access_token(user_id=admin_sub, email="admin@corp.com", role=UserRole.ADMIN)

    with patch("app.services.case_intelligence_service.LLMClient.generate_text", new_callable=AsyncMock) as mock_llm:
        mock_payload = dict(MOCK_SUMMARY_PAYLOAD)
        mock_payload["case_id"] = str(case.id)
        import json
        mock_llm.return_value = json.dumps(mock_payload)

        resp = client.post(
            f"/api/v1/cases/{case.id}/summary/generate",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == str(case.id)
        assert data["status"] == "complete"
        assert "executive" in data["summary_json"]["sections"]


@pytest.mark.asyncio
async def test_summary_get_stranger_403():
    """Stranger attempting to read summary of an unowned case receives 403."""
    async with TestSession() as session:
        owner_sub = str(uuid.uuid4())
        stranger_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, owner_sub, "Stranger Read Case")
        await create_fixture_doc(session, case.id)

    token_stranger = create_access_token(user_id=stranger_sub, email="stranger@law.com", role=UserRole.LAWYER)
    resp = client.get(
        f"/api/v1/cases/{case.id}/summary",
        headers={"Authorization": f"Bearer {token_stranger}"},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_summary_get_cross_case_403():
    """User possessing valid token for Case A attempting GET on Case B receives 403."""
    async with TestSession() as session:
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())
        case_a = await create_fixture_case(session, user_a, "Case A")
        case_b = await create_fixture_case(session, user_b, "Case B")

    token_a = create_access_token(user_id=user_a, email="user_a@law.com", role=UserRole.LAWYER)
    resp = client.get(
        f"/api/v1/cases/{case_b.id}/summary",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


# ===========================================================================
# 2. State Machine Tests (All 6 Rows)
# ===========================================================================

@pytest.mark.asyncio
async def test_state_machine_row1_no_summary_404():
    """Row 1: First GET before any summary generation returns 404 with explicit message."""
    async with TestSession() as session:
        user_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, user_sub, "Unsummarized Case")

    token = create_access_token(user_id=user_sub, email="lawyer@law.com", role=UserRole.LAWYER)
    resp = client.get(
        f"/api/v1/cases/{case.id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert "No summary generated yet" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_state_machine_row2_generating_serves_previous_complete():
    """Row 2: While GENERATING is in flight, GET returns previous COMPLETE with generating:true."""
    async with TestSession() as session:
        user_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, user_sub, "In-Flight Case")
        doc = await create_fixture_doc(session, case.id)
        current_hash = compute_case_data_hash([doc])

        repo = CaseSummaryRepository(session)
        from datetime import timedelta
        # Write previous complete (10 seconds ago)
        prev = CaseSummary(
            id=uuid.uuid4(),
            case_id=case.id,
            status=CaseSummaryStatus.COMPLETE,
            source_doc_count=1,
            source_data_hash=current_hash,
            summary_json=MOCK_SUMMARY_PAYLOAD,
            model_version=settings.google_model or "gemini-3.5-flash-lite",
            generated_at=datetime.now(timezone.utc) - timedelta(seconds=10),
            created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        session.add(prev)
        await session.flush()

        # Write currently generating (now)
        in_flight = CaseSummary(
            id=uuid.uuid4(),
            case_id=case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=1,
            source_data_hash=current_hash,
            created_at=datetime.now(timezone.utc),
        )
        session.add(in_flight)
        await session.commit()

    token = create_access_token(user_id=user_sub, email="lawyer@law.com", role=UserRole.LAWYER)
    resp = client.get(
        f"/api/v1/cases/{case.id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["generating"] is True
    assert data["summary_json"] is not None
    assert "executive" in data["summary_json"]["sections"]


@pytest.mark.asyncio
async def test_state_machine_row3_success_complete():
    """Row 3: Successful synthesis sets status=COMPLETE atomically with summary_json and generated_at."""
    async with TestSession() as session:
        user_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, user_sub, "Success Case")
        await create_fixture_doc(session, case.id)

    token = create_access_token(user_id=user_sub, email="lawyer@law.com", role=UserRole.LAWYER)

    import json
    mock_payload = dict(MOCK_SUMMARY_PAYLOAD)
    mock_payload["case_id"] = str(case.id)

    with patch("app.services.case_intelligence_service.LLMClient.generate_text", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = json.dumps(mock_payload)

        resp = client.post(
            f"/api/v1/cases/{case.id}/summary/generate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "complete"
        assert data["generated_at"] is not None
        assert data["model_version"] == (settings.google_model or "gemini-3.5-flash-lite")

    # Verify directly from DB
    async with TestSession() as session:
        repo = CaseSummaryRepository(session)
        latest = await repo.get_latest_by_case_id(case.id)
        assert latest is not None
        assert latest.status == CaseSummaryStatus.COMPLETE
        assert latest.summary_json["sections"]["executive"] is not None


@pytest.mark.asyncio
async def test_state_machine_row4_failure_serves_previous_complete():
    """Row 4: Non-quota failure sets status=FAILED; GET serves previous COMPLETE with failure indicator."""
    async with TestSession() as session:
        user_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, user_sub, "Failure Case")
        doc = await create_fixture_doc(session, case.id)
        current_hash = compute_case_data_hash([doc])

        repo = CaseSummaryRepository(session)
        # Establish previous complete summary
        await repo.create(
            case_id=case.id,
            status=CaseSummaryStatus.COMPLETE,
            source_doc_count=1,
            source_data_hash=current_hash,
            summary_json=MOCK_SUMMARY_PAYLOAD,
            model_version=settings.google_model or "gemini-3.5-flash-lite",
            generated_at=datetime.now(timezone.utc),
        )
        await session.commit()

    token = create_access_token(user_id=user_sub, email="lawyer@law.com", role=UserRole.LAWYER)

    # Induce malformed model JSON response
    with patch("app.services.case_intelligence_service.LLMClient.generate_text", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "MALFORMED NON-JSON TEXT"

        resp = client.post(
            f"/api/v1/cases/{case.id}/summary/generate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (400, 500)

    # Verify latest record is FAILED
    async with TestSession() as session:
        repo = CaseSummaryRepository(session)
        latest = await repo.get_latest_by_case_id(case.id)
        assert latest.status == CaseSummaryStatus.FAILED

    # GET serves previous COMPLETE with failed_last_generation banner
    get_resp = client.get(
        f"/api/v1/cases/{case.id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["failed_last_generation"] is True
    assert data["last_generation_status"] == "failed"
    assert data["summary_json"] is not None


@pytest.mark.asyncio
async def test_state_machine_row5_quota_exhausted():
    """Row 5: QuotaExhaustedException sets status=QUOTA_PAUSED, returns 503, serves previous COMPLETE."""
    async with TestSession() as session:
        user_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, user_sub, "Quota Case")
        doc = await create_fixture_doc(session, case.id)
        current_hash = compute_case_data_hash([doc])

        repo = CaseSummaryRepository(session)
        await repo.create(
            case_id=case.id,
            status=CaseSummaryStatus.COMPLETE,
            source_doc_count=1,
            source_data_hash=current_hash,
            summary_json=MOCK_SUMMARY_PAYLOAD,
            model_version="gemini-2.5-flash",
            generated_at=datetime.now(timezone.utc),
        )
        await session.commit()

    token = create_access_token(user_id=user_sub, email="lawyer@law.com", role=UserRole.LAWYER)

    # Induce QuotaExhaustedException
    with patch("app.services.case_intelligence_service.LLMClient.generate_text", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = QuotaExhaustedException("Gemini quota exhausted (429)")

        resp = client.post(
            f"/api/v1/cases/{case.id}/summary/generate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
        assert "quota exhausted" in resp.json()["detail"].lower()

    # Verify latest record is QUOTA_PAUSED
    async with TestSession() as session:
        repo = CaseSummaryRepository(session)
        latest = await repo.get_latest_by_case_id(case.id)
        assert latest.status == CaseSummaryStatus.QUOTA_PAUSED

    # GET serves previous COMPLETE with last_generation_status = quota_paused
    get_resp = client.get(
        f"/api/v1/cases/{case.id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["failed_last_generation"] is True
    assert data["last_generation_status"] == "quota_paused"


@pytest.mark.asyncio
async def test_state_machine_row6_staleness():
    """Row 6: When doc timestamps mutate, GET returns stale:true without triggering regeneration."""
    async with TestSession() as session:
        user_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, user_sub, "Staleness Case")
        doc = await create_fixture_doc(session, case.id)
        old_hash = compute_case_data_hash([doc])

        repo = CaseSummaryRepository(session)
        await repo.create(
            case_id=case.id,
            status=CaseSummaryStatus.COMPLETE,
            source_doc_count=1,
            source_data_hash=old_hash,
            summary_json=MOCK_SUMMARY_PAYLOAD,
            model_version="gemini-2.5-flash",
            generated_at=datetime.now(timezone.utc),
        )
        await session.commit()

        # Mutate document updated_at to simulate processing update
        doc.updated_at = datetime.now(timezone.utc)
        session.add(doc)
        await session.commit()

    token = create_access_token(user_id=user_sub, email="lawyer@law.com", role=UserRole.LAWYER)

    # Spy on LLMClient to guarantee zero regeneration is triggered on GET
    with patch("app.services.case_intelligence_service.LLMClient.generate_text", new_callable=AsyncMock) as mock_llm:
        resp = client.get(
            f"/api/v1/cases/{case.id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stale"] is True
        assert data["status"] == "complete"
        mock_llm.assert_not_called()


# ===========================================================================
# 3. Concurrency Guard & Rate Limiting Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_concurrency_guard_returns_409_and_single_llm_execution():
    """
    Simultaneously firing two generation requests for the same case returns 409
    for the second request and executes exactly one LLM call sequence.
    """
    async with TestSession() as session:
        user_sub = str(uuid.uuid4())
        case = await create_fixture_case(session, user_sub, "Concurrency Case")
        await create_fixture_doc(session, case.id)

    token = create_access_token(user_id=user_sub, email="lawyer@law.com", role=UserRole.LAWYER)
    headers = {"Authorization": f"Bearer {token}"}

    import json
    mock_payload = dict(MOCK_SUMMARY_PAYLOAD)
    mock_payload["case_id"] = str(case.id)

    llm_call_count = 0

    async def slow_generate_text(*args, **kwargs):
        nonlocal llm_call_count
        llm_call_count += 1
        # Sleep long enough so task2 arrives while task1 is waiting inside LLM generation
        await asyncio.sleep(1.5)
        return json.dumps(mock_payload)

    with patch("app.services.case_intelligence_service.LLMClient.generate_text", side_effect=slow_generate_text):
        loop = asyncio.get_running_loop()
        
        def run_call():
            return client.post(f"/api/v1/cases/{case.id}/summary/generate", headers=headers)

        task1 = loop.run_in_executor(None, run_call)
        # Sleep 0.4s to guarantee task1 creates and commits the GENERATING DB record before task2 starts
        await asyncio.sleep(0.4)
        task2 = loop.run_in_executor(None, run_call)

        resp1, resp2 = await asyncio.gather(task1, task2)

        status_codes = sorted([resp1.status_code, resp2.status_code])
        assert status_codes == [200, 409], f"Expected [200, 409], got {status_codes}"
        # Exactly one LLM execution ran
        assert llm_call_count == 1


def test_rate_limit_2_per_minute():
    """
    Verify shared limiter limits /generate endpoint to 2/minute.
    With an unauthorized non-existent case_id and lawyer role, get_case_scoped_document_ids
    deterministically rejects attempts 1 and 2 with HTTP 403 Forbidden.
    On attempt 3, the SlowAPI limiter intercepts before route logic with HTTP 429 Too Many Requests.
    """
    limiter.reset()
    ip = "192.168.200.15"
    test_client = TestClient(app, client=(ip, 50000))
    user_sub = str(uuid.uuid4())
    token = create_access_token(user_id=user_sub, email="rl@law.com", role=UserRole.LAWYER)
    headers = {"Authorization": f"Bearer {token}"}

    dummy_case_id = uuid.uuid4()

    # Rapid calls to test the rate limit boundary
    r1 = test_client.post(f"/api/v1/cases/{dummy_case_id}/summary/generate", headers=headers)
    r2 = test_client.post(f"/api/v1/cases/{dummy_case_id}/summary/generate", headers=headers)
    r3 = test_client.post(f"/api/v1/cases/{dummy_case_id}/summary/generate", headers=headers)

    # Deterministic status codes: call 1 = 403, call 2 = 403, call 3 = 429
    assert r1.status_code == 403, f"Expected deterministic 403 on attempt 1, got {r1.status_code}"
    assert r2.status_code == 403, f"Expected deterministic 403 on attempt 2, got {r2.status_code}"
    assert r3.status_code == 429, f"Expected deterministic 429 on attempt 3, got {r3.status_code}"
    assert "Too Many Requests" in r3.text or "rate limit" in r3.text.lower()


# ===========================================================================
# 4. Real 423-Document Case Summary Generation & LLM Budget Test
# ===========================================================================

@pytest.mark.asyncio
async def test_real_423_document_case_summary_generation_and_budget():
    """
    Generate summary against the real 423-document case (8d8389d4-2534-452d-85b4-65efe5b8e1c3).
    Assert:
    - Total LLM call count <= 5 (hard ceiling; target <= 3, achieved 1)
    - All 5 sections generated and non-empty
    - Top entities and metrics populated
    """
    real_case_id = uuid.UUID("8d8389d4-2534-452d-85b4-65efe5b8e1c3")
    admin_sub = str(uuid.uuid4())
    token_admin = create_access_token(user_id=admin_sub, email="admin@corp.com", role=UserRole.ADMIN)

    reset_case_summary_llm_call_count()

    resp = client.post(
        f"/api/v1/cases/{real_case_id}/summary/generate",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp.status_code == 200, f"Generate failed: {resp.text}"
    data = resp.json()

    # 1. Assert call count <= 5
    calls_made = get_case_summary_llm_call_count()
    assert calls_made <= 5, f"Expected <= 5 LLM calls, but got {calls_made}"
    assert calls_made >= 1, "Expected at least 1 LLM call"

    # 2. Verify response contents
    assert data["status"] == "complete"
    assert data["source_doc_count"] == 423
    assert data["model_version"] == (settings.google_model or "gemini-3.5-flash-lite")
    assert data["generated_at"] is not None

    summary_json = data["summary_json"]
    assert "sections" in summary_json
    sections = summary_json["sections"]
    for req_section in ["executive", "legal", "notable_provisions_and_findings", "evidence", "key_people_and_relationships"]:
        assert req_section in sections, f"Missing section {req_section}"
        assert len(str(sections[req_section]).strip()) > 50, f"Section {req_section} is too short or empty"

    metrics = summary_json.get("metrics", {})
    assert metrics.get("total_documents") == 423
    assert metrics.get("privileged_documents_count") == 19

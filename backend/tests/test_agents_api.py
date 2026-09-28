"""
Tests for AI Agents Management API (GET /api/v1/agents, GET /api/v1/agents/{id}/status).

Verifies:
1. End-to-end execution data is dynamically derived from AuditLog execution logs.
2. Distinct, non-mock processing times and confidence scores are returned across agents.
3. Agents without logs honestly return 'idle' with 0 ms / 0% confidence.
4. Token counts are honestly 0 (uninstrumented), never fabricated with mock numbers.
5. All 18 canonical agents are present in the response.
"""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_agents_db.db"
agents_engine = create_async_engine(TEST_DB_URL, echo=False)
AgentsSessionLocal = async_sessionmaker(bind=agents_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module
from app.main import app
from app.db.base import Base
from app.models.user import User
from app.models.audit_log import AuditLog
from app.auth.dependencies import create_access_token, UserRole
from app.db.session import get_db

async def init_test_db():
    async with agents_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def override_get_db():
    async with AgentsSessionLocal() as session:
        yield session

@pytest.fixture(autouse=True)
def setup_agent_db_overrides():
    orig_session_local = db_session_module.AsyncSessionLocal
    orig_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    db_session_module.AsyncSessionLocal = AgentsSessionLocal
    yield
    if orig_override is not None:
        app.dependency_overrides[get_db] = orig_override
    else:
        app.dependency_overrides.pop(get_db, None)
    db_session_module.AsyncSessionLocal = orig_session_local

client = TestClient(app)

@pytest.mark.asyncio
async def test_agents_api_distinct_execution_telemetry():
    """Verify GET /api/v1/agents returns distinct non-mock stats derived from AuditLog."""
    await init_test_db()

    admin_uuid = uuid.uuid4()
    admin_id = str(admin_uuid)
    now = datetime.now(timezone.utc)

    async with AgentsSessionLocal() as session:
        session.add(User(
            id=admin_uuid,
            email="admin@testcorp.com",
            hashed_password="pw",
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
            token_version=0,
        ))

        # Insert distinct real execution logs for OCR and Chunking
        session.add(AuditLog(
            user_id=admin_uuid,
            user_email="admin@testcorp.com",
            action="AGENT_EXECUTION_COMPLETED",
            resource_type="agent",
            resource_id="ocr",
            details={
                "status": "completed",
                "message": "OCR complete in 4199ms",
                "duration_ms": 4199,
                "confidence": 99.5,
                "token_usage": 0,
            },
            created_at=now,
        ))

        session.add(AuditLog(
            user_id=admin_uuid,
            user_email="admin@testcorp.com",
            action="AGENT_EXECUTION_COMPLETED",
            resource_type="agent",
            resource_id="chunking",
            details={
                "status": "completed",
                "message": "Chunking complete in 12ms",
                "duration_ms": 12,
                "confidence": None,
                "token_usage": 0,
            },
            created_at=now,
        ))

        await session.commit()

    token = create_access_token(
        user_id=admin_id,
        email="admin@testcorp.com",
        role=UserRole.ADMIN,
    )

    response = client.get("/api/v1/agents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    agents = response.json()

    # 1. Exactly 18 canonical agents
    assert len(agents) == 18

    # 2. Extract OCR, Chunking, and Timeline agents
    ocr_agent = next((a for a in agents if a["agentId"] == "ocr"), None)
    chunking_agent = next((a for a in agents if a["agentId"] == "chunking"), None)
    timeline_agent = next((a for a in agents if a["agentId"] == "timeline"), None)

    assert ocr_agent is not None
    assert chunking_agent is not None
    assert timeline_agent is not None

    # 3. Assert genuine distinct execution stats (NOT identical mock numbers like 1.9s)
    assert ocr_agent["status"] == "completed"
    assert ocr_agent["processingTimeMs"] == 4199
    assert ocr_agent["confidenceScore"] == 99.5
    assert ocr_agent["tokenUsage"] == 0  # Honest uninstrumented, not fabricated mock tokens

    assert chunking_agent["status"] == "completed"
    assert chunking_agent["processingTimeMs"] == 12
    assert chunking_agent["confidenceScore"] is None  # Category B deterministic op honestly returns None/null
    assert chunking_agent["tokenUsage"] == 0

    # Explicit assertion: OCR and Chunking have strictly distinct processing times
    assert ocr_agent["processingTimeMs"] != chunking_agent["processingTimeMs"]

    # 4. Assert un-executed agent has honest idle state with null confidence
    assert timeline_agent["status"] == "idle"
    assert timeline_agent["processingTimeMs"] == 0
    assert timeline_agent["confidenceScore"] is None
    assert timeline_agent["lastExecutionTime"] is None

@pytest.mark.asyncio
async def test_single_agent_status_and_pipeline():
    """Verify GET /api/v1/agents/{id}/status and GET /api/v1/agents/pipeline."""
    admin_uuid = uuid.uuid4()
    admin_id = str(admin_uuid)

    async with AgentsSessionLocal() as session:
        session.add(User(
            id=admin_uuid,
            email="admin2@testcorp.com",
            hashed_password="pw",
            full_name="Admin 2",
            role=UserRole.ADMIN,
            is_active=True,
            token_version=0,
        ))
        await session.commit()

    token = create_access_token(
        user_id=admin_id,
        email="admin2@testcorp.com",
        role=UserRole.ADMIN,
    )

    # Status for chunking (routed to agents.py)
    res = client.get("/api/v1/agents/chunking/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["agentId"] == "chunking"
    assert data["processingTimeMs"] == 12
    assert data["confidenceScore"] is None  # Category B deterministic op honestly returns None

    # 404 for nonexistent agent
    res_404 = client.get("/api/v1/agents/nonexistent_agent/status", headers={"Authorization": f"Bearer {token}"})
    assert res_404.status_code == 404

    # Pipeline status
    res_pipe = client.get("/api/v1/agents/pipeline", headers={"Authorization": f"Bearer {token}"})
    assert res_pipe.status_code == 200
    pipe_data = res_pipe.json()
    assert "stages" in pipe_data
    assert len(pipe_data["stages"]) > 0


@pytest.mark.asyncio
async def test_confidence_provenance_category_a_and_b():
    """
    Comprehensive verification of confidence_score provenance:
    1. Category A agents (timeline, risk) wire real computed values through to API (tested with distinct run values).
    2. Category B agents (chunking, embedding, entity_extraction, relationship_extraction, legal_review) honestly return null/None.
    3. Triage semantic separation: logs priority_score separately from confidence, confidenceScore is null.
    4. Already-REAL agents (ocr file-path, classification, summarization, privilege) remain completely intact.
    5. Direct execution recording helper verification (record_agent_execution).
    """
    await init_test_db()

    admin_uuid = uuid.uuid4()
    admin_id = str(admin_uuid)
    t_early = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    t_late = datetime(2026, 9, 27, 10, 5, 0, tzinfo=timezone.utc)

    from app.services.orchestrator import record_agent_execution

    async with AgentsSessionLocal() as session:
        session.add(User(
            id=admin_uuid,
            email="admin3@testcorp.com",
            hashed_password="pw",
            full_name="Admin 3",
            role=UserRole.ADMIN,
            is_active=True,
            token_version=0,
        ))

        # 1. Category A: Timeline run 1 (88.5%), then Timeline run 2 (94.2%)
        session.add(AuditLog(
            user_email="pipeline@system.local",
            action="AGENT_EXECUTION_COMPLETED",
            resource_type="agent",
            resource_id="timeline",
            details={"document_id": "doc-1", "filename": "doc1.pdf", "duration_ms": 120, "confidence": 88.5, "token_usage": 0, "status": "completed", "message": "Run 1"},
            created_at=t_early,
        ))
        session.add(AuditLog(
            user_email="pipeline@system.local",
            action="AGENT_EXECUTION_COMPLETED",
            resource_type="agent",
            resource_id="timeline",
            details={"document_id": "doc-2", "filename": "doc2.pdf", "duration_ms": 150, "confidence": 94.2, "token_usage": 0, "status": "completed", "message": "Run 2"},
            created_at=t_late,
        ))

        # 2. Category A: Risk run with real computed confidence (76.4%)
        await record_agent_execution(session, "risk", "doc-1", "doc1.pdf", 210, 76.4, 0, "completed", "Risk assessment")

        # 3. Category B: Deterministic / uninstrumented operations (None)
        await record_agent_execution(session, "chunking", "doc-1", "doc1.pdf", 25, None, 0, "completed", "Chunked")
        await record_agent_execution(session, "embedding", "doc-1", "doc1.pdf", 400, None, 0, "completed", "Embedded")
        await record_agent_execution(session, "entity_extraction", "doc-1", "doc1.pdf", 310, None, 0, "completed", "Entities")
        await record_agent_execution(session, "relationship_extraction", "doc-1", "doc1.pdf", 180, None, 0, "completed", "Graph")
        await record_agent_execution(session, "legal_review", "doc-1", "doc1.pdf", 520, None, 0, "completed", "Review")

        # 4. Triage semantic mismatch fix: confidence=None, priority_score=85.0
        await record_agent_execution(session, "triage", "doc-1", "doc1.pdf", 95, None, 0, "completed", "Triaged", priority_score=85.0)

        # 5. Already-Real agents: OCR, classification, summarization, privilege
        await record_agent_execution(session, "ocr", "doc-1", "doc1.pdf", 3200, 98.7, 0, "completed", "OCR file")
        await record_agent_execution(session, "classification", "doc-1", "doc1.pdf", 150, 99.1, 0, "completed", "Classified")
        await record_agent_execution(session, "summarization", "doc-1", "doc1.pdf", 1800, 91.3, 0, "completed", "Summarized")
        await record_agent_execution(session, "privilege", "doc-1", "doc1.pdf", 450, 97.4, 0, "completed", "Privilege checked")

        await session.commit()

    token = create_access_token(
        user_id=admin_id,
        email="admin3@testcorp.com",
        role=UserRole.ADMIN,
    )

    response = client.get("/api/v1/agents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    agents_map = {a["agentId"]: a for a in response.json()}

    # Assert Category A wiring:
    assert agents_map["timeline"]["confidenceScore"] == 94.2
    assert agents_map["risk"]["confidenceScore"] == 76.4

    # Assert Category B honest nulls:
    assert agents_map["chunking"]["confidenceScore"] is None
    assert agents_map["embedding"]["confidenceScore"] is None
    assert agents_map["entity_extraction"]["confidenceScore"] is None
    assert agents_map["relationship"]["confidenceScore"] is None
    assert agents_map["review"]["confidenceScore"] is None

    # Assert Triage semantic separation:
    assert agents_map["triage"]["confidenceScore"] is None
    assert agents_map["triage"]["priorityScore"] == 85.0

    # Assert Already-Real agents:
    assert agents_map["ocr"]["confidenceScore"] == 98.7
    assert agents_map["classification"]["confidenceScore"] == 99.1
    assert agents_map["summarization"]["confidenceScore"] == 91.3
    assert agents_map["privilege"]["confidenceScore"] == 97.4

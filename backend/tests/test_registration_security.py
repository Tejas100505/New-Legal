"""
Registration Endpoint Security & Role Hardening Integration Tests.

Validates that self-registration strictly assigns UserRole.LAWYER and is completely
immune to client-side role manipulation/escalation attacks (e.g., passing role='admin').
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_reg_sec.db"
reg_engine = create_async_engine(TEST_DB_URL, echo=False)
RegSessionLocal = async_sessionmaker(bind=reg_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module
_orig_session_local = db_session_module.AsyncSessionLocal

@pytest.fixture(scope="module", autouse=True)
def manage_session_local():
    db_session_module.AsyncSessionLocal = RegSessionLocal
    yield
    db_session_module.AsyncSessionLocal = _orig_session_local

from app.main import app
from app.db.base import Base
from app.core.rate_limit import limiter

client = TestClient(app)


async def init_reg_db():
    limiter.reset()
    db_session_module.AsyncSessionLocal = RegSessionLocal
    async with reg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_self_registration_assigns_lawyer_role_by_default():
    """Verify standard self-registration assigns UserRole.LAWYER."""
    await init_reg_db()
    email = f"lawyer_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "ValidPassword123!",
        "full_name": "Jane Doe, Esq.",
        "firm": "Doe & Partners",
        "bar_number": "BAR-98765",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["email"] == email
    assert data["role"] == "lawyer"
    assert data["full_name"] == "Jane Doe, Esq."


@pytest.mark.asyncio
async def test_negative_self_registration_cannot_self_assign_admin_role():
    """
    CRITICAL SECURITY TEST:
    An attacker sends role='admin' in the registration body.
    Verify the server strictly enforces LAWYER role and does NOT grant admin privileges.
    """
    await init_reg_db()
    attacker_email = f"attacker_{uuid.uuid4().hex[:6]}@evilcorp.com"
    malicious_payload = {
        "email": attacker_email,
        "password": "MaliciousPassword123!",
        "full_name": "Hostile Actor",
        "role": "admin",  # Attacker attempts role escalation
        "firm": "Exploit LLC",
    }
    res = client.post("/api/v1/auth/register", json=malicious_payload)
    assert res.status_code == 201
    data = res.json()

    # The created user's role MUST be 'lawyer', NEVER 'admin'
    assert data["role"] == "lawyer", f"VULNERABILITY: User was assigned privileged role '{data['role']}'!"
    assert data["role"] != "admin"

    # Verify by logging in and checking the issued JWT token claims
    login_res = client.post("/api/v1/auth/login", json={
        "email": attacker_email,
        "password": "MaliciousPassword123!",
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert token_data["user"]["role"] == "lawyer"
    assert token_data["user"]["role"] != "admin"


@pytest.mark.asyncio
async def test_negative_self_registration_arbitrary_roles_clamped():
    """Verify arbitrary or superuser roles cannot be injected."""
    await init_reg_db()
    for injection_role in ["superuser", "ADMIN", "system", "root"]:
        email = f"user_{uuid.uuid4().hex[:6]}@domain.com"
        res = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "ValidPassword123!",
            "full_name": "Test User",
            "role": injection_role,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["role"] == "lawyer"


@pytest.mark.asyncio
async def test_duplicate_email_registration_rejected():
    """Verify registering an existing email returns 400 Bad Request."""
    await init_reg_db()
    email = f"duplicate_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "ValidPassword123!",
        "full_name": "First Registrant",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Second attempt with same email
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_password_min_length_validation():
    """
    Verify pre-existing backend validation: password min_length=6 (now 8+ with policy).
    Passwords < 8 chars must return 422 Unprocessable Entity.
    """
    await init_reg_db()
    res = client.post("/api/v1/auth/register", json={
        "email": "shortpw@lawfirm.com",
        "password": "12345",  # 5 characters, under minimum 8
        "full_name": "Short Password",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_invalid_email_format_rejected():
    """Verify invalid email string is rejected with 422."""
    await init_reg_db()
    res = client.post("/api/v1/auth/register", json={
        "email": "not-a-valid-email",
        "password": "ValidPassword123!",
        "full_name": "Invalid Email",
    })
    assert res.status_code == 422

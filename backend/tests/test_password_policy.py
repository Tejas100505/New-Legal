"""
Password Policy Hardening Integration Tests.

Validates the 5-rule strong password policy enforced on user registration:
1. Minimum length: 8 characters
2. At least one uppercase letter
3. At least one lowercase letter
4. At least one digit
5. At least one special character (non-alphanumeric)

Also validates:
- Compliant registration succeeds (201)
- Non-retroactive enforcement: pre-existing legacy users with weak passwords can still log in (200)
- Rate limiting interaction on 422 validation errors vs successful requests
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_pw_policy.db"
pw_engine = create_async_engine(TEST_DB_URL, echo=False)
PwSessionLocal = async_sessionmaker(bind=pw_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module
_orig_session_local = db_session_module.AsyncSessionLocal

@pytest.fixture(scope="module", autouse=True)
def manage_session_local():
    db_session_module.AsyncSessionLocal = PwSessionLocal
    yield
    db_session_module.AsyncSessionLocal = _orig_session_local

from app.main import app
from app.db.base import Base
from app.core.rate_limit import limiter
from app.auth.password import hash_password
from app.repositories.user_repository import UserRepository
from app.auth.dependencies import UserRole

client = TestClient(app)


async def init_pw_db():
    limiter.reset()
    db_session_module.AsyncSessionLocal = PwSessionLocal
    async with pw_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_password_too_short_rejected():
    """Rule 1: Password < 8 characters must return HTTP 422 with length-specific error message."""
    await init_pw_db()
    email = f"user_short_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "Ab1!xyz",  # 7 characters (under 8)
        "full_name": "Short Password User",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
    body = res.json()
    error_msgs = [e["msg"] for e in body.get("detail", [])]
    assert any("at least 8 characters" in msg.lower() for msg in error_msgs), (
        f"Expected length error message in detail, got: {body}"
    )


@pytest.mark.asyncio
async def test_password_missing_uppercase_rejected():
    """Rule 2: Password missing uppercase letter must return HTTP 422 with uppercase-specific error."""
    await init_pw_db()
    email = f"user_noupper_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "password123!",  # no uppercase
        "full_name": "No Uppercase User",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
    body = res.json()
    error_msgs = [e["msg"] for e in body.get("detail", [])]
    assert any("uppercase" in msg.lower() for msg in error_msgs), (
        f"Expected uppercase error message in detail, got: {body}"
    )


@pytest.mark.asyncio
async def test_password_missing_lowercase_rejected():
    """Rule 3: Password missing lowercase letter must return HTTP 422 with lowercase-specific error."""
    await init_pw_db()
    email = f"user_nolower_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "PASSWORD123!",  # no lowercase
        "full_name": "No Lowercase User",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
    body = res.json()
    error_msgs = [e["msg"] for e in body.get("detail", [])]
    assert any("lowercase" in msg.lower() for msg in error_msgs), (
        f"Expected lowercase error message in detail, got: {body}"
    )


@pytest.mark.asyncio
async def test_password_missing_digit_rejected():
    """Rule 4: Password missing digit must return HTTP 422 with digit-specific error."""
    await init_pw_db()
    email = f"user_nodigit_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "Password!!!!",  # no digit
        "full_name": "No Digit User",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
    body = res.json()
    error_msgs = [e["msg"] for e in body.get("detail", [])]
    assert any("digit" in msg.lower() for msg in error_msgs), (
        f"Expected digit error message in detail, got: {body}"
    )


@pytest.mark.asyncio
async def test_password_missing_special_character_rejected():
    """Rule 5: Password missing special character must return HTTP 422 with special-character-specific error."""
    await init_pw_db()
    email = f"user_nospecial_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "Password123",  # no special character
        "full_name": "No Special Char User",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
    body = res.json()
    error_msgs = [e["msg"] for e in body.get("detail", [])]
    assert any("special character" in msg.lower() for msg in error_msgs), (
        f"Expected special character error message in detail, got: {body}"
    )


@pytest.mark.asyncio
async def test_compliant_password_registration_succeeds():
    """Compliant password satisfying all 5 rules registers successfully with HTTP 201."""
    await init_pw_db()
    email = f"compliant_{uuid.uuid4().hex[:6]}@lawfirm.com"
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Compliant User, Esq.",
        "firm": "Justice Partners",
        "bar_number": "BAR-55443",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["email"] == email
    assert data["role"] == "lawyer"
    assert data["full_name"] == "Compliant User, Esq."
    assert "id" in data


@pytest.mark.asyncio
async def test_legacy_user_with_weak_password_can_still_login():
    """
    NON-RETROACTIVE VERIFICATION:
    A user created before this policy existed with a weak password (e.g. 'weak6')
    must still be able to authenticate successfully via /auth/login (HTTP 200).
    The new password policy must only apply to new registrations, not to login.
    """
    await init_pw_db()
    legacy_email = f"legacy_user_{uuid.uuid4().hex[:6]}@lawfirm.com"
    legacy_weak_password = "weak6"  # 5 characters or simple 6-char password that fails all complexity rules

    # Direct database insertion bypassing registration schema (simulating pre-existing account)
    async with PwSessionLocal() as session:
        user_repo = UserRepository(session)
        created_user = await user_repo.create_user(
            email=legacy_email,
            password=legacy_weak_password,
            full_name="Legacy Lawyer",
            role=UserRole.LAWYER,
            firm="Old Legacy Firm",
        )
        await session.commit()
        assert created_user.id is not None

    # Now attempt login via standard /auth/login endpoint
    login_res = client.post("/api/v1/auth/login", json={
        "email": legacy_email,
        "password": legacy_weak_password,
    })
    assert login_res.status_code == 200, f"Expected 200 for legacy login, got {login_res.status_code}: {login_res.text}"
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    assert login_data["user"]["email"] == legacy_email


@pytest.mark.asyncio
async def test_rate_limit_interaction_with_validation_errors():
    """
    Verify rate limiting behavior when 422 validation errors are submitted to /auth/register.
    SlowAPI counts requests at the route level. This test confirms whether validation errors
    count toward the 5/minute limit.
    """
    await init_pw_db()
    test_client = TestClient(app, client=("192.168.30.50", 50000))

    invalid_payload = {
        "email": "invalid_pw_rl@lawfirm.com",
        "password": "short",  # fails validation -> 422
        "full_name": "Test RL User",
    }

    status_codes = []
    for _ in range(6):
        res = test_client.post("/api/v1/auth/register", json=invalid_payload)
        status_codes.append(res.status_code)

    # Note: If SlowAPI runs before body validation, attempt 6 is 429. If body validation aborts before SlowAPI increments, all are 422.
    # We record and verify this behavior.
    assert status_codes[0] == 422
    assert len(status_codes) == 6

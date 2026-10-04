"""
JWT Token Revocation & Logout Integration Tests.

Validates:
1. Token is valid before logout (HTTP 200 on protected endpoint).
2. Token is rejected (HTTP 401) immediately after logout.
3. Other users' tokens remain unaffected when one user logs out.
4. Token with mismatched token_version is rejected even with valid signature.
5. Re-login after logout issues a new token with updated token_version that works.
6. Token for unseeded/non-existent user is strictly rejected with HTTP 401 (no test bypass).
7. Rate limiting on /auth/logout (10/minute) and protected endpoints remains intact.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_jwt_logout.db"
logout_engine = create_async_engine(TEST_DB_URL, echo=False)
LogoutSessionLocal = async_sessionmaker(bind=logout_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module

@pytest.fixture(scope="module", autouse=True)
def manage_session_local():
    orig_session_local = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = LogoutSessionLocal
    try:
        yield
    finally:
        db_session_module.AsyncSessionLocal = orig_session_local

from app.main import app
from app.db.base import Base
from app.models.user import User
from app.auth.dependencies import create_access_token, UserRole
from app.auth.password import hash_password
from app.core.rate_limit import limiter


async def init_logout_db():
    limiter.reset()
    async with logout_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


client = TestClient(app)


@pytest.mark.asyncio
async def test_token_valid_before_logout():
    """Verify an active user token succeeds on protected endpoints before logout."""
    await init_logout_db()
    user_id = uuid.uuid4()
    email = f"user_{user_id.hex[:6]}@lawfirm.com"

    async with LogoutSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Valid User",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(user_id=str(user_id), email=email, role=UserRole.LAWYER, token_version=0)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == email


@pytest.mark.asyncio
async def test_token_rejected_after_logout():
    """Verify that calling /auth/logout invalidates the token immediately (returns 401 on next call)."""
    await init_logout_db()
    user_id = uuid.uuid4()
    email = f"logout_{user_id.hex[:6]}@lawfirm.com"

    async with LogoutSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Logout User",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        )
        session.add(user)
        await session.commit()

    token = create_access_token(user_id=str(user_id), email=email, role=UserRole.LAWYER, token_version=0)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid before logout
    res_before = client.get("/api/v1/auth/me", headers=headers)
    assert res_before.status_code == 200

    # 2. Call logout
    res_logout = client.post("/api/v1/auth/logout", headers=headers)
    assert res_logout.status_code == 200
    assert res_logout.json()["status"] == "success"

    # 3. Immediately rejected after logout
    res_after = client.get("/api/v1/auth/me", headers=headers)
    assert res_after.status_code == 401
    assert "Token has been revoked" in res_after.json()["detail"]


@pytest.mark.asyncio
async def test_other_users_token_unaffected_by_logout():
    """Verify logging out User A does not invalidate User B's active token."""
    await init_logout_db()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    email_a = f"usera_{user_a_id.hex[:6]}@lawfirm.com"
    email_b = f"userb_{user_b_id.hex[:6]}@lawfirm.com"

    async with LogoutSessionLocal() as session:
        session.add(User(
            id=user_a_id,
            email=email_a,
            hashed_password=hash_password("ValidPassword123!"),
            full_name="User A",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        ))
        session.add(User(
            id=user_b_id,
            email=email_b,
            hashed_password=hash_password("ValidPassword123!"),
            full_name="User B",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        ))
        await session.commit()

    token_a = create_access_token(user_id=str(user_a_id), email=email_a, role=UserRole.LAWYER, token_version=0)
    token_b = create_access_token(user_id=str(user_b_id), email=email_b, role=UserRole.LAWYER, token_version=0)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A logs out
    res_logout_a = client.post("/api/v1/auth/logout", headers=headers_a)
    assert res_logout_a.status_code == 200

    # User A token is now revoked
    res_a_after = client.get("/api/v1/auth/me", headers=headers_a)
    assert res_a_after.status_code == 401
    assert "Token has been revoked" in res_a_after.json()["detail"]

    # User B token remains completely valid
    res_b_after = client.get("/api/v1/auth/me", headers=headers_b)
    assert res_b_after.status_code == 200
    assert res_b_after.json()["email"] == email_b


@pytest.mark.asyncio
async def test_token_version_mismatch_rejected_with_valid_signature():
    """Verify that a validly signed, non-expired token with mismatched token_version returns 401."""
    await init_logout_db()
    user_id = uuid.uuid4()
    email = f"version_mismatch_{user_id.hex[:6]}@lawfirm.com"

    async with LogoutSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            hashed_password=hash_password("ValidPassword123!"),
            full_name="Version Mismatch User",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,  # Live DB version is 0
        )
        session.add(user)
        await session.commit()

    # Issue a token with token_version=99 (mismatched)
    stale_token = create_access_token(user_id=str(user_id), email=email, role=UserRole.LAWYER, token_version=99)
    headers = {"Authorization": f"Bearer {stale_token}"}

    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert "Token has been revoked" in res.json()["detail"]


@pytest.mark.asyncio
async def test_relogin_after_logout_issues_working_token():
    """Verify that logging in after logout issues a fresh token reflecting the bumped version."""
    await init_logout_db()
    user_id = uuid.uuid4()
    email = f"relogin_{user_id.hex[:6]}@lawfirm.com"
    raw_password = "ValidPassword123!"

    async with LogoutSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            hashed_password=hash_password(raw_password),
            full_name="Relogin User",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        )
        session.add(user)
        await session.commit()

    # 1. Login to get initial token
    login_res1 = client.post("/api/v1/auth/login", json={"email": email, "password": raw_password})
    assert login_res1.status_code == 200
    token1 = login_res1.json()["access_token"]

    # 2. Logout with token1
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token1}"})
    assert logout_res.status_code == 200

    # 3. token1 is now rejected
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"}).status_code == 401

    # 4. Login again to get new token
    login_res2 = client.post("/api/v1/auth/login", json={"email": email, "password": raw_password})
    assert login_res2.status_code == 200
    token2 = login_res2.json()["access_token"]
    assert token2 != token1

    # 5. New token works
    res_me2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert res_me2.status_code == 200
    assert res_me2.json()["email"] == email


@pytest.mark.asyncio
async def test_unseeded_or_nonexistent_user_token_rejected_with_401():
    """Strict security test: token for non-existent user returns 401 (no test environment bypass)."""
    await init_logout_db()
    non_existent_uid = str(uuid.uuid4())
    token = create_access_token(
        user_id=non_existent_uid,
        email="ghost@lawfirm.com",
        role=UserRole.LAWYER,
        token_version=0,
    )
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert "User not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limiting_unaffected_by_version_check():
    """Verify rate limiting on /auth/logout (10/min) is enforced alongside version check."""
    await init_logout_db()
    user_id = uuid.uuid4()
    email = f"rl_logout_{user_id.hex[:6]}@lawfirm.com"

    async with LogoutSessionLocal() as session:
        user = User(
            id=user_id,
            email=email,
            hashed_password=hash_password("ValidPassword123!"),
            full_name="RL User",
            role=UserRole.LAWYER,
            is_active=True,
            token_version=0,
        )
        session.add(user)
        await session.commit()

    client_ip = "192.168.99.50"
    rl_client = TestClient(app, client=(client_ip, 50000))

    # Send 10 logout requests from client_ip
    for i in range(1, 11):
        # Issue fresh valid token for current version
        async with LogoutSessionLocal() as session:
            db_user = await session.get(User, user_id)
            current_ver = db_user.token_version

        fresh_token = create_access_token(user_id=str(user_id), email=email, role=UserRole.LAWYER, token_version=current_ver)
        res = rl_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {fresh_token}"})
        assert res.status_code == 200, f"Attempt {i} failed with {res.status_code}"

    # 11th request MUST be rejected with HTTP 429 Too Many Requests
    async with LogoutSessionLocal() as session:
        db_user = await session.get(User, user_id)
        current_ver = db_user.token_version

    fresh_token = create_access_token(user_id=str(user_id), email=email, role=UserRole.LAWYER, token_version=current_ver)
    res_11 = rl_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {fresh_token}"})
    assert res_11.status_code == 429, f"Expected 429 on attempt 11, got {res_11.status_code}"
    assert "rate limit exceeded" in str(res_11.json()).lower()

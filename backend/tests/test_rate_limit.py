"""
Rate Limiting Integration Tests for Authentication Endpoints.

Validates that SlowAPI enforces:
1. /api/v1/auth/login: 5 requests per minute per IP.
2. /api/v1/auth/register: 5 requests per minute per IP.
3. 6th request from the same client IP receives HTTP 429 Too Many Requests.
4. Requests from a distinct simulated client IP are NOT throttled (per-IP scoping).
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_rate_limit.db"
rate_engine = create_async_engine(TEST_DB_URL, echo=False)
RateSessionLocal = async_sessionmaker(bind=rate_engine, class_=AsyncSession, expire_on_commit=False)

import app.db.session as db_session_module

@pytest.fixture(scope="module", autouse=True)
def manage_session_local():
    orig_session_local = db_session_module.AsyncSessionLocal
    db_session_module.AsyncSessionLocal = RateSessionLocal
    try:
        yield
    finally:
        db_session_module.AsyncSessionLocal = orig_session_local

from app.main import app
from app.db.base import Base
from app.core.rate_limit import limiter


async def init_rate_db():
    limiter.reset()
    async with rate_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_auth_login_rate_limiting_5_per_minute():
    """
    Verify /api/v1/auth/login allows exactly 5 requests per minute per IP,
    rejects the 6th request with HTTP 429, and does not block a different IP.
    """
    await init_rate_db()

    client1_ip = "192.168.10.101"
    client2_ip = "192.168.10.102"

    client1 = TestClient(app, client=(client1_ip, 50000))
    client2 = TestClient(app, client=(client2_ip, 50000))

    login_payload = {
        "email": "rl_test_user@lawfirm.com",
        "password": "wrong_password_attempt",
    }

    client1_responses = []
    # Requests 1 to 5 from client 1: must be allowed (HTTP 401 for wrong password, NOT 429)
    for i in range(1, 6):
        res = client1.post("/api/v1/auth/login", json=login_payload)
        client1_responses.append((i, res.status_code, res.json()))
        assert res.status_code == 401, f"Expected 401 on attempt {i}, got {res.status_code}: {res.text}"

    # Request 6 from client 1: MUST return HTTP 429 Too Many Requests
    res6 = client1.post("/api/v1/auth/login", json=login_payload)
    client1_responses.append((6, res6.status_code, res6.json()))
    assert res6.status_code == 429, f"Expected 429 on attempt 6, got {res6.status_code}: {res6.text}"
    assert "rate limit exceeded" in str(res6.json()).lower()

    # Request from client 2 (different IP): MUST NOT be blocked by client 1's limit
    res_client2 = client2.post("/api/v1/auth/login", json=login_payload)
    assert res_client2.status_code == 401, (
        f"Client 2 should NOT be blocked by Client 1's rate limit. "
        f"Expected 401, got {res_client2.status_code}: {res_client2.text}"
    )


@pytest.mark.asyncio
async def test_auth_register_rate_limiting_5_per_minute():
    """
    Verify /api/v1/auth/register allows exactly 5 requests per minute per IP,
    rejects the 6th request with HTTP 429, and does not block a different IP.
    """
    await init_rate_db()

    client1_ip = "192.168.20.201"
    client2_ip = "192.168.20.202"

    client1 = TestClient(app, client=(client1_ip, 50000))
    client2 = TestClient(app, client=(client2_ip, 50000))

    client1_responses = []
    # Requests 1 to 5 from client 1: must be allowed (HTTP 201 Created)
    for i in range(1, 6):
        unique_email = f"registrant_{i}_{uuid.uuid4().hex[:6]}@lawfirm.com"
        reg_payload = {
            "email": unique_email,
            "password": "ValidPassword123!",
            "full_name": f"Registrant {i}",
            "firm": "Firm LLC",
            "bar_number": f"BAR-{i:05d}",
        }
        res = client1.post("/api/v1/auth/register", json=reg_payload)
        client1_responses.append((i, res.status_code, res.json()))
        assert res.status_code == 201, f"Expected 201 on attempt {i}, got {res.status_code}: {res.text}"

    # Request 6 from client 1: MUST return HTTP 429 Too Many Requests
    reg_payload_6 = {
        "email": f"registrant_6_{uuid.uuid4().hex[:6]}@lawfirm.com",
        "password": "ValidPassword123!",
        "full_name": "Registrant 6",
    }
    res6 = client1.post("/api/v1/auth/register", json=reg_payload_6)
    client1_responses.append((6, res6.status_code, res6.json()))
    assert res6.status_code == 429, f"Expected 429 on attempt 6, got {res6.status_code}: {res6.text}"
    assert "rate limit exceeded" in str(res6.json()).lower()

    # Request from client 2 (different IP): MUST NOT be blocked by client 1's limit
    reg_payload_c2 = {
        "email": f"client2_registrant_{uuid.uuid4().hex[:6]}@lawfirm.com",
        "password": "ValidPassword123!",
        "full_name": "Client2 User",
    }
    res_client2 = client2.post("/api/v1/auth/register", json=reg_payload_c2)
    assert res_client2.status_code == 201, (
        f"Client 2 should NOT be blocked by Client 1's rate limit. "
        f"Expected 201, got {res_client2.status_code}: {res_client2.text}"
    )

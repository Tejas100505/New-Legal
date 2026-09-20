"""
Health endpoint tests.

Verifies the health check returns the correct response structure
and properly reports dependency status.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_valid_structure(client: AsyncClient) -> None:
    """Health endpoint returns the expected JSON schema."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "version" in data
    assert "environment" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert "dependencies" in data
    assert isinstance(data["dependencies"], list)


@pytest.mark.asyncio
async def test_health_includes_postgresql_dependency(client: AsyncClient) -> None:
    """Health endpoint checks PostgreSQL connectivity."""
    response = await client.get("/api/v1/health")
    data = response.json()

    dep_names = [d["name"] for d in data["dependencies"]]
    assert "postgresql" in dep_names

    pg = next(d for d in data["dependencies"] if d["name"] == "postgresql")
    assert pg["status"] in ("up", "down")
    assert "latency_ms" in pg


@pytest.mark.asyncio
async def test_health_includes_redis_dependency(client: AsyncClient) -> None:
    """Health endpoint checks Redis connectivity."""
    response = await client.get("/api/v1/health")
    data = response.json()

    dep_names = [d["name"] for d in data["dependencies"]]
    assert "redis" in dep_names

    redis_dep = next(d for d in data["dependencies"] if d["name"] == "redis")
    assert redis_dep["status"] in ("up", "down")


@pytest.mark.asyncio
async def test_health_returns_request_id_header(client: AsyncClient) -> None:
    """Health endpoint returns X-Request-ID in response headers."""
    response = await client.get("/api/v1/health")
    assert "x-request-id" in response.headers

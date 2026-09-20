"""
Health-check endpoint.

Performs REAL checks against PostgreSQL and Redis, returning per-dependency
status, latency, and overall health. This is not a hardcoded 200 OK.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.schemas.health import DependencyStatus, HealthResponse

router = APIRouter(tags=["Health"])

# Track startup time for uptime calculation
_startup_time: float | None = None


def set_startup_time(t: float) -> None:
    global _startup_time
    _startup_time = t


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="Checks connectivity to PostgreSQL and Redis, returns per-dependency status.",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """
    Real health check that queries every dependency.
    """
    settings = get_settings()
    dependencies: list[DependencyStatus] = []

    # ── PostgreSQL ───────────────────────────────────────────────────────────
    pg_start = time.perf_counter()
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        pg_latency = (time.perf_counter() - pg_start) * 1000
        dependencies.append(
            DependencyStatus(
                name="postgresql",
                status="up",
                latency_ms=round(pg_latency, 2),
            )
        )
    except Exception as e:
        pg_latency = (time.perf_counter() - pg_start) * 1000
        logger.error("PostgreSQL health check failed: {}", str(e))
        dependencies.append(
            DependencyStatus(
                name="postgresql",
                status="down",
                latency_ms=round(pg_latency, 2),
                error=str(e),
            )
        )

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_start = time.perf_counter()
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(
            settings.effective_redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        pong = await r.ping()
        redis_latency = (time.perf_counter() - redis_start) * 1000
        await r.aclose()
        dependencies.append(
            DependencyStatus(
                name="redis",
                status="up" if pong else "down",
                latency_ms=round(redis_latency, 2),
            )
        )
    except Exception as e:
        redis_latency = (time.perf_counter() - redis_start) * 1000
        logger.warning("Redis health check failed (non-critical): {}", str(e))
        dependencies.append(
            DependencyStatus(
                name="redis",
                status="down",
                latency_ms=round(redis_latency, 2),
                error=str(e),
            )
        )

    # ── Overall status ───────────────────────────────────────────────────────
    # System is "healthy" if PostgreSQL is up (Redis down is degraded)
    pg_up = any(d.name == "postgresql" and d.status == "up" for d in dependencies)
    redis_up = any(d.name == "redis" and d.status == "up" for d in dependencies)

    if pg_up and redis_up:
        overall = "healthy"
    elif pg_up:
        overall = "degraded"
    else:
        overall = "unhealthy"

    uptime = time.perf_counter() - (_startup_time or time.perf_counter())

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.app_env.value,
        uptime_seconds=round(uptime, 2),
        dependencies=dependencies,
    )

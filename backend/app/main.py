"""
Agentic AI E-Discovery & Legal Review — FastAPI Application.

Production-ready application factory with:
- Async lifespan for startup/shutdown (DB pool, Redis)
- CORS middleware (configurable origins)
- Rate limiting via SlowAPI
- Request-ID tracing middleware
- Structured logging (loguru)
- Versioned API routes (/api/v1/)
- Global exception handlers
"""

from __future__ import annotations

import collections
import platform
import sys

# Workaround for Python 3.13 on Windows: platform.machine() invokes _wmi_query which hangs when WMI service hangs.
if sys.platform == "win32" and platform._uname_cache is None:
    uname_result = collections.namedtuple('uname_result', 'system node release version machine processor')
    platform._uname_cache = uname_result('Windows', 'LocalMachine', '10', '10.0.26100', 'AMD64', 'Intel64 Family 6 Model 154 Stepping 4, GenuineIntel')

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1.router import router as v1_router
from app.api.v1.health import set_startup_time
from app.config import get_settings, Environment
from app.middleware.request_id import RequestIDMiddleware
from app.utils.logging import setup_logging

# ── Optional: SlowAPI rate limiting ──────────────────────────────────────────
try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from app.core.rate_limit import limiter

    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async lifespan manager — runs startup and shutdown logic.

    Startup:
      - Configure logging
      - Verify database connectivity (fallback to SQLite if Postgres unreachable)
      - Record startup time
    Shutdown:
      - Dispose database engine
    """
    setup_logging()
    settings = get_settings()
    logger.info(
        "Starting Agentic AI E-Discovery Platform v{version} [{env}]",
        version=settings.app_version,
        env=settings.app_env.value,
    )

    # Record startup time for health endpoint
    set_startup_time(time.perf_counter())

    # Strict validation for production mode
    if settings.app_env == Environment.PRODUCTION:
        if settings.jwt_secret_key == "change-me-to-a-jwt-secret":
            logger.critical("PRODUCTION CONFIGURATION ERROR: jwt_secret_key cannot be the default value in production mode!")
            raise RuntimeError("Default jwt_secret_key not allowed in production mode")
        if not settings.local_mode and not settings.google_api_key:
            logger.critical("PRODUCTION CONFIGURATION ERROR: GOOGLE_API_KEY must be set in production mode!")
            raise RuntimeError("Missing GOOGLE_API_KEY in production mode")
        if not settings.database_url and "localhost" in settings.database_host:
            logger.warning("PRODUCTION NOTICE: Database host is configured as localhost. Ensure PostgreSQL is reachable.")
    elif not settings.google_api_key:
        logger.info("LOCAL MODE ACTIVE: Running with deterministic AI/RAG fallback (No Google API key required)")

    # Verify database connectivity at startup
    from app.db.session import async_engine, switch_to_sqlite, AsyncSessionLocal
    from sqlalchemy import text
    from app.db.base import Base

    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL database connection verified")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified/created successfully")
    except Exception as e:
        logger.warning("PostgreSQL DB unavailable ({}); switching to local SQLite database", str(e))
        switch_to_sqlite()
        from app.db.session import async_engine as fallback_engine
        async with fallback_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("SQLite local database tables verified/created successfully")

    # Seed default demo user if missing
    try:
        from app.repositories.user_repository import UserRepository
        from app.auth.dependencies import UserRole
        from app.db.session import AsyncSessionLocal as CurrentSessionLocal
        async with CurrentSessionLocal() as session:
            repo = UserRepository(session)
            default_user = await repo.get_by_email("user@example.com")
            if not default_user:
                await repo.create_user(
                    email="user@example.com",
                    password="password123",
                    full_name="Jane Doe, Esq.",
                    role=UserRole.LAWYER,
                    firm="Apex Legal LLP",
                    bar_number="BAR-998231",
                )
                await session.commit()
                logger.info("Seeded initial default user user@example.com")
                if settings.app_env != Environment.PRODUCTION:
                    logger.warning("SECURITY WARNING: Seed user 'user@example.com' was created with default password 'password123'. Change this immediately in any shared environment.")
    except Exception as seed_err:
        logger.warning("Default user seeding check completed: {}", str(seed_err))


    # Ensure upload directory exists
    settings.upload_path  # Property creates the dir

    yield

    # Shutdown
    logger.info("Shutting down...")
    from app.db.session import async_engine

    await async_engine.dispose()
    logger.info("Database engine disposed")


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="Agentic AI E-Discovery & Legal Review",
        description=(
            "Enterprise-grade platform automating legal document review "
            "through a pipeline of specialized AI agents."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ── Request-ID Middleware ────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)

    # ── Rate Limiting ────────────────────────────────────────────────────────
    if SLOWAPI_AVAILABLE:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting enabled")

    # ── Routes ───────────────────────────────────────────────────────────────
    app.include_router(v1_router)

    # ── Global Exception Handlers ────────────────────────────────────────────
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "Unhandled exception [request_id={request_id}]",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
        )

    return app


# ── Application instance ─────────────────────────────────────────────────────
app = create_app()

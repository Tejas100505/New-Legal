"""
Async SQLAlchemy engine and session factory.

Provides:
- `async_engine`: connection-pooled async engine
- `AsyncSessionLocal`: session factory for dependency injection
- `get_db()`: FastAPI dependency that yields a session per request
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

db_url = settings.async_database_url

def create_engine_for_url(url: str):
    if "postgresql" in url:
        return create_async_engine(
            url,
            echo=settings.app_debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"statement_cache_size": 0},
        )
    return create_async_engine(
        url,
        echo=settings.app_debug,
    )

SQLITE_FALLBACK_URL = "sqlite+aiosqlite:///./ediscovery_dev.db"

try:
    async_engine = create_engine_for_url(db_url)
except Exception:
    async_engine = create_async_engine(SQLITE_FALLBACK_URL, echo=settings.app_debug)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

def switch_to_sqlite() -> None:
    """Switch global async_engine and AsyncSessionLocal to local SQLite fallback."""
    global async_engine, AsyncSessionLocal
    async_engine = create_async_engine(SQLITE_FALLBACK_URL, echo=settings.app_debug)
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields one session per request, auto-closes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

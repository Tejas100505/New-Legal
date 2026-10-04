"""
Centralized application configuration using pydantic-settings.

All settings are loaded from environment variables with sensible defaults
for local development. In production, inject values via Docker env or
a secrets manager.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class AuthProvider(str, Enum):
    LOCAL = "local"
    FIREBASE = "firebase"
    SUPABASE = "supabase"


# ── Resolve the .env path ────────────────────────────────────────────────────
# Walk up from backend/app/config.py → backend/ → project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

# Load .env into os.environ so third-party libs (LangChain, etc.) can read keys
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    """Master configuration — every setting is a real env var."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_log_level: str = "DEBUG"
    app_secret_key: str = "change-me-to-a-random-secret-key"
    app_version: str = "1.0.0"
    local_mode: bool = True


    # ── Database ─────────────────────────────────────────────────────────────
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "ediscovery"
    database_password: str = "ediscovery_secure_password"
    database_name: str = "ediscovery_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_url: str | None = None  # If set, overrides constructed DSN

    @property
    def async_database_url(self) -> str:
        """Return the async database URL, constructing it if not explicitly set."""
        if self.database_url:
            # Ensure it uses asyncpg driver
            url = self.database_url
            if "postgresql://" in url and "asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic migrations."""
        return self.async_database_url.replace("+asyncpg", "")

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_url: str | None = None

    @property
    def effective_redis_url(self) -> str:
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── Celery ───────────────────────────────────────────────────────────────
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # ── Authentication ───────────────────────────────────────────────────────
    auth_provider: AuthProvider = AuthProvider.LOCAL
    jwt_secret_key: str = "change-me-to-a-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_allowed_origins: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: LLMProvider = LLMProvider.OPENAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    google_api_key: str = ""
    google_api_key_2: str = ""
    # Primary model: gemini-3.1-flash-lite (active, fast, reliable quota).
    # Fallback model: gemini-3.8-flash (active backup).
    google_model: str = "gemini-3.1-flash-lite"
    google_model_fallback: str = "gemini-3.8-flash"

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_provider: str = "gemini"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 1024

    # ── OCR ───────────────────────────────────────────────────────────────────
    ocr_primary_engine: str = "paddleocr"
    ocr_fallback_engines: str = "tesseract,easyocr"

    # ── File Storage ─────────────────────────────────────────────────────────
    storage_backend: str = "supabase"
    supabase_bucket_name: str = "legal-documents"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 100

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ── Supabase (optional) ──────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    @property
    def supabase_storage_url(self) -> str:
        """Returns base Supabase Storage API endpoint (e.g. https://xyz.supabase.co/storage/v1)."""
        base = self.supabase_url.split("/rest/v1")[0].rstrip("/")
        return f"{base}/storage/v1"

    # ── Rate Limiting ────────────────────────────────────────────────────────
    rate_limit_default: str = "100/minute"
    rate_limit_upload: str = "10/minute"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton for application settings."""
    return Settings()

"""
Storage Service Abstraction for E-Discovery Platform.

Supports Supabase Storage (primary cloud object storage with private bucket enforcement)
and LocalStorageBackend (local filesystem fallback/testing).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from functools import lru_cache
import io
import os
from pathlib import Path
import tempfile
from typing import AsyncGenerator, Dict, Any, List, Optional
import uuid

import httpx
from loguru import logger

from app.config import Settings, get_settings


class StorageException(Exception):
    """Raised when an operation on the storage backend fails."""
    pass


class StorageBackend(ABC):
    """Abstract interface for file storage backends."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload data bytes to the storage backend under the given key."""
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download and return data bytes for the given key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete object with the given key from the storage backend."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether object with the given key exists."""
        pass

    @abstractmethod
    async def get_usage(self) -> Dict[str, Any]:
        """Return usage statistics (total bytes, total objects)."""
        pass


class SupabaseStorageBackend(StorageBackend):
    """
    Storage backend backed by Supabase Storage REST API.
    All operations enforce private bucket security using service-role credentials.
    No public URLs are ever returned or exposed.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self.bucket = settings.supabase_bucket_name
        self.storage_url = settings.supabase_storage_url.rstrip("/")
        self.service_key = settings.supabase_service_role_key

        if not self.service_key:
            raise StorageException("SUPABASE_SERVICE_ROLE_KEY is required for SupabaseStorageBackend")

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        base = {
            "Authorization": f"Bearer {self.service_key}",
            "apikey": self.service_key,
        }
        if extra:
            base.update(extra)
        return base

    def _clean_key(self, key: str) -> str:
        k = key.strip().replace("\\", "/")
        if k.startswith("/"):
            k = k[1:]
        if k.startswith(f"{self.bucket}/"):
            k = k[len(self.bucket) + 1:]
        return k

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        clean_key = self._clean_key(key)
        url = f"{self.storage_url}/object/{self.bucket}/{clean_key}"
        headers = self._headers({
            "Content-Type": content_type,
            "x-upsert": "true",
        })

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, content=data)
            except Exception as exc:
                raise StorageException(f"Network error connecting to Supabase Storage: {exc}") from exc

            if response.status_code in (200, 201):
                logger.info("Successfully uploaded object to Supabase Storage: bucket={}, key={}", self.bucket, clean_key)
                return clean_key

            if response.status_code == 429:
                raise StorageException(f"Supabase Storage rate limit reached (429): {response.text}")

            raise StorageException(
                f"Supabase Storage upload failed with status {response.status_code}: {response.text}"
            )

    async def download(self, key: str) -> bytes:
        clean_key = self._clean_key(key)
        url = f"{self.storage_url}/object/authenticated/{self.bucket}/{clean_key}"
        headers = self._headers()

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(url, headers=headers)
            except Exception as exc:
                raise StorageException(f"Network error connecting to Supabase Storage: {exc}") from exc

            if response.status_code == 200:
                return response.content

            if response.status_code == 404:
                raise FileNotFoundError(f"Object '{clean_key}' not found in bucket '{self.bucket}'")

            if response.status_code == 429:
                raise StorageException(f"Supabase Storage rate limit reached (429): {response.text}")

            raise StorageException(
                f"Supabase Storage download failed with status {response.status_code}: {response.text}"
            )

    async def delete(self, key: str) -> bool:
        clean_key = self._clean_key(key)
        url = f"{self.storage_url}/object/{self.bucket}"
        headers = self._headers({"Content-Type": "application/json"})

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request("DELETE", url, headers=headers, json={"prefixes": [clean_key]})
            except Exception as exc:
                raise StorageException(f"Network error connecting to Supabase Storage: {exc}") from exc

            if response.status_code in (200, 204):
                logger.info("Deleted object from Supabase Storage: bucket={}, key={}", self.bucket, clean_key)
                return True

            if response.status_code == 404:
                return True

            logger.warning("Failed to delete object from Supabase Storage: status={}, response={}", response.status_code, response.text)
            return False

    async def exists(self, key: str) -> bool:
        clean_key = self._clean_key(key)
        url = f"{self.storage_url}/object/authenticated/{self.bucket}/{clean_key}"
        headers = self._headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.head(url, headers=headers)
                if response.status_code == 200:
                    return True
                # If HEAD is unsupported, fall back to GET with range
                if response.status_code in (405, 400):
                    response = await client.get(url, headers={**headers, "Range": "bytes=0-0"})
                    return response.status_code in (200, 206)
                return False
            except Exception:
                return False

    async def get_usage(self) -> Dict[str, Any]:
        """Fetch all objects from the bucket to compute accurate usage and object counts across all prefixes."""
        url = f"{self.storage_url}/object/list/{self.bucket}"
        headers = self._headers({"Content-Type": "application/json"})
        total_bytes = 0
        total_objects = 0

        async def _list_prefix(client: httpx.AsyncClient, prefix: str) -> tuple[int, int]:
            p_bytes = 0
            p_objects = 0
            offset = 0
            limit = 100
            while True:
                payload = {
                    "prefix": prefix,
                    "limit": limit,
                    "offset": offset,
                    "sortBy": {"column": "name", "order": "asc"},
                }
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise StorageException(f"Failed to list objects in bucket '{self.bucket}': {response.text}")

                items = response.json()
                if not items:
                    break

                for item in items:
                    if item.get("id") is None:
                        # Directory prefix
                        sub_prefix = f"{prefix}/{item['name']}".strip("/")
                        sub_bytes, sub_objs = await _list_prefix(client, sub_prefix)
                        p_bytes += sub_bytes
                        p_objects += sub_objs
                    else:
                        p_objects += 1
                        meta = item.get("metadata") or {}
                        p_bytes += meta.get("size", 0)

                if len(items) < limit:
                    break
                offset += len(items)

            return p_bytes, p_objects

        async with httpx.AsyncClient(timeout=60.0) as client:
            total_bytes, total_objects = await _list_prefix(client, "")

        return {
            "bucket": self.bucket,
            "total_bytes": total_bytes,
            "total_objects": total_objects,
            "total_mb": round(total_bytes / (1024 * 1024), 4),
            "free_tier_limit_bytes": 1024 * 1024 * 1024,
            "free_tier_limit_mb": 1024.0,
            "usage_percentage": round((total_bytes / (1024 * 1024 * 1024)) * 100, 4),
        }


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for offline testing or standalone development."""

    def __init__(self, settings: Settings):
        self._upload_path = settings.upload_path

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        clean_name = Path(key).name
        target = self._upload_path / clean_name
        target.write_bytes(data)
        return str(target)

    async def download(self, key: str) -> bytes:
        p = Path(key)
        if not p.is_absolute():
            p = self._upload_path / p.name
        if not p.exists():
            raise FileNotFoundError(f"Local file not found: {p}")
        return p.read_bytes()

    async def delete(self, key: str) -> bool:
        p = Path(key)
        if not p.is_absolute():
            p = self._upload_path / p.name
        p.unlink(missing_ok=True)
        return True

    async def exists(self, key: str) -> bool:
        p = Path(key)
        if not p.is_absolute():
            p = self._upload_path / p.name
        return p.exists()

    async def get_usage(self) -> Dict[str, Any]:
        files = [f for f in self._upload_path.iterdir() if f.is_file()]
        total_bytes = sum(f.stat().st_size for f in files)
        return {
            "bucket": "local_uploads",
            "total_bytes": total_bytes,
            "total_objects": len(files),
            "total_mb": round(total_bytes / (1024 * 1024), 4),
            "free_tier_limit_bytes": 1024 * 1024 * 1024,
            "free_tier_limit_mb": 1024.0,
            "usage_percentage": round((total_bytes / (1024 * 1024 * 1024)) * 100, 4),
        }


class StorageService:
    """High-level facade for managing document file storage."""

    def __init__(self, backend: StorageBackend, settings: Settings):
        self.backend = backend
        self.settings = settings

    async def upload_document_file(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        prefix: str = "raw",
    ) -> str:
        """Uploads a document file and returns its storage key/path."""
        ext = Path(filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        key = f"{prefix}/{unique_name}" if prefix else unique_name
        return await self.backend.upload(key, content, content_type=content_type)

    def _resolve_legacy_local_path(self, storage_path: str) -> Optional[Path]:
        """Resolves whether a storage_path points to an existing local file."""
        if not storage_path:
            return None
        candidates = [
            Path(storage_path),
            Path("backend") / storage_path,
            Path("..") / storage_path,
            Path("uploads") / Path(storage_path).name,
            Path("backend/uploads") / Path(storage_path).name,
            Path("../uploads") / Path(storage_path).name,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                return c
        return None

    async def download_document_file(self, storage_path: str) -> bytes:
        """
        Downloads the file bytes for the document.
        Seamlessly handles both Supabase storage keys and legacy local disk paths.
        """
        # 1. Check legacy local disk path first (for unmigrated local files during migration)
        local_path = self._resolve_legacy_local_path(storage_path)
        if local_path is not None:
            return local_path.read_bytes()

        # 2. Fetch from the configured storage backend
        return await self.backend.download(storage_path)

    async def delete_document_file(self, storage_path: str) -> bool:
        """Deletes a document from storage backend and cleans up any legacy local file."""
        local_path = self._resolve_legacy_local_path(storage_path)
        if local_path is not None:
            try:
                local_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Failed to unlink local file {}: {}", local_path, e)

        try:
            return await self.backend.delete(storage_path)
        except Exception as e:
            logger.warning("Failed to delete storage object {}: {}", storage_path, e)
            return False

    @asynccontextmanager
    async def get_local_filepath(self, storage_path: str) -> AsyncGenerator[str, None]:
        """
        Context manager providing a temporary local filesystem path for OCR / PyPDF engines.
        If a local file exists, yields it directly.
        If stored in Supabase, downloads bytes to a temporary file and guarantees clean deletion on exit.
        """
        local_path = self._resolve_legacy_local_path(storage_path)
        if local_path is not None:
            yield str(local_path)
            return

        # Fetch bytes from storage backend
        content = await self.download_document_file(storage_path)
        ext = Path(storage_path).suffix or ".bin"

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            yield tmp_path
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as e:
                logger.warning("Failed to clean up temporary OCR file {}: {}", tmp_path, e)

    async def get_usage(self) -> Dict[str, Any]:
        """Returns storage usage against the free-tier limit."""
        return await self.backend.get_usage()


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Singleton getter for the configured storage service."""
    settings = get_settings()
    if settings.storage_backend == "supabase" and settings.supabase_service_role_key:
        backend = SupabaseStorageBackend(settings)
    else:
        logger.info("Using LocalStorageBackend (backend={}, has_key={})", settings.storage_backend, bool(settings.supabase_service_role_key))
        backend = LocalStorageBackend(settings)
    return StorageService(backend=backend, settings=settings)

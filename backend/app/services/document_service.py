"""
Document service — business logic for document upload and management.

Handles file validation, storage, checksum computation, and DB persistence
via the repository layer. No agent/AI logic here — that comes in Part 2.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from pathlib import Path

from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentResponse, DocumentUploadResponse


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "message/rfc822",           # .eml
    "application/octet-stream", # fallback for unknown
}


class DocumentService:
    """Handles document upload, validation, and CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = DocumentRepository(session)
        self._settings = get_settings()

    async def upload_document(
        self,
        file: UploadFile,
        case_id: uuid.UUID | None = None,
        uploaded_by: uuid.UUID | None = None,
    ) -> DocumentUploadResponse:
        """
        Validate, store, and register a new document using DocumentIngestionAgent.
        """
        content = await file.read()
        file_size = len(content)

        if file_size > self._settings.max_upload_size_bytes:
            raise ValueError(
                f"File exceeds maximum size of {self._settings.max_upload_size_mb} MB"
            )

        if file_size == 0:
            raise ValueError("Uploaded file is empty")

        ext = Path(file.filename or "unknown").suffix
        filename = file.filename or "unknown"
        
        # We pre-calculate hash to get any existing from DB to pass to the agent
        # so the agent can throw the DuplicateFileException as required.
        checksum = hashlib.sha256(content).hexdigest()
        existing_doc = await self._repo.get_by_checksum(checksum)
        existing_hashes = [checksum] if existing_doc else []

        from app.agents.ingestion import DocumentIngestionAgent, IngestionInput, AgentException

        agent = DocumentIngestionAgent()
        agent_input = IngestionInput(
            file_bytes=content,
            original_filename=filename,
            existing_hashes=existing_hashes
        )
        
        t_ingest = time.perf_counter()
        try:
            # Agent will validate, check duplicates, extract metadata
            agent_output = await agent.run(agent_input)
            ingest_duration = max(1, int((time.perf_counter() - t_ingest) * 1000))
        except AgentException as e:
            raise ValueError(str(e))

        logger.info(
            "Agent processed document",
            filename=agent_output.filename,
            size=agent_output.file_size,
            hash=agent_output.hash,
        )

        # Upload directly to storage backend (Supabase Storage)
        from app.services.storage_service import get_storage_service, StorageException
        storage_service = get_storage_service()
        try:
            storage_path = await storage_service.upload_document_file(
                filename=agent_output.filename,
                content=content,
                content_type=agent_output.mime_type,
                prefix="raw",
            )
        except StorageException as e:
            logger.error("Failed to upload document file to storage backend: {}", e)
            raise ValueError(f"Storage upload failed: {e}")

        # Persist to database
        document = await self._repo.create(
            case_id=case_id,
            uploaded_by=uploaded_by,
            filename=Path(storage_path).name,
            original_filename=agent_output.filename,
            content_type=agent_output.mime_type,
            file_size=agent_output.file_size,
            storage_path=storage_path,
            checksum_sha256=agent_output.hash,
            status=DocumentStatus.UPLOADED,
            doc_metadata={
                "upload_timestamp": agent_output.upload_timestamp,
                "document_type": agent_output.document_type,
                "custodian": agent_output.custodian,
                "confidence_score": agent_output.confidence_score
            }
        )

        from app.services.status_history_service import record_status_transition
        await record_status_transition(
            self._repo._session,
            document,
            DocumentStatus.UPLOADED,
            changed_by=uploaded_by,
            reason="initial_document_upload",
            old_status=None,
        )

        from app.services.orchestrator import record_agent_execution
        ingest_conf = round(agent_output.confidence_score * 100, 1) if agent_output.confidence_score <= 1.0 else agent_output.confidence_score
        await record_agent_execution(
            self._repo._session,
            "ingestion",
            str(document.id),
            agent_output.filename,
            ingest_duration,
            ingest_conf,
            0,
            "completed",
            f"Ingested {agent_output.filename} ({agent_output.file_size} bytes) in {ingest_duration}ms."
        )

        await self._repo._session.commit()

        return DocumentUploadResponse(
            id=document.id,
            filename=document.original_filename,
            status=document.status,
            uploaded_by=document.uploaded_by,
            message=f"Document '{document.original_filename}' uploaded successfully",
        )

    async def get_document(self, doc_id: uuid.UUID) -> DocumentResponse | None:
        """Fetch a single document by ID."""
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            return None
        return DocumentResponse.model_validate(doc)

    async def list_documents(
        self,
        *,
        case_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        include_content: bool = False,
    ) -> tuple[list[DocumentResponse], int]:
        """List documents with optional case filter and pagination."""
        offset = (page - 1) * page_size
        if case_id:
            docs = await self._repo.get_by_case_id(
                case_id, offset=offset, limit=page_size
            )
        else:
            docs = await self._repo.get_all(offset=offset, limit=page_size)
        total = await self._repo.count()
        results = []
        for d in docs:
            item = DocumentResponse.model_validate(d)
            if not include_content:
                item.extracted_text = None
            results.append(item)
        return results, total

    async def delete_document(self, doc_id: uuid.UUID) -> bool:
        """Delete a document record and clean up stored file."""
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            return False
        # Remove file from storage backend (and legacy local disk if present)
        if doc.storage_path:
            from app.services.storage_service import get_storage_service
            storage_service = get_storage_service()
            try:
                await storage_service.delete_document_file(doc.storage_path)
            except Exception as e:
                logger.warning("Could not delete file at path {}: {}", doc.storage_path, e)
        deleted = await self._repo.delete(doc_id)
        if deleted:
            await self._repo._session.commit()
            logger.info("Deleted document", doc_id=str(doc_id))
        return deleted

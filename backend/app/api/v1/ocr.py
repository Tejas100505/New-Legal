"""
OCR Agent API routes.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.agents.ocr import OCRAgent, OCRInput, AgentException
from app.db.session import get_db
from app.models.document import DocumentStatus
from app.services.document_service import DocumentService
from app.auth.dependencies import get_current_user, TokenPayload
from app.api.v1.documents import check_document_access
from loguru import logger

router = APIRouter(prefix="", tags=["OCR Agent"])

# Global agent instance for status/memory (in production use dependency injection)
ocr_agent = OCRAgent()

class OCRRequest(BaseModel):
    document_id: uuid.UUID
    page_number: int = 1


@router.post(
    "/ocr",
    status_code=status.HTTP_200_OK,
    summary="Trigger OCR on a document",
)
@limiter.limit("20/minute")
async def trigger_ocr(
    request: Request,
    data: OCRRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute the OCR agent on an uploaded document."""
    service = DocumentService(db)
    doc = await service.get_document(data.document_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {data.document_id} not found"
        )
    await check_document_access(doc, current_user, db)
        
    try:
        from app.services.storage_service import get_storage_service
        storage_service = get_storage_service()

        async with storage_service.get_local_filepath(doc.storage_path or "") as local_file_path:
            agent_input = OCRInput(
                file_path=local_file_path,
                document_type=doc.content_type,
                page_number=data.page_number
            )
            result = await ocr_agent.run(agent_input, request_id=str(uuid.uuid4()))
        
        # Persist extracted text and status update to DB
        await service._repo.update(
            request.document_id,
            extracted_text=result.text,
            status=DocumentStatus.OCR_PROCESSING
        )
        
        return result.model_dump()
        
    except AgentException as e:
        logger.error(f"OCR Agent failed for document {request.document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/agents/ocr/status",
    status_code=status.HTTP_200_OK,
    summary="Get OCR Agent status",
)
async def get_ocr_agent_status(
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return status, metrics, and recent memory of the OCR Agent."""
    return {
        "agent": ocr_agent.name,
        "prompt_version": ocr_agent.prompt_version,
        "available_engines": [engine.name for engine in ocr_agent.engines],
        "memory_entries_count": len(ocr_agent.memory),
        "recent_history": list(ocr_agent.memory.values())[-5:] # Last 5 executions
    }

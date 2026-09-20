"""
Semantic Search API routes.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document
from app.models.chunk import DocumentChunk
from app.repositories.chunk_repository import ChunkRepository
from app.services.document_service import DocumentService
from app.agents.chunking import ChunkingAgent, ChunkingInput
from app.agents.embedding import EmbeddingAgent, EmbeddingInput, ChunkData
from app.agents.retrieval import RetrievalInput
from app.auth.dependencies import get_current_user, TokenPayload, UserRole
from app.api.v1.documents import check_document_access
from app.services.retrieval_service import retrieve_case_chunks, retrieval_agent

router = APIRouter(prefix="", tags=["Semantic Search"])

# Global agent instances
chunking_agent = ChunkingAgent()
embedding_agent = EmbeddingAgent()


class EmbedRequest(BaseModel):
    document_id: uuid.UUID
    embedding_provider: str = "sentence_transformers"


class SearchRequest(BaseModel):
    query: str
    metadata_filters: Dict[str, Any] = {}
    top_k: int = 5


@router.post(
    "/embed",
    status_code=status.HTTP_201_CREATED,
    summary="Chunk and embed a document",
)
@limiter.limit("10/minute")
async def trigger_embed(
    request: Request,
    data: EmbedRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute chunking and embedding pipeline on an existing document."""
    service = DocumentService(db)
    chunk_repo = ChunkRepository(db)
    
    doc = await service.get_document(data.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await check_document_access(doc, current_user, db)
        
    text = getattr(doc, "extracted_text", None)
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text is empty; cannot chunk and embed."
        )

    # 1. Chunking
    chunk_input = ChunkingInput(
        document_id=str(doc.id),
        text=text,
        metadata={"filename": doc.filename}
    )
    chunk_result = await chunking_agent.run(chunk_input)
    
    # 2. Embedding
    embed_chunks_input = [ChunkData(**c.model_dump()) for c in chunk_result.chunks]
    embed_input = EmbeddingInput(
        chunks=embed_chunks_input,
        provider=data.embedding_provider
    )
    embed_result = await embedding_agent.run(embed_input)
    
    # 3. Store in DB
    for ec in embed_result.embedded_chunks:
        new_chunk = DocumentChunk(
            document_id=uuid.UUID(ec.document_id),
            chunk_id=ec.chunk_id,
            page=ec.page,
            section=ec.section,
            text=next(c.text for c in chunk_result.chunks if c.chunk_id == ec.chunk_id),
            embedding=ec.embedding,
            embedding_model=ec.embedding_model,
            metadata_=ec.metadata
        )
        db.add(new_chunk)
        
    await db.commit()
    
    return {
        "status": "success",
        "chunks_processed": len(embed_result.embedded_chunks),
        "provider": embed_result.provider_used
    }


@router.post(
    "/search",
    status_code=status.HTTP_200_OK,
    summary="Hybrid Semantic Search",
)
@router.post(
    "/search/semantic",
    status_code=status.HTTP_200_OK,
    summary="Hybrid Semantic Search (Alias)",
)
@limiter.limit("20/minute")
async def hybrid_search(
    request: Request,
    data: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute hybrid search using pgvector, BM25, and CrossEncoder."""
    case_id: Optional[uuid.UUID] = None
    if data.metadata_filters and "case_id" in data.metadata_filters:
        try:
            case_id = uuid.UUID(str(data.metadata_filters["case_id"]))
        except (ValueError, TypeError):
            case_id = None

    t_ret = time.perf_counter()
    try:
        results = await retrieve_case_chunks(
            db=db,
            query=data.query,
            case_id=case_id,
            current_user=current_user,
            top_k=data.top_k,
            metadata_filters=data.metadata_filters,
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_403_FORBIDDEN:
            return {
                "query": data.query,
                "results": [],
                "confidence_score": 0.0,
            }
        raise

    ret_duration = max(1, int((time.perf_counter() - t_ret) * 1000))

    from app.services.orchestrator import record_agent_execution
    query_str = (data.query[:50] + '...') if len(data.query) > 50 else data.query
    await record_agent_execution(
        db,
        "retrieval",
        str(uuid.uuid4()),
        "hybrid_search",
        ret_duration,
        95.0,
        0,
        "completed",
        f"Retrieved {len(results)} candidates for query: '{query_str}' in {ret_duration}ms.",
        auto_commit=True,
    )
    confidence = results[0]["confidence"] if results else 0.0
    return {
        "query": data.query,
        "results": results,
        "confidence_score": confidence,
    }


@router.get(
    "/search/history",
    status_code=status.HTTP_200_OK,
    summary="Get Search History",
)
async def get_search_history(
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return recent search requests from the Retrieval Agent's memory."""
    history = []
    for req_id, data in retrieval_agent.memory.items():
        if current_user.role != UserRole.ADMIN and data.get("user_id") != current_user.sub:
            continue
        history.append({
            "request_id": req_id,
            "query": data["input"]["query"],
            "top_k": data["input"]["top_k"],
            "results_count": len(data["output"]["results"]),
            "latency": data["latency"]
        })
    return {"history": history}

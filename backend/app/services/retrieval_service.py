"""
Standalone case-scoped chunk retrieval service.

Extracts the chunk-retrieval pipeline into a reusable, case-scoped function
enforcing creator-only ownership and admin-override access control.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embedding import ChunkData, EmbeddingAgent, EmbeddingInput
from app.agents.retrieval import RetrievalAgent, RetrievalInput
from app.auth.dependencies import TokenPayload, UserRole
from app.repositories.chunk_repository import ChunkRepository
from app.services.case_scoping import get_case_scoped_document_ids

embedding_agent = EmbeddingAgent()
retrieval_agent = RetrievalAgent()


async def retrieve_case_chunks(
    db: AsyncSession,
    query: str,
    case_id: Optional[uuid.UUID],
    current_user: TokenPayload,
    top_k: int = 5,
    metadata_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve and rerank case-scoped document chunks for a query.

    1. Enforces case scoping using get_case_scoped_document_ids.
    2. Generates query vector embedding using EmbeddingAgent.
    3. Performs vector similarity search via ChunkRepository.
    4. Transforms candidates into standard chunk dictionaries.
    5. Applies BM25 + Cross-Encoder reranking via RetrievalAgent.
    """
    # 1. Case scoping
    if case_id is None and metadata_filters and "case_id" in metadata_filters:
        try:
            case_id = uuid.UUID(str(metadata_filters["case_id"]))
        except (ValueError, TypeError):
            case_id = None

    scoped_doc_ids = await get_case_scoped_document_ids(db, case_id, current_user)
    if not scoped_doc_ids:
        return []

    filters: Dict[str, Any] = {"document_ids": scoped_doc_ids}

    # Handle client-requested metadata filters (document_id, page)
    if metadata_filters:
        if "document_id" in metadata_filters:
            try:
                req_doc_id = uuid.UUID(str(metadata_filters["document_id"]))
                if current_user.role != UserRole.ADMIN and req_doc_id not in scoped_doc_ids:
                    return []
                filters["document_id"] = req_doc_id
            except (ValueError, TypeError):
                pass

        if "page" in metadata_filters:
            filters["page"] = metadata_filters["page"]

    # 2. Query embedding
    query_chunk = ChunkData(
        chunk_id="query",
        document_id=str(uuid.uuid4()),
        page=1,
        section="query",
        text=query,
        metadata={},
    )
    embed_result = await embedding_agent.run(
        EmbeddingInput(chunks=[query_chunk])
    )
    query_vector = embed_result.embedded_chunks[0].embedding

    # 3. Vector search (fetch vector candidates for reranking)
    chunk_repo = ChunkRepository(db)
    vector_results = await chunk_repo.vector_search(
        query_embedding=query_vector,
        limit=20,
        filters=filters,
    )

    if not vector_results:
        return []

    # 4. Candidate transformation
    candidate_chunks = []
    for c, score in vector_results:
        candidate_chunks.append({
            "chunk_id": c.chunk_id,
            "document_id": str(c.document_id),
            "page": c.page,
            "section": c.section,
            "text": c.text,
            "metadata": c.metadata_ or {},
            "vector_score": round(score, 4),
        })

    # 5. RetrievalAgent reranking
    agent_metadata_filters = {}
    if metadata_filters:
        agent_metadata_filters = {
            k: v for k, v in metadata_filters.items() if k != "case_id"
        }

    retrieval_input = RetrievalInput(
        query=query,
        candidate_chunks=candidate_chunks,
        metadata_filters=agent_metadata_filters,
        top_k=top_k,
    )

    req_id = str(uuid.uuid4())
    result = await retrieval_agent.run(retrieval_input, request_id=req_id)

    if req_id in retrieval_agent.memory:
        retrieval_agent.memory[req_id]["user_id"] = current_user.sub

    return [r.model_dump() for r in result.results]

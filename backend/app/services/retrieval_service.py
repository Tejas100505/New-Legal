"""
Standalone case-scoped chunk retrieval service.

Extracts the chunk-retrieval pipeline into a reusable, case-scoped function
enforcing creator-only ownership and admin-override access control.
"""

from __future__ import annotations

import math
import re
import uuid
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embedding import ChunkData, EmbeddingAgent, EmbeddingInput
from app.agents.retrieval import RetrievalAgent, RetrievalInput, ChunkData as RetChunkData
from app.auth.dependencies import TokenPayload, UserRole
from app.models.chunk import DocumentChunk
from app.repositories.chunk_repository import ChunkRepository
from app.services.case_scoping import get_case_scoped_document_ids

embedding_agent = EmbeddingAgent()
retrieval_agent = RetrievalAgent()


BATCH3_MIN_CHUNK_CHARS: int = 50

EMAIL_ADDRESS_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
HEADER_PATTERN = re.compile(r"\b(?:to|from|cc|bcc)\s*:\s*", re.IGNORECASE)
DELIM_PATTERN = re.compile(r"[,;\s<>\"'()]+")


def is_address_list_fragment(text: str, threshold: float = 0.80) -> bool:
    """Flag a chunk as an address-list fragment if >80% of its non-whitespace characters are email addresses or address delimiters."""
    if not text:
        return False
    emails = EMAIL_ADDRESS_PATTERN.findall(text)
    if not emails:
        return False
    no_emails = EMAIL_ADDRESS_PATTERN.sub("", text)
    no_headers = HEADER_PATTERN.sub("", no_emails)
    prose_remaining = DELIM_PATTERN.sub("", no_headers)
    total_non_whitespace = len(re.sub(r"\s+", "", text))
    if total_non_whitespace == 0:
        return False
    email_chars = total_non_whitespace - len(prose_remaining)
    return (email_chars / total_non_whitespace) > threshold


def _compute_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return float(dot / (n1 * n2))


async def retrieve_case_chunks(
    db: AsyncSession,
    query: str,
    case_id: Optional[uuid.UUID],
    current_user: TokenPayload,
    top_k: int = 5,
    metadata_filters: Optional[Dict[str, Any]] = None,
    min_chunk_chars: Optional[int] = None,
    candidate_pool_size: int = 20,
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
        limit=candidate_pool_size,
        filters=filters,
        min_chunk_chars=min_chunk_chars,
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


async def retrieve_case_chunks_qa(
    db: AsyncSession,
    query: str,
    case_id: Optional[uuid.UUID],
    current_user: TokenPayload,
    top_k: int = 5,
    metadata_filters: Optional[Dict[str, Any]] = None,
    min_chunk_chars: Optional[int] = BATCH3_MIN_CHUNK_CHARS,
    candidate_pool_size: int = 20,
) -> List[Dict[str, Any]]:
    """
    Case-scoped chunk retrieval for Batch 3 Q&A pipeline.
    Uses BM25-top-N union Cosine-top-N candidate generation with address-list filtering,
    followed by hybrid reranking.
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

    # 3. Vector search (cosine-top-N, filtered by min_chunk_chars and address list filter)
    chunk_repo = ChunkRepository(db)
    vector_results = await chunk_repo.vector_search(
        query_embedding=query_vector,
        limit=candidate_pool_size * 2,
        filters=filters,
        min_chunk_chars=min_chunk_chars,
    )

    filtered_vector_results: List[tuple[DocumentChunk, float]] = []
    for c, score in vector_results:
        if not is_address_list_fragment(c.text or ""):
            filtered_vector_results.append((c, score))
            if len(filtered_vector_results) >= candidate_pool_size:
                break

    # 4. Fetch case-scoped chunks for BM25 (applying min_chunk_chars, metadata filters, and address filter)
    stmt = select(DocumentChunk).where(DocumentChunk.document_id.in_(scoped_doc_ids))
    if min_chunk_chars is not None:
        stmt = stmt.where(func.length(DocumentChunk.text) >= min_chunk_chars)
    if "document_id" in filters:
        stmt = stmt.where(DocumentChunk.document_id == filters["document_id"])
    if "page" in filters:
        stmt = stmt.where(DocumentChunk.page == filters["page"])

    res = await db.execute(stmt)
    all_case_chunks = list(res.scalars().all())
    bm25_candidate_chunks = [c for c in all_case_chunks if not is_address_list_fragment(c.text or "")]

    # 5. In-memory BM25 scoring using exact RetrievalAgent pattern
    bm25_top_chunks: List[DocumentChunk] = []
    if bm25_candidate_chunks:
        tokenized_corpus = [re.findall(r"\b\w+\b", (c.text or "").lower()) for c in bm25_candidate_chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = re.findall(r"\b\w+\b", query.lower())
        bm25_scores = bm25.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
        bm25_top_chunks = [bm25_candidate_chunks[i] for i in ranked_indices[:candidate_pool_size]]

    # 6. Union and deduplicate
    seen_chunk_ids = set()
    merged_candidates: List[RetChunkData] = []
    vector_score_map = {c.chunk_id: score for c, score in filtered_vector_results}

    # Add cosine top candidates
    for c, score in filtered_vector_results:
        if c.chunk_id not in seen_chunk_ids:
            seen_chunk_ids.add(c.chunk_id)
            merged_candidates.append(RetChunkData(
                chunk_id=c.chunk_id,
                document_id=str(c.document_id),
                page=c.page,
                section=c.section,
                text=c.text,
                metadata=c.metadata_ or {},
                vector_score=round(score, 4),
            ))

    # Add BM25 top candidates
    for c in bm25_top_chunks:
        if c.chunk_id not in seen_chunk_ids:
            seen_chunk_ids.add(c.chunk_id)
            if c.chunk_id in vector_score_map:
                v_score = vector_score_map[c.chunk_id]
            elif c.embedding is not None:
                v_score = _compute_cosine_similarity(query_vector, c.embedding)
            else:
                v_score = 0.0
            merged_candidates.append(RetChunkData(
                chunk_id=c.chunk_id,
                document_id=str(c.document_id),
                page=c.page,
                section=c.section,
                text=c.text,
                metadata=c.metadata_ or {},
                vector_score=round(v_score, 4),
            ))

    if not merged_candidates:
        return []

    # 7. Pass merged candidate pool to existing hybrid reranker unchanged
    agent_metadata_filters = {}
    if metadata_filters:
        agent_metadata_filters = {
            k: v for k, v in metadata_filters.items() if k != "case_id"
        }

    retrieval_input = RetrievalInput(
        query=query,
        candidate_chunks=merged_candidates,
        metadata_filters=agent_metadata_filters,
        top_k=top_k,
    )

    req_id = str(uuid.uuid4())
    result = await retrieval_agent.run(retrieval_input, request_id=req_id)

    if req_id in retrieval_agent.memory:
        retrieval_agent.memory[req_id]["user_id"] = current_user.sub

    return [r.model_dump() for r in result.results]


"""
AI Intelligence Layer API routes.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

import numpy as np

from app.core.rate_limit import limiter

from sqlalchemy import select
from app.models.case import Case
from app.models.document import Document
from app.db.session import get_db
from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.repositories.chunk_repository import ChunkRepository
from app.agents.classification import ClassificationAgent, ClassificationInput
from app.agents.entity_extraction import EntityExtractionAgent, EntityExtractionInput
from app.agents.relationship import RelationshipAgent, RelationshipInput
from app.agents.timeline import TimelineAgent, TimelineInput
from app.agents.clustering import ClusteringAgent, ClusteringInput
from app.agents.embedding import EmbeddingAgent, EmbeddingInput, ChunkData
from app.auth.dependencies import get_current_user, TokenPayload, UserRole
from app.api.v1.documents import check_document_access

router = APIRouter(prefix="", tags=["AI Intelligence"])

# Global agent instances
classification_agent = ClassificationAgent()
entity_agent = EntityExtractionAgent()
relationship_agent = RelationshipAgent()
timeline_agent = TimelineAgent()
clustering_agent = ClusteringAgent()
embedding_agent = EmbeddingAgent()


class DocumentRequest(BaseModel):
    document_id: uuid.UUID


class ClusteringRequest(BaseModel):
    document_ids: List[uuid.UUID]


async def _get_document_text(document_id: uuid.UUID, db: AsyncSession, current_user: TokenPayload) -> str:
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    await check_document_access(doc, current_user, db)
    text = getattr(doc, "extracted_text", None)
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document {document_id} has no extracted text to analyze."
        )
    return text


@router.get(
    "/entities",
    status_code=status.HTTP_200_OK,
    summary="Get all extracted entities across documents",
)
async def get_all_entities(
    case_id: uuid.UUID | None = Query(None, alias="case_id"),
    case_id_camel: uuid.UUID | None = Query(None, alias="caseId"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all entities extracted across stored document metadata."""
    effective_case_id = case_id or case_id_camel
    if effective_case_id and current_user.role != UserRole.ADMIN:
        case = await db.get(Case, effective_case_id)
        if not case or case.created_by != current_user.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case entities")

    query = (
        select(Document.id, Document.original_filename, Document.doc_metadata)
        .outerjoin(Case, Document.case_id == Case.id)
        .where(Document.doc_metadata.isnot(None))
    )
    if effective_case_id:
        query = query.where(Document.case_id == effective_case_id)
    elif current_user.role != UserRole.ADMIN:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except (ValueError, TypeError):
            user_uuid = None
        filter_cond = (Case.created_by == current_user.sub)
        if user_uuid is not None:
            filter_cond = filter_cond | ((Document.case_id.is_(None)) & (Document.uploaded_by == user_uuid))
        query = query.where(filter_cond)
    query = query.limit(100)
    result = await db.execute(query)
    rows = result.all()
    
    all_entities = []
    for doc_id, filename, meta in rows:
        if not isinstance(meta, dict):
            continue
        doc_ents = meta.get("entities", {})
        entity_conf = (
            meta.get("confidence_score")
            or meta.get("entity_confidence")
            or (meta.get("entity_extraction") if isinstance(meta.get("entity_extraction"), dict) else {}).get("confidence_score")
        )
        for category, items in doc_ents.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item_text = item.get("text") or item.get("name") or str(item)
                        raw_conf = item.get("confidence") or entity_conf
                    else:
                        item_text = str(item)
                        raw_conf = entity_conf
                    all_entities.append({
                        "id": f"ent_{len(all_entities)+1}",
                        "type": category[:-1] if category.endswith("s") else category,
                        "text": item_text,
                        "confidence": float(raw_conf) if raw_conf is not None else None,
                        "document_id": str(doc_id),
                        "filename": filename
                    })
                    
    return {"entities": all_entities}






@router.post(
    "/classify",
    status_code=status.HTTP_200_OK,
    summary="Classify a document",
)
@limiter.limit("15/minute")
async def classify_document(
    request: Request,
    data: DocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    text = await _get_document_text(data.document_id, db, current_user)
    input_data = ClassificationInput(document_id=str(data.document_id), text=text)
    result = await classification_agent.run(input_data)
    return result.model_dump()


@router.post(
    "/entities",
    status_code=status.HTTP_200_OK,
    summary="Extract entities from a document",
)
@limiter.limit("20/minute")
async def extract_entities(
    request: Request,
    data: DocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    text = await _get_document_text(data.document_id, db, current_user)
    input_data = EntityExtractionInput(document_id=str(data.document_id), text=text)
    result = await entity_agent.run(input_data)
    return result.model_dump()


@router.post(
    "/relationships",
    status_code=status.HTTP_200_OK,
    summary="Generate relationship graph",
)
@limiter.limit("20/minute")
async def generate_relationships(
    request: Request,
    data: DocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    text = await _get_document_text(data.document_id, db, current_user)
    entity_result = await entity_agent.run(EntityExtractionInput(document_id=str(data.document_id), text=text))
    input_data = RelationshipInput(
        document_id=str(data.document_id),
        entities=entity_result.entities.model_dump()
    )
    result = await relationship_agent.run(input_data)
    return result.model_dump()


@router.post(
    "/timeline",
    status_code=status.HTTP_200_OK,
    summary="Extract chronological timeline",
)
@limiter.limit("15/minute")
async def extract_timeline(
    request: Request,
    data: DocumentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    text = await _get_document_text(data.document_id, db, current_user)
    input_data = TimelineInput(document_id=str(data.document_id), text=text)
    result = await timeline_agent.run(input_data)
    return result.model_dump()


@router.post(
    "/clusters",
    status_code=status.HTTP_200_OK,
    summary="Cluster retrieved documents",
)
@limiter.limit("10/minute")
async def cluster_documents(
    request: Request,
    data: ClusteringRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    if not data.document_ids:
        return {"clusters": [], "confidence_score": 0.0}

    chunk_repo = ChunkRepository(db)
    docs_to_cluster = []

    for doc_id in data.document_ids:
        text = await _get_document_text(doc_id, db, current_user)
        chunks = await chunk_repo.get_by_document_id(doc_id)
        valid_embeddings = [c.embedding for c in chunks if c.embedding and len(c.embedding) == 1024]

        if valid_embeddings:
            # Average chunk embeddings to represent the full document
            avg_embedding = np.mean(valid_embeddings, axis=0).tolist()
            doc_embedding = avg_embedding
        else:
            if not text or not text.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document {doc_id} has no text or embeddings available to cluster."
                )
            # Generate real 1024-d embedding via Gemini Embedding API
            embed_chunk = ChunkData(
                chunk_id=f"cluster_{doc_id}",
                document_id=str(doc_id),
                page=1,
                section="full_document",
                text=text[:4000],
                metadata={}
            )
            embed_res = await embedding_agent.run(EmbeddingInput(chunks=[embed_chunk]))
            doc_embedding = embed_res.embedded_chunks[0].embedding

        docs_to_cluster.append({
            "id": str(doc_id),
            "text": text,
            "embedding": doc_embedding
        })

    input_data = ClusteringInput(documents=docs_to_cluster)
    t_clust = time.perf_counter()
    result = await clustering_agent.run(input_data)
    clust_duration = max(1, int((time.perf_counter() - t_clust) * 1000))
    clust_conf = round(result.confidence_score * 100, 1) if result.confidence_score <= 1.0 else result.confidence_score

    from app.services.orchestrator import record_agent_execution
    await record_agent_execution(
        db,
        "clustering",
        str(uuid.uuid4()),
        "document_clusters",
        clust_duration,
        clust_conf,
        0,
        "completed",
        f"Clustered {len(data.document_ids)} documents into {len(result.clusters)} clusters in {clust_duration}ms.",
        auto_commit=True,
    )
    return result.model_dump()

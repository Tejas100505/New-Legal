"""
Case Q&A API routes (Batch 3 Grounded RAG).

Provides endpoint:
- POST /api/v1/cases/{case_id}/ask

Enforces:
- Creator-only + admin-override security via get_case_scoped_document_ids (Batch 2 semantics)
- Rate limiting: 10/minute per client via SlowAPI limiter
- Deterministic Gate A (citation existence) and Gate B (lexical grounding) verification
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, TokenPayload
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.case_qa import QuestionRequest, QuestionResponse
from app.services.case_qa_service import ask_case_question

router = APIRouter(tags=["Case Q&A"])


@router.post(
    "/cases/{case_id}/ask",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Case-Scoped Grounded Q&A",
)
@limiter.limit("10/minute")
async def ask_case_question_endpoint(
    request: Request,
    case_id: uuid.UUID,
    data: QuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> QuestionResponse:
    """
    Stateless, single-turn, case-scoped grounded Q&A.

    - Scopes retrieval strictly to the authorized case.
    - Retrieves top-5 chunks via BM25-union-cosine (min_chunk_chars=50, address filter, theta=None).
    - Prompts LLM with labeled excerpts [C1]..[Ck] treating chunk text as untrusted data.
    - Enforces Gate A (citation validity) and Gate B (lexical grounding tau=0.55 + numeric/date containment).
    - Rate limited to 10 requests/minute per client.
    """
    return await ask_case_question(
        db=db,
        case_id=case_id,
        question=data.question,
        current_user=current_user,
    )

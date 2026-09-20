"""
Review Pipeline API routes.

POST /api/v1/review   – Run full review pipeline
POST /api/v1/report   – Generate exportable report
GET  /api/v1/review-map – Return the Review Map
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.services.document_service import DocumentService
from app.agents.summarization import SummarizationAgent, SummarizationInput
from app.agents.privilege import PrivilegeAgent, PrivilegeInput
from app.agents.pii import PIIAgent, PIIInput
from app.agents.risk import RiskAgent, RiskInput
from app.agents.verification import VerificationAgent, VerificationInput
from app.agents.review import ReviewAgent, ReviewInput
from app.agents.report import ReportAgent, ReportInput
from app.agents.entity_extraction import EntityExtractionAgent, EntityExtractionInput
from app.agents.relationship import RelationshipAgent, RelationshipInput
from app.agents.timeline import TimelineAgent, TimelineInput
from app.repositories.evaluation_repository import EvaluationRepository
from app.models.document import DocumentStatus
from app.auth.dependencies import get_current_user, TokenPayload, UserRole
from app.api.v1.documents import check_document_access

router = APIRouter(prefix="", tags=["Review Pipeline"])

# Global agent instances
summarization_agent = SummarizationAgent()
privilege_agent = PrivilegeAgent()
pii_agent = PIIAgent()
risk_agent = RiskAgent()
verification_agent = VerificationAgent()
review_agent = ReviewAgent()
report_agent = ReportAgent()
entity_agent = EntityExtractionAgent()
relationship_agent = RelationshipAgent()
timeline_agent = TimelineAgent()

# In-memory store for the latest review map per user
_latest_review_maps: Dict[str, Any] = {}


class ReviewRequest(BaseModel):
    document_ids: List[uuid.UUID]


class ReportRequest(BaseModel):
    document_id: uuid.UUID
    format: str = "markdown"
    review_data: Dict[str, Any] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


async def _get_document_text(document_id: uuid.UUID, db: AsyncSession) -> str:
    service = DocumentService(db)
    doc = await service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    text = getattr(doc, "extracted_text", None)
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document {document_id} has no extracted text. Run OCR or text extraction first."
        )
    return text


@router.post(
    "/review",
    status_code=status.HTTP_200_OK,
    summary="Run full review pipeline",
)
@limiter.limit("5/minute")
async def run_review(
    request: Request,
    data: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Execute the full review pipeline across all documents."""
    global _latest_review_map

    service = DocumentService(db)
    eval_repo = EvaluationRepository(db)
    doc_results = []

    for doc_id in data.document_ids:
        doc = await service._repo.get_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        await check_document_access(doc, current_user, db)
        
        text = doc.extracted_text
        if not text or not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {doc_id} has no extracted text. Run OCR or text extraction first."
            )
        doc_id_str = str(doc_id)
        doc_start = time.perf_counter()

        # 1. Summarization
        sum_result = await summarization_agent.run(
            SummarizationInput(document_id=doc_id_str, text=text)
        )

        # 2. Privilege
        priv_result = await privilege_agent.run(
            PrivilegeInput(document_id=doc_id_str, text=text)
        )

        # 3. PII
        t_pii = time.perf_counter()
        pii_result = await pii_agent.run(
            PIIInput(document_id=doc_id_str, text=text)
        )
        pii_duration = max(1, int((time.perf_counter() - t_pii) * 1000))
        from app.services.orchestrator import record_agent_execution
        await record_agent_execution(
            db,
            "pii",
            doc_id_str,
            "document_review",
            pii_duration,
            98.0,
            0,
            "completed",
            f"PII scan complete: {len(pii_result.entities_found)} entities detected in {pii_duration}ms.",
        )

        # 4. Risk
        risk_result = await risk_agent.run(
            RiskInput(document_id=doc_id_str, text=text)
        )

        # 5. Verification
        first_summary = sum_result.summaries[0].content if sum_result.summaries else ""
        citations = sum_result.summaries[0].citations if sum_result.summaries else []
        t_ver = time.perf_counter()
        ver_result = await verification_agent.run(
            VerificationInput(
                document_id=doc_id_str,
                summary_text=first_summary,
                source_text=text,
                citations=citations,
            )
        )
        ver_duration = max(1, int((time.perf_counter() - t_ver) * 1000))
        ver_score = round(ver_result.confidence_score * 100, 1) if ver_result.confidence_score <= 1.0 else ver_result.confidence_score
        await record_agent_execution(
            db,
            "verification",
            doc_id_str,
            "document_review",
            ver_duration,
            ver_score,
            0,
            "completed",
            f"Verification complete: confidence score {ver_score:.1f}% in {ver_duration}ms.",
        )

        # 6. Entity Extraction [NEW]
        entity_res = await entity_agent.run(
            EntityExtractionInput(document_id=doc_id_str, text=text)
        )

        # 7. Relationship [NEW]
        relationship_res = await relationship_agent.run(
            RelationshipInput(document_id=doc_id_str, entities=entity_res.entities.model_dump())
        )

        # 8. Timeline [NEW]
        timeline_res = await timeline_agent.run(
            TimelineInput(document_id=doc_id_str, text=text)
        )

        # Gather document result for review agent
        doc_res_data = {
            "document_id": doc_id_str,
            "summaries": [s.model_dump() for s in sum_result.summaries],
            "classification": "Contracts",  # Mocked / would come from Classification
            "privilege": priv_result.model_dump(),
            "pii_redacted": len(pii_result.entities_found) > 0,
            "risk": risk_result.overall_risk,
            "verification": ver_result.model_dump(),
            "entities": entity_res.entities.model_dump(),
            "graph_data": relationship_res.graph_data,
            "timeline": [t.model_dump() for t in timeline_res.timeline],
        }
        doc_results.append(doc_res_data)

        # Save findings in doc_metadata in the DB
        doc_metadata = doc.doc_metadata or {}
        doc_metadata.update({
            "summaries": doc_res_data["summaries"],
            "privilege": doc_res_data["privilege"],
            "pii_redacted": doc_res_data["pii_redacted"],
            "risk": risk_result.model_dump(),
            "verification": doc_res_data["verification"],
            "entities": doc_res_data["entities"],
            "graph_data": doc_res_data["graph_data"],
            "timeline": doc_res_data["timeline"],
        })
        doc.doc_metadata = doc_metadata
        doc.status = DocumentStatus.REVIEWED
        await service._repo.update(doc.id, doc_metadata=doc_metadata, status=DocumentStatus.REVIEWED)

        # Record metrics to evaluation_metrics table
        latency_ms = (time.perf_counter() - doc_start) * 1000
        rouge_scores_dump = {}
        if hasattr(sum_result, "rouge_scores"):
            for k, v in sum_result.rouge_scores.items():
                rouge_scores_dump[k] = v.model_dump() if hasattr(v, "model_dump") else v

        await eval_repo.create(
            case_id=doc.case_id,
            document_id=doc.id,
            metric_type="review",
            ocr_accuracy=1.0,  # Digital text assumed 100% accurate
            rouge_scores=rouge_scores_dump,
            hallucination_rate=ver_result.hallucination_score,
            latency_ms=latency_ms,
            token_usage={"prompt_tokens": 150, "completion_tokens": 100, "total_tokens": 250},
            privilege_accuracy=priv_result.confidence_score if hasattr(priv_result, "confidence_score") else 1.0,
            user_feedback=None
        )

    # 9. Review Agent (merge all)
    review_result = await review_agent.run(
        ReviewInput(documents=doc_results)
    )

    _latest_review_maps[current_user.sub] = review_result.review_map
    await db.commit()

    return review_result.model_dump()


@router.post(
    "/report",
    status_code=status.HTTP_200_OK,
    summary="Generate report",
)
async def generate_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate an exportable report."""
    service = DocumentService(db)
    doc = await service.get_document(request.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found")
    await check_document_access(doc, current_user, db)

    input_data = ReportInput(
        document_id=str(request.document_id),
        format=request.format,
        review_data=request.review_data,
        timeline=request.timeline,
        risks=request.risks,
        recommendations=request.recommendations,
    )
    t_rep = time.perf_counter()
    result = await report_agent.run(input_data)
    rep_duration = max(1, int((time.perf_counter() - t_rep) * 1000))
    from app.services.orchestrator import record_agent_execution
    await record_agent_execution(
        db,
        "report",
        str(request.document_id),
        "case_report",
        rep_duration,
        95.0,
        0,
        "completed",
        f"Report generated in {request.format} format in {rep_duration}ms.",
        auto_commit=True,
    )
    return result.model_dump()


@router.get(
    "/review-map",
    status_code=status.HTTP_200_OK,
    summary="Get Review Map",
)
async def get_review_map(
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return the latest Review Map as node-link JSON."""
    user_map = _latest_review_maps.get(current_user.sub)
    if not user_map:
        if current_user.role == UserRole.ADMIN and _latest_review_maps:
            user_map = next(iter(_latest_review_maps.values()))
        else:
            return {"nodes": [], "links": [], "message": "No review has been run yet."}
    return user_map

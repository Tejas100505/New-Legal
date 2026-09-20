"""
Reports and Audit Logs API routes.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document
from app.models.audit_log import AuditLog
from app.auth.dependencies import get_current_user, require_role, TokenPayload, UserRole
from app.services.case_scoping import get_case_scoped_document_ids
from app.agents.report import ReportAgent, ReportInput

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/audit-logs",
    status_code=status.HTTP_200_OK,
    summary="Get Audit Logs",
)
async def get_audit_logs(
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(UserRole.LAWYER, UserRole.ADMIN)),
) -> Dict[str, Any]:
    """Fetch system audit logs for legal compliance."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(AuditLog.user_email == current_user.email)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "status": "success",
        "total": len(logs),
        "audit_logs": [
            {
                "id": str(log.id),
                "user_email": log.user_email or "system@legal.com",
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details or {},
                "timestamp": log.created_at.isoformat(),
            }
            for log in logs
        ]
    }


@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export Case/Document Summary Report",
)
async def export_report(
    case_id: Optional[uuid.UUID] = None,
    format: str = Query("json", pattern="^(json|pdf|csv|markdown|docx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Any:
    """Generate and export executive summary report using ReportAgent and real database queries."""
    # 1. Scoping: Retrieve accessible document IDs using shared helper
    accessible_doc_ids = await get_case_scoped_document_ids(db, case_id, current_user)

    case_title = "Platform-wide Legal Review"
    if case_id:
        case = await db.get(Case, case_id)
        if case and case.name:
            case_title = case.name

    # 2. Query real document records
    docs: List[Document] = []
    if accessible_doc_ids:
        docs_stmt = (
            select(Document)
            .where(Document.id.in_(accessible_doc_ids))
            .order_by(Document.created_at.desc())
        )
        docs = list((await db.execute(docs_stmt)).scalars().all())

    # 3. Assemble review metrics, timeline, and risk data from real records
    privileged_count = 0
    high_risk_count = 0
    timeline_events: List[Dict[str, Any]] = []
    risks_list: List[Dict[str, Any]] = []
    seen_timeline_dates = set()

    for doc in docs:
        meta = doc.doc_metadata or {}

        # Privilege detection check
        is_priv = False
        priv_analysis = meta.get("privilege_analysis") or meta.get("privilege")
        if isinstance(priv_analysis, dict) and priv_analysis.get("is_privileged"):
            is_priv = True
        elif meta.get("is_privileged") is True:
            is_priv = True
        if is_priv:
            privileged_count += 1

        # Risk assessment aggregation
        risk_info = meta.get("risk_analysis") or meta.get("risk")
        if isinstance(risk_info, dict):
            assessments = risk_info.get("assessments")
            if isinstance(assessments, list):
                for assessment in assessments:
                    if isinstance(assessment, dict):
                        level = (assessment.get("risk_level") or "").upper()
                        if level in ("HIGH", "CRITICAL"):
                            high_risk_count += 1
                        risks_list.append({
                            "category": assessment.get("category", "General Risk"),
                            "risk_level": level or "UNKNOWN",
                            "reason": assessment.get("reason") or assessment.get("description") or f"Identified in {doc.original_filename}",
                        })
            elif risk_info.get("overall_risk") in ("HIGH", "CRITICAL"):
                high_risk_count += 1
                risks_list.append({
                    "category": "Overall Risk",
                    "risk_level": risk_info.get("overall_risk"),
                    "reason": f"Elevated risk in {doc.original_filename}",
                })

        # Timeline event aggregation
        doc_timeline = meta.get("timeline")
        if isinstance(doc_timeline, list):
            for ev in doc_timeline:
                if isinstance(ev, dict) and "date" in ev and "description" in ev:
                    dedup_key = (ev["date"], ev["description"][:60])
                    if dedup_key not in seen_timeline_dates:
                        seen_timeline_dates.add(dedup_key)
                        timeline_events.append({
                            "date": ev["date"],
                            "description": ev["description"],
                        })

    # Sort timeline chronologically
    timeline_events.sort(key=lambda x: x.get("date", ""))

    review_data = {
        "title": f"E-Discovery & Legal Review Executive Summary: {case_title}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": str(case_id) if case_id else "All Cases",
        "case_name": case_title,
        "total_documents": len(docs),
        "privileged_documents": privileged_count,
        "high_risk_flags": high_risk_count,
    }

    report_input = ReportInput(
        document_id=str(case_id) if case_id else "case_all",
        format=format,
        review_data=review_data,
        timeline=timeline_events,
        risks=risks_list,
        recommendations=[],  # Honest null/empty list when no recommendations generated yet
    )

    report_agent = ReportAgent()
    try:
        agent_output = await report_agent.run(report_input)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report generation failed: {e}",
        )

    # Return appropriate content type based on requested format
    if format == "json":
        # Parse JSON string from ReportAgent and merge with review_data for API contract consistency
        report_dict = json.loads(agent_output.content)
        return {
            "title": review_data["title"],
            "generated_at": review_data["generated_at"],
            "case_id": review_data["case_id"],
            "case_name": review_data["case_name"],
            "key_metrics": {
                "documents_analyzed": review_data["total_documents"],
                "privileged_documents": review_data["privileged_documents"],
                "high_risk_flags": review_data["high_risk_flags"],
            },
            "summary": {
                "total_documents": review_data["total_documents"],
            },
            "timeline": report_dict.get("timeline", []),
            "risks": report_dict.get("risks", []),
            "recommendations": report_dict.get("recommendations", []),
        }

    if format == "markdown":
        return Response(
            content=agent_output.content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=case_report_{report_input.document_id}.md"},
        )

    if format == "csv":
        return Response(
            content=agent_output.content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=case_report_{report_input.document_id}.csv"},
        )

    if format == "pdf":
        pdf_bytes = base64.b64decode(agent_output.content)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=case_report_{report_input.document_id}.pdf"},
        )

    if format == "docx":
        docx_bytes = base64.b64decode(agent_output.content)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=case_report_{report_input.document_id}.docx"},
        )

    return Response(
        content=agent_output.content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=case_report_{report_input.document_id}.txt"},
    )

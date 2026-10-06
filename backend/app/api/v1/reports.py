"""
Reports and Audit Logs API routes.
"""

from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.auth.dependencies import get_current_user, require_role, TokenPayload, UserRole
from app.services.report_service import generate_and_export_case_report

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


@router.get(
    "/history",
    status_code=status.HTTP_200_OK,
    summary="Get Case Report History",
)
async def get_report_history(
    case_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch history of generated reports from audit logs."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.action == "REPORT_GENERATED")
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if case_id:
        stmt = stmt.where(AuditLog.resource_id == str(case_id))
    elif current_user.role != UserRole.ADMIN:
        stmt = stmt.where(AuditLog.user_email == current_user.email)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    reports_history = []
    for log in logs:
        details = log.details or {}
        report_type = details.get("report_type", "review_summary")
        reports_history.append({
            "id": f"rpt_{log.id}",
            "audit_id": str(log.id),
            "name": f"{report_type.replace('_', ' ').title()} Report",
            "type": report_type,
            "format": details.get("format", "json"),
            "status": details.get("status", "completed"),
            "caseId": log.resource_id or "platform_wide",
            "caseName": details.get("case_name", "E-Discovery Review"),
            "matterNumber": details.get("matter_number", "N/A"),
            "generatedAt": log.created_at.isoformat(),
            "user_email": log.user_email,
            "metrics": {
                "total_documents": details.get("total_documents", 0),
                "privileged_documents": details.get("privileged_documents", 0),
                "high_risk_flags": details.get("high_risk_flags", 0),
            },
        })

    return {
        "status": "success",
        "total": len(reports_history),
        "reports": reports_history,
    }


@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export Evidence-Backed Case Report",
)
async def export_report(
    case_id: Optional[uuid.UUID] = None,
    report_type: str = Query("review_summary", pattern="^(review_summary|privilege_log|risk_assessment|executive_summary)$"),
    format: str = Query("json", pattern="^(json|pdf|csv|markdown|docx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
) -> Any:
    """
    Generate and export case report backed by real database records.
    Dispatches to ReportService and ReportAgent.
    """
    try:
        result = await generate_and_export_case_report(
            db=db,
            case_id=case_id,
            report_type=report_type,
            export_format=format,
            current_user=current_user,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report generation failed: {e}",
        )

    agent_output = result["agent_output"]
    raw_data = result["raw_data"]
    case_name = raw_data["case_info"]["case_name"]
    safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", case_name.lower())[:30].strip("_") or "case"
    filename_base = f"{safe_slug}_{report_type}"

    if format == "json":
        report_dict = json.loads(agent_output.content)
        return {
            "title": report_dict.get("title", f"{report_type.replace('_', ' ').title()} Report"),
            "report_type": report_type,
            "generated_at": raw_data["generated_at"],
            "case_id": raw_data["case_info"]["case_id"],
            "case_name": case_name,
            "case_info": raw_data["case_info"],
            "corpus_stats": raw_data["corpus_stats"],
            "key_metrics": {
                "documents_analyzed": raw_data["corpus_stats"]["total_documents"],
                "privileged_documents": raw_data["corpus_stats"]["privileged_documents"],
                "high_risk_flags": raw_data["corpus_stats"]["high_risk_documents"],
            },
            "summary": {
                "total_documents": raw_data["corpus_stats"]["total_documents"],
            },
            "executive_summary": raw_data["executive_summary"],
            "executive_sections": raw_data["executive_sections"],
            "top_entities": raw_data["top_entities"],
            "findings": raw_data["findings"],
            "timeline": raw_data["timeline"],
            "privilege_log": raw_data["privilege_log"],
            "risks": raw_data["risk_assessment"],
            "recommendations": report_dict.get("recommendations", []),
        }

    if format == "markdown":
        return Response(
            content=agent_output.content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.md"},
        )

    if format == "csv":
        return Response(
            content=agent_output.content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"},
        )

    if format == "pdf":
        pdf_bytes = base64.b64decode(agent_output.content)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.pdf"},
        )

    if format == "docx":
        docx_bytes = base64.b64decode(agent_output.content)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.docx"},
        )

    return Response(
        content=agent_output.content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename_base}.txt"},
    )

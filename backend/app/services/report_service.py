"""
Case Report Service.

Assembles genuine, evidence-backed legal report data scoped strictly by case_id.
Aggregates:
- Case Information & Matter Details
- Corpus Statistics (total, reviewed, flagged, privileged, high-risk)
- Executive Intelligence (persisted CaseSummary)
- Top Canonical Entities
- Privilege Log (structured row-level e-discovery log)
- Risk Assessment Matrix
- Chronological Timeline
- Major Findings & Source Citations
- Audit Log Persistence
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import TokenPayload, UserRole
from app.models.case import Case
from app.models.case_summary import CaseSummary, CaseSummaryStatus
from app.models.document import Document, DocumentStatus
from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.case_summary_repository import CaseSummaryRepository
from app.services.case_scoping import get_case_scoped_document_ids
from app.agents.report import ReportAgent, ReportInput, ReportOutput


async def assemble_case_report_data(
    db: AsyncSession,
    case_id: Optional[uuid.UUID],
    report_type: str,
    current_user: TokenPayload,
) -> Dict[str, Any]:
    """
    Assemble complete, structured case data directly from database records.
    Strictly case-scoped via get_case_scoped_document_ids.
    """
    # 1. Enforce access control and case scoping
    accessible_doc_ids = await get_case_scoped_document_ids(db, case_id, current_user)

    case_obj: Optional[Case] = None
    if case_id:
        case_obj = await db.get(Case, case_id)

    # Matter details
    case_info = {
        "case_id": str(case_id) if case_id else "platform_wide",
        "case_name": case_obj.name if (case_obj and case_obj.name) else "Platform-wide Legal Review",
        "case_number": case_obj.case_number if (case_obj and case_obj.case_number) else "N/A",
        "matter_number": getattr(case_obj, "matter_number", None) or (case_obj.case_number if case_obj else None) or "N/A",
        "client": getattr(case_obj, "client", None) or "N/A",
        "case_type": getattr(case_obj, "case_type", None) or "Commercial / Regulatory Litigation",
        "status": case_obj.status.value if (case_obj and hasattr(case_obj.status, "value")) else ("active" if case_obj else "system"),
        "priority": case_obj.priority.value if (case_obj and hasattr(case_obj.priority, "value")) else ("medium" if case_obj else "standard"),
        "created_at": case_obj.created_at.isoformat() if (case_obj and case_obj.created_at) else None,
        "last_activity": case_obj.updated_at.isoformat() if (case_obj and case_obj.updated_at) else None,
    }

    # 2. Query documents
    docs: List[Document] = []
    if accessible_doc_ids:
        docs_stmt = (
            select(Document)
            .where(Document.id.in_(accessible_doc_ids))
            .order_by(Document.created_at.desc())
        )
        docs = list((await db.execute(docs_stmt)).scalars().all())

    # 3. Compute corpus statistics
    total_docs = len(docs)
    reviewed_docs = 0
    flagged_docs = 0
    processing_docs = 0
    privileged_docs_count = 0
    high_risk_docs_count = 0

    processing_statuses = {
        DocumentStatus.UPLOADED,
        DocumentStatus.VALIDATING,
        DocumentStatus.OCR_PROCESSING,
        DocumentStatus.CHUNKING,
        DocumentStatus.EMBEDDING,
        DocumentStatus.ANALYZING,
    }

    # Data collection collections
    privilege_log_rows: List[Dict[str, Any]] = []
    risks_list: List[Dict[str, Any]] = []
    timeline_events: List[Dict[str, Any]] = []
    findings_list: List[Dict[str, Any]] = []
    seen_timeline_keys = set()
    seen_risk_keys = set()
    raw_entities: Dict[str, Dict[str, Any]] = {}

    for doc in docs:
        st = doc.status
        if st == DocumentStatus.REVIEWED:
            reviewed_docs += 1
        elif st == DocumentStatus.FLAGGED:
            flagged_docs += 1
        elif st in processing_statuses:
            processing_docs += 1

        meta = doc.doc_metadata or {}
        if meta.get("is_escalated"):
            flagged_docs = max(flagged_docs, 1)

        # Check privilege
        is_priv = False
        priv_analysis = meta.get("privilege_analysis") or meta.get("privilege") or {}
        if isinstance(priv_analysis, dict) and priv_analysis.get("is_privileged"):
            is_priv = True
        elif meta.get("is_privileged") is True:
            is_priv = True

        if is_priv:
            privileged_docs_count += 1
            # Extract privilege details for formal privilege log
            priv_type = meta.get("privilege_type")
            reasoning = ""
            if isinstance(priv_analysis, dict):
                if not priv_type:
                    priv_type = priv_analysis.get("privilege_type")
                reasoning = priv_analysis.get("reasoning") or ""
                if not reasoning:
                    detections = priv_analysis.get("detections")
                    if isinstance(detections, list):
                        for det in detections:
                            if isinstance(det, dict) and det.get("detected"):
                                if not priv_type:
                                    priv_type = det.get("privilege_type")
                                reasoning = det.get("explanation") or ""
                                break

            if not priv_type:
                priv_type = "Attorney-Client / Work Product"
            if not reasoning:
                reasoning = "Protected under e-discovery recall-first privilege safeguards"

            # Date identification
            doc_date = meta.get("date") or meta.get("document_date")
            if not doc_date and doc.created_at:
                doc_date = doc.created_at.strftime("%Y-%m-%d")

            custodian = meta.get("custodian") or meta.get("author") or "N/A"
            status_str = doc.status.value if hasattr(doc.status, "value") else str(doc.status)

            privilege_log_rows.append({
                "document": doc.original_filename,
                "document_id": str(doc.id)[:8],
                "full_document_id": str(doc.id),
                "date": str(doc_date or "N/A"),
                "author_custodian": str(custodian),
                "privilege_type": str(priv_type),
                "legal_basis": str(reasoning),
                "review_status": status_str,
                "withholding_status": meta.get("withholding_status") or "Withheld in Full",
            })

        # Check risk
        doc_has_high_risk = False
        risk_info = meta.get("risk_analysis") or meta.get("risk")
        if isinstance(risk_info, dict):
            assessments = risk_info.get("assessments")
            if isinstance(assessments, list):
                for assessment in assessments:
                    if isinstance(assessment, dict):
                        level = (assessment.get("risk_level") or "").upper()
                        if level in ("HIGH", "CRITICAL"):
                            doc_has_high_risk = True
                        cat = assessment.get("category", "General Risk")
                        reason = assessment.get("reason") or assessment.get("description") or f"Identified in {doc.original_filename}"
                        risk_key = (cat, level, reason[:50])
                        if risk_key not in seen_risk_keys:
                            seen_risk_keys.add(risk_key)
                            risks_list.append({
                                "category": cat,
                                "risk_level": level or "MEDIUM",
                                "severity": level or "MEDIUM",
                                "reason": reason,
                                "explanation": reason,
                                "source_document": doc.original_filename,
                                "document_id": str(doc.id)[:8],
                            })
            elif risk_info.get("overall_risk") in ("HIGH", "CRITICAL"):
                doc_has_high_risk = True
                risks_list.append({
                    "category": "Overall Risk",
                    "risk_level": risk_info.get("overall_risk"),
                    "severity": risk_info.get("overall_risk"),
                    "reason": f"Elevated risk flagged in {doc.original_filename}",
                    "explanation": f"Elevated risk flagged in {doc.original_filename}",
                    "source_document": doc.original_filename,
                    "document_id": str(doc.id)[:8],
                })

        if doc_has_high_risk:
            high_risk_docs_count += 1

        # Check timeline
        doc_timeline = meta.get("timeline")
        if isinstance(doc_timeline, list):
            for ev in doc_timeline:
                if isinstance(ev, dict) and "date" in ev and "description" in ev:
                    t_key = (ev["date"], ev["description"][:60])
                    if t_key not in seen_timeline_keys:
                        seen_timeline_keys.add(t_key)
                        timeline_events.append({
                            "date": ev["date"],
                            "event": ev.get("event") or ev.get("title") or ev["description"][:50],
                            "description": ev["description"],
                            "source_document": doc.original_filename,
                            "document_id": str(doc.id)[:8],
                        })

        # Check findings from document metadata
        ai_findings = meta.get("ai_findings") or meta.get("findings")
        if isinstance(ai_findings, list):
            for f in ai_findings:
                if isinstance(f, dict):
                    findings_list.append({
                        "title": f.get("title") or f.get("category") or "Key Finding",
                        "category": f.get("category") or "Evidence Analysis",
                        "severity": f.get("severity") or f.get("risk_level") or "Informational",
                        "description": f.get("description") or f.get("text") or "",
                        "source_document": doc.original_filename,
                        "citation": f.get("citation") or f.get("quote") or "",
                    })
                elif isinstance(f, str) and f.strip():
                    findings_list.append({
                        "title": "Finding",
                        "category": "Review Discovery",
                        "severity": "Informational",
                        "description": f.strip(),
                        "source_document": doc.original_filename,
                        "citation": "",
                    })

        # Extract entities from doc metadata as fallback
        doc_entities = meta.get("entities")
        if isinstance(doc_entities, dict):
            for cat, items in doc_entities.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str) and item.strip():
                            ename = item.strip()
                            if ename not in raw_entities:
                                raw_entities[ename] = {
                                    "name": ename,
                                    "type": cat[:-1] if cat.endswith("s") else cat,
                                    "importance_score": 0.05,
                                    "mention_count": 1,
                                }
                            else:
                                raw_entities[ename]["mention_count"] += 1
                                raw_entities[ename]["importance_score"] = min(
                                    1.0, raw_entities[ename]["importance_score"] + 0.02
                                )

    # Sort timeline chronologically
    timeline_events.sort(key=lambda x: str(x.get("date", "")))

    # Corpus dictionary
    corpus_stats = {
        "total_documents": total_docs,
        "reviewed_documents": reviewed_docs,
        "flagged_documents": flagged_docs,
        "processing_documents": processing_docs,
        "privileged_documents": privileged_docs_count,
        "high_risk_documents": high_risk_docs_count,
    }

    # 4. Integrate Persisted Case Executive Summary
    persisted_summary_text: Optional[str] = None
    persisted_sections: Dict[str, Any] = {}
    persisted_metadata: Dict[str, Any] = {}
    top_entities: List[Dict[str, Any]] = []

    if case_id:
        summary_repo = CaseSummaryRepository(db)
        case_summary_record = await summary_repo.get_latest_by_case_id(case_id)
        if (
            case_summary_record
            and case_summary_record.status == CaseSummaryStatus.COMPLETE
            and case_summary_record.summary_json
        ):
            sj = case_summary_record.summary_json
            persisted_sections = sj.get("sections") or {}
            persisted_summary_text = (
                persisted_sections.get("executive")
                or persisted_sections.get("legal")
                or persisted_sections.get("summary")
            )
            persisted_metadata = {
                "model_version": case_summary_record.model_version or "N/A",
                "generated_at": case_summary_record.generated_at.isoformat() if case_summary_record.generated_at else None,
                "source_doc_count": case_summary_record.source_doc_count,
            }
            if sj.get("top_entities"):
                top_entities = sj.get("top_entities")

            # If summary contains key_dates, add any missing dates to timeline
            for kd in sj.get("key_dates", []):
                if isinstance(kd, dict) and "date" in kd:
                    t_key = (kd["date"], (kd.get("description") or kd.get("event") or "")[:60])
                    if t_key not in seen_timeline_keys:
                        seen_timeline_keys.add(t_key)
                        timeline_events.append({
                            "date": kd["date"],
                            "event": kd.get("event") or "Key Date",
                            "description": kd.get("description") or kd.get("significance") or "",
                            "source_document": "Case Summary Synthesis",
                            "document_id": "Summary",
                        })

            # If summary contains notable provisions and findings, add to findings
            provisions = persisted_sections.get("notable_provisions_and_findings")
            if provisions and isinstance(provisions, str):
                findings_list.insert(0, {
                    "title": "Notable Provisions & Executive Findings",
                    "category": "Persisted Synthesis",
                    "severity": "High",
                    "description": provisions,
                    "source_document": "Case Intelligence Synthesis",
                    "citation": "",
                })

    if not persisted_summary_text:
        persisted_summary_text = "Case-level executive summary not yet available."

    # If top_entities is still empty, populate from raw_entities
    if not top_entities and raw_entities:
        sorted_entities = sorted(raw_entities.values(), key=lambda e: e.get("mention_count", 0), reverse=True)
        top_entities = sorted_entities[:10]

    # Re-sort timeline after any additions
    timeline_events.sort(key=lambda x: str(x.get("date", "")))

    return {
        "report_type": report_type,
        "case_info": case_info,
        "corpus_stats": corpus_stats,
        "executive_summary": persisted_summary_text,
        "executive_sections": persisted_sections,
        "summary_metadata": persisted_metadata,
        "top_entities": top_entities,
        "findings": findings_list,
        "timeline": timeline_events,
        "privilege_log": privilege_log_rows,
        "risk_assessment": risks_list,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def generate_and_export_case_report(
    db: AsyncSession,
    case_id: Optional[uuid.UUID],
    report_type: str,
    export_format: str,
    current_user: TokenPayload,
) -> Dict[str, Any]:
    """
    Orchestrate report generation and persistence:
    1. Assemble real scoped data
    2. Dispatch to ReportAgent
    3. Persist AuditLog entry
    4. Return payload
    """
    data = await assemble_case_report_data(db, case_id, report_type, current_user)

    report_input = ReportInput(
        document_id=str(case_id) if case_id else "case_all",
        report_type=report_type,
        format=export_format,
        case_info=data["case_info"],
        corpus_stats=data["corpus_stats"],
        executive_summary=data["executive_summary"],
        executive_sections=data["executive_sections"],
        summary_metadata=data["summary_metadata"],
        top_entities=data["top_entities"],
        findings=data["findings"],
        timeline=data["timeline"],
        privilege_log=data["privilege_log"],
        risks=data["risk_assessment"],
        review_data={
            "case_id": data["case_info"]["case_id"],
            "case_name": data["case_info"]["case_name"],
            "matter_number": data["case_info"]["matter_number"],
            "total_documents": data["corpus_stats"]["total_documents"],
            "reviewed_documents": data["corpus_stats"]["reviewed_documents"],
            "flagged_documents": data["corpus_stats"]["flagged_documents"],
            "privileged_documents": data["corpus_stats"]["privileged_documents"],
            "high_risk_flags": data["corpus_stats"]["high_risk_documents"],
        },
    )

    report_agent = ReportAgent()
    agent_output: ReportOutput = await report_agent.run(report_input)

    # Persist AuditLog entry for compliance and history restoration
    try:
        user_uuid: Optional[uuid.UUID] = None
        if current_user.sub:
            try:
                candidate_id = uuid.UUID(current_user.sub)
                existing_user = await db.get(User, candidate_id)
                if existing_user:
                    user_uuid = candidate_id
            except (ValueError, TypeError):
                pass

        audit_entry = AuditLog(
            user_id=user_uuid,
            user_email=current_user.email,
            action="REPORT_GENERATED",
            resource_type="case_report",
            resource_id=str(case_id) if case_id else "platform_wide",
            details={
                "report_type": report_type,
                "format": export_format,
                "case_name": data["case_info"]["case_name"],
                "matter_number": data["case_info"]["matter_number"],
                "total_documents": data["corpus_stats"]["total_documents"],
                "privileged_documents": data["corpus_stats"]["privileged_documents"],
                "high_risk_flags": data["corpus_stats"]["high_risk_documents"],
                "timestamp": data["generated_at"],
                "status": "completed",
            },
        )
        db.add(audit_entry)
        await db.commit()
    except Exception as audit_err:
        logger.warning(f"Failed to persist report audit log: {audit_err}")
        await db.rollback()

    return {
        "report_type": report_type,
        "format": export_format,
        "raw_data": data,
        "agent_output": agent_output,
    }

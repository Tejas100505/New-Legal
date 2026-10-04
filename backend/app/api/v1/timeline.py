import uuid
from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document
from app.auth.dependencies import get_current_user, TokenPayload, UserRole

router = APIRouter(prefix="/timeline", tags=["Timeline"])

class TimelineEventResponse(BaseModel):
    id: str
    title: str
    description: str
    type: str
    timestamp: str
    caseId: str = Field(alias="caseId")
    caseName: str = Field(alias="caseName")
    userId: str = Field(alias="userId")
    userName: str = Field(alias="userName")
    documentId: Optional[str] = Field(None, alias="documentId")
    documentName: Optional[str] = Field(None, alias="documentName")
    lawyerName: Optional[str] = Field(None, alias="lawyerName")
    priority: Optional[str] = None
    amount: Optional[float] = None
    entityNames: Optional[List[str]] = Field(default_factory=list, alias="entityNames")
    metadata: Dict[str, str] = Field(default_factory=dict)
    source: str = "live"  # data provenance: "live" = from pipeline extraction
    
    model_config = {"populate_by_name": True}


@router.get("", response_model=List[TimelineEventResponse], summary="Get filtered timeline events")
async def get_timeline(
    case_id: Optional[str] = Query(None, alias="caseId"),
    case_id_snake: Optional[str] = Query(None, alias="case_id"),
    priority: Optional[str] = None,
    lawyer_name: Optional[str] = Query(None, alias="lawyerName"),
    entity_name: Optional[str] = Query(None, alias="entityName"),
    document_id: Optional[str] = Query(None, alias="documentId"),
    evidence_id: Optional[str] = Query(None, alias="evidenceId"),
    search: Optional[str] = None,
    limit: Optional[int] = Query(None, description="Optional limit of timeline events"),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    effective_case_id_str = case_id or case_id_snake
    uuid_case_id = None
    case_name = "Case Timeline Investigation"
    
    if effective_case_id_str:
        try:
            uuid_case_id = uuid.UUID(effective_case_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID format")

    if uuid_case_id:
        case = await db.get(Case, uuid_case_id)
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        if current_user.role != UserRole.ADMIN and case.created_by != current_user.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case timeline")
        case_name = case.name or "Case Investigation"

    # Retrieve documents efficiently without heavy extracted_text
    stmt = (
        select(
            Document.id,
            Document.case_id,
            Document.uploaded_by,
            Document.original_filename,
            Document.filename,
            Document.file_size,
            Document.status,
            Document.created_at,
            Document.doc_metadata
        )
        .outerjoin(Case, Document.case_id == Case.id)
        .where(Document.doc_metadata.isnot(None))
        .order_by(Document.created_at.desc())
    )
    if uuid_case_id:
        stmt = stmt.where(Document.case_id == uuid_case_id)
    elif current_user.role != UserRole.ADMIN:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except (ValueError, TypeError):
            user_uuid = None
        filter_cond = (Case.created_by == current_user.sub)
        if user_uuid is not None:
            filter_cond = filter_cond | ((Document.case_id.is_(None)) & (Document.uploaded_by == user_uuid))
        stmt = stmt.where(filter_cond)

    result = await db.execute(stmt)
    docs = result.all()

    live_events: List[Dict[str, Any]] = []
    for d in docs:
        doc_id, doc_case_id, uploaded_by, orig_fn, fn, fsize, doc_status, created_at, meta = d
        meta = meta or {}
        fn_display = orig_fn or fn or ""
        is_email = "email" in fn_display.lower() or fn_display.endswith(".txt")
        tl = meta.get("timeline")
        
        # Extract entities for search & chips
        doc_entities = meta.get("entities", {})
        entity_names_sample = []
        if isinstance(doc_entities, dict):
            for cat_list in doc_entities.values():
                if isinstance(cat_list, list):
                    for item in cat_list:
                        if isinstance(item, str) and item.strip() and len(entity_names_sample) < 5:
                            entity_names_sample.append(item.strip())

        if tl and isinstance(tl, list):
            for idx, item in enumerate(tl):
                if not isinstance(item, dict):
                    continue
                date_str = item.get("date", "2023-01-01")
                if "T" not in date_str:
                    date_str = f"{date_str}T00:00:00Z"
                
                ev_type = item.get("type") or ("email" if is_email else "document")
                
                # Normalize priority
                ev_importance = item.get("importance")
                if not ev_importance:
                    triage = meta.get("triage") if isinstance(meta.get("triage"), dict) else {}
                    risk = meta.get("risk") if isinstance(meta.get("risk"), dict) else {}
                    ev_importance = triage.get("priority_tier") or risk.get("risk_level") or "medium"
                
                p_norm = str(ev_importance).lower()
                if p_norm not in ("critical", "high", "medium", "low"):
                    p_norm = "medium"

                desc = item.get("description", "")
                title = desc[:70] + "..." if len(desc) > 70 else (desc or "Investigation Event")
                
                live_events.append({
                    "id": f"evt_{str(doc_id)[:6]}_{idx}",
                    "title": title,
                    "description": desc,
                    "type": ev_type,
                    "timestamp": date_str,
                    "caseId": str(doc_case_id or uuid_case_id or ""),
                    "caseName": case_name,
                    "userId": str(uploaded_by) if uploaded_by else "sys",
                    "userName": "TimelineAgent",
                    "documentId": str(doc_id),
                    "documentName": fn_display,
                    "priority": p_norm,
                    "entityNames": entity_names_sample,
                    "metadata": {
                        "document_id": str(doc_id),
                        "filename": fn_display,
                    },
                    "source": "live"
                })
        elif created_at:
            live_events.append({
                "id": f"evt_doc_{str(doc_id)[:6]}",
                "title": f"Document Ingestion: {fn_display}",
                "description": f"Uploaded file '{fn_display}' ({fsize or 0} bytes).",
                "type": "upload",
                "timestamp": created_at.isoformat(),
                "caseId": str(doc_case_id or uuid_case_id or ""),
                "caseName": case_name,
                "userId": str(uploaded_by) if uploaded_by else "sys",
                "userName": "System",
                "documentId": str(doc_id),
                "documentName": fn_display,
                "priority": "low",
                "entityNames": entity_names_sample,
                "metadata": {
                    "document_id": str(doc_id),
                    "filename": fn_display,
                },
                "source": "live"
            })

    events = live_events

    # Case scoping filter
    if uuid_case_id:
        events = [e for e in events if e["caseId"] == str(uuid_case_id)]

    # Filters
    if priority:
        events = [e for e in events if e.get("priority") == priority.lower()]
    if lawyer_name:
        events = [e for e in events if e.get("lawyerName") == lawyer_name]
    if document_id:
        events = [e for e in events if e.get("documentId") == document_id]
    if entity_name:
        events = [e for e in events if e.get("entityNames") and any(entity_name.lower() in ent.lower() for ent in e["entityNames"])]
    if search:
        query = search.lower()
        events = [
            e for e in events 
            if query in e["title"].lower() 
            or query in e["description"].lower() 
            or query in (e.get("documentName") or "").lower()
        ]

    # Sort chronologically
    events.sort(key=lambda x: x["timestamp"])

    # Pagination
    if limit is not None:
        events = events[offset : offset + limit]

    return events


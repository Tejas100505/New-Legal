import uuid
from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.case import Case
from app.models.document import Document
from app.services.document_service import DocumentService
from app.auth.dependencies import get_current_user, TokenPayload, UserRole
from app.api.v1.documents import check_document_access

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
    lawyerName: Optional[str] = Field(None, alias="lawyerName")
    priority: Optional[str] = None
    amount: Optional[float] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
    source: str = "live"  # data provenance: "live" = from pipeline extraction
    
    model_config = {"populate_by_name": True}


@router.get("", response_model=List[TimelineEventResponse], summary="Get filtered timeline events")
async def get_timeline(
    case_id: Optional[str] = Query(None, alias="caseId"),
    priority: Optional[str] = None,
    lawyer_name: Optional[str] = Query(None, alias="lawyerName"),
    entity_name: Optional[str] = Query(None, alias="entityName"),
    document_id: Optional[str] = Query(None, alias="documentId"),
    evidence_id: Optional[str] = Query(None, alias="evidenceId"),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    service = DocumentService(db)
    
    # Check if case_id is a valid UUID
    uuid_case_id = None
    if case_id:
        try:
            uuid_case_id = uuid.UUID(case_id)
        except ValueError:
            pass

    if uuid_case_id and current_user.role != UserRole.ADMIN:
        case = await db.get(Case, uuid_case_id)
        if not case or case.created_by != current_user.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case timeline")

    # Retrieve documents
    if uuid_case_id:
        docs = await service._repo.get_by_case_id(uuid_case_id)
    elif current_user.role == UserRole.ADMIN:
        docs = await service._repo.get_all()
    else:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except (ValueError, TypeError):
            user_uuid = None
        filter_cond = (Case.created_by == current_user.sub)
        if user_uuid is not None:
            filter_cond = filter_cond | ((Document.case_id.is_(None)) & (Document.uploaded_by == user_uuid))

        stmt = (
            select(Document)
            .outerjoin(Case, Document.case_id == Case.id)
            .where(filter_cond)
        )
        docs = (await db.execute(stmt)).scalars().all()

    live_events = []
    for doc in docs:
        if doc.doc_metadata and "timeline" in doc.doc_metadata:
            for item in doc.doc_metadata["timeline"]:
                date_str = item.get("date", "2023-01-01")
                # Format to timestamp format
                if "T" not in date_str:
                    date_str = f"{date_str}T00:00:00Z"
                
                live_events.append({
                    "id": f"evt_live_{uuid.uuid4().hex[:6]}",
                    "title": item.get("description", "Extracted Event")[:40] + "...",
                    "description": item.get("description", ""),
                    "type": "ai_finding",
                    "timestamp": date_str,
                    "caseId": str(doc.case_id or ""),
                    "caseName": "Case Timeline Review",
                    "userId": str(doc.uploaded_by) if doc.uploaded_by else "sys",
                    "userName": "TimelineAgent",
                    "priority": "medium",
                    "metadata": {"document_id": str(doc.id)},
                    "source": "live"
                })
        elif doc.created_at:
            live_events.append({
                "id": f"evt_doc_{doc.id.hex[:6]}",
                "title": f"Document Ingestion: {doc.original_filename or doc.filename}",
                "description": f"Uploaded file '{doc.original_filename or doc.filename}' ({doc.file_size} bytes, status: {doc.status.value if hasattr(doc.status, 'value') else str(doc.status)}).",
                "type": "upload",
                "timestamp": doc.created_at.isoformat(),
                "caseId": str(doc.case_id or ""),
                "caseName": "Document Ingestion",
                "userId": str(doc.uploaded_by) if doc.uploaded_by else "sys",
                "userName": "System",
                "priority": "low",
                "metadata": {"document_id": str(doc.id)},
                "source": "live"
            })

    events = live_events

    # Apply filters
    if case_id:
        events = [e for e in events if e["caseId"] == case_id]
    if priority:
        events = [e for e in events if e.get("priority") == priority]
    if lawyer_name:
        events = [e for e in events if e.get("lawyerName") == lawyer_name]
    if search:
        query = search.lower()
        events = [e for e in events if query in e["title"].lower() or query in e["description"].lower()]
        
    return events

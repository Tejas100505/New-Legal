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
    source: str = "live" # "live" | "mock_fallback"
    
    model_config = {"populate_by_name": True}

MOCK_EVENTS = [
  {
    "id": "evt_016", "title": "Privilege Review Flagged", "description": "3 documents flagged for attorney-client privilege in SEC investigation.",
    "type": "ai_finding", "timestamp": "2026-07-17T07:15:00Z", "caseId": "case_003",
    "caseName": "SEC Investigation", "userId": "sys", "userName": "Privilege Detector", "priority": "critical", "metadata": {"count": "3"}
  },
  {
    "id": "evt_017", "title": "Batch Upload Completed", "description": "47 documents uploaded and queued for OCR processing.",
    "type": "upload", "timestamp": "2026-07-17T06:30:00Z", "caseId": "case_001",
    "caseName": "Meridian v. Atlas", "userId": "usr_001", "userName": "Sarah Chen", "priority": "medium", "metadata": {"count": "47"}
  },
  {
    "id": "evt_018", "title": "Case Status Updated", "description": "Greenfield case moved to active review phase.",
    "type": "status_change", "timestamp": "2026-07-16T18:00:00Z", "caseId": "case_003",
    "caseName": "SEC Investigation", "userId": "usr_001", "userName": "Sarah Chen", "priority": "low", "metadata": {"from": "active", "to": "review"}
  },
  {
    "id": "evt_019", "title": "Risk Assessment Generated", "description": "Automated risk assessment completed for NovaTech IP portfolio.",
    "type": "review", "timestamp": "2026-07-16T15:30:00Z", "caseId": "case_005",
    "caseName": "NovaTech Merger", "userId": "sys", "userName": "Risk Analyzer", "priority": "medium", "metadata": {"score": "72"}
  },
  {
    "id": "evt_020", "title": "New Evidence Discovered", "description": "Timeline Builder identified potential backdated document in Thornton estate.",
    "type": "ai_finding", "timestamp": "2026-07-16T12:00:00Z", "caseId": "case_002",
    "caseName": "Thornton Estate", "userId": "sys", "userName": "Timeline Builder", "priority": "high", "metadata": {"documentId": "doc_005"}
  },
  {
    "id": "evt_001", "title": "Meridian Corp NDA Signed",
    "description": "Dr. James Whitfield and John Miller sign a comprehensive Non-Disclosure Agreement before beginning R&D work.",
    "type": "contract", "timestamp": "2023-05-14T09:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "lawyerName": "Sarah Chen", "priority": "medium", "metadata": {}
  },
  {
    "id": "evt_002", "title": "Contested Patent Filing Date",
    "description": "Patent US-2024-0089123 on Semiconductor Planarization is filed with the USPTO by Meridian Corp.",
    "type": "legal_event", "timestamp": "2024-03-12T10:30:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "priority": "high", "metadata": {}
  },
  {
    "id": "evt_003", "title": "John Miller Resignation",
    "description": "John Miller resigns as Senior R&D Engineer from Meridian Corp, citing personal reasons. System access is revoked.",
    "type": "incident", "timestamp": "2025-08-15T17:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "priority": "high", "metadata": {}
  },
  {
    "id": "evt_004", "title": "Unauthorized Code Repo Copying",
    "description": "System access logs detect a massive clone of the internal R&D repository by credentials assigned to John Miller just before resignation.",
    "type": "ocr_timestamp", "timestamp": "2025-08-15T18:24:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_002", "userName": "AI Extractor", "priority": "high", "metadata": {"source": "Security Server Logs"}
  },
  {
    "id": "evt_005", "title": "John Miller Hired by Atlas Industries",
    "description": "Atlas Industries announces John Miller has joined as VP of Semiconductor Engineering, a position created recently.",
    "type": "incident", "timestamp": "2025-09-01T09:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "priority": "high", "metadata": {}
  },
  {
    "id": "evt_006", "title": "Wire Transfer to Switzerland",
    "description": "Financial ledger shows a wire transfer of $1.2M from Atlas Offshore account to a Swiss bank account linked to John Miller's family trust.",
    "type": "payment", "timestamp": "2025-09-10T14:15:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "amount": 1200000.0, "priority": "medium", "metadata": {"bank": "Credit Suisse"}
  },
  {
    "id": "evt_007", "title": "Slack Communication - Phoenix Launch",
    "description": "Internal Slack conversation shows Robert Chen (CEO) urging engineering to launch Project Phoenix weeks ahead of schedule.",
    "type": "email", "timestamp": "2025-11-20T16:44:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_002", "userName": "AI Extractor", "priority": "medium", "metadata": {"channel": "#exec-leadership"}
  },
  {
    "id": "evt_008", "title": "Patent Infringement Complaint Filed",
    "description": "Meridian Corp files official complaint against Atlas Industries in Northern District of California (2026-CV-4821).",
    "type": "legal_event", "timestamp": "2026-02-14T09:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "lawyerName": "Sarah Chen", "priority": "critical", "metadata": {}
  },
  {
    "id": "evt_009", "title": "Subpoena Served on Atlas",
    "description": "Court issues subpoena requiring Atlas Industries to preserve and produce engineering logs and blueprint documents.",
    "type": "legal_event", "timestamp": "2026-04-10T10:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "priority": "high", "metadata": {}
  },
  {
    "id": "evt_010", "title": "First Court Hearing",
    "description": "Judge hears arguments on motion for preliminary injunction filed by Meridian Corp. Decides to expedite discovery.",
    "type": "hearing", "timestamp": "2026-05-20T13:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "lawyerName": "Sarah Chen", "priority": "high", "metadata": {}
  },
  {
    "id": "evt_011", "title": "AI Decision: Code Similarity Flagged",
    "description": "Legal Review Agent runs similarity scan and flags 89% structural overlap between Meridian's proprietary planarization code and Atlas's repository.",
    "type": "ai_decision", "timestamp": "2026-06-05T11:20:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_002", "userName": "AI Review Agent", "priority": "high", "metadata": {"confidence": "97%"}
  },
  {
    "id": "evt_012", "title": "Deposition of Dr. Whitfield",
    "description": "Dr. James Whitfield is deposed for 6 hours by Atlas Counsel, validating the timeline of invention of the semiconductor process.",
    "type": "hearing", "timestamp": "2026-06-12T10:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "priority": "medium", "metadata": {"location": "San Jose Court Room 4"}
  },
  {
    "id": "evt_013", "title": "Deposition of John Miller",
    "description": "John Miller is deposed. Admits accessing Meridian servers post-termination but claims it was to retrieve personal assets.",
    "type": "hearing", "timestamp": "2026-06-18T10:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "priority": "medium", "metadata": {"location": "Austin Office Depot"}
  },
  {
    "id": "evt_014", "title": "Expert Witness Report Submitted",
    "description": "Dr. Linda Vance submits expert analysis comparing the R&D artifacts, validating the claim of copy-pasted manufacturing processes.",
    "type": "document", "timestamp": "2026-07-02T16:00:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_001", "userName": "Sarah Chen", "priority": "high", "metadata": {}
  },
  {
    "id": "evt_015", "title": "AI Decision: Trade Secret Theft High Probability",
    "description": "Legal Review Agent runs final inference and flags Case 2026-CV-4821 as containing high evidence supporting a willful trade secret violation.",
    "type": "ai_decision", "timestamp": "2026-07-16T14:30:00Z", "caseId": "case_001", "caseName": "Meridian v. Atlas",
    "userId": "usr_002", "userName": "Legal Review Agent", "priority": "high", "metadata": {"confidence": "94.2%"}
  },
]

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
                    "caseId": str(doc.case_id or "case_unknown"),
                    "caseName": "Case Ingestion Review",
                    "userId": "sys",
                    "userName": "TimelineAgent",
                    "priority": "medium",
                    "metadata": {"document_id": str(doc.id)},
                    "source": "live"
                })

    if live_events:
        events = live_events
    else:
        # Use mock events with source marked
        events = []
        for e in MOCK_EVENTS:
            e_copy = dict(e)
            e_copy["source"] = "mock_fallback"
            events.append(e_copy)

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

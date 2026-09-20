import uuid
import networkx as nx
from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.document_service import DocumentService
from app.auth.dependencies import get_current_user, TokenPayload

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

class NodeResponse(BaseModel):
    id: str
    label: str
    type: str
    metadata: Dict[str, str] = Field(default_factory=dict)
    importance: float = 0.5
    description: Optional[str] = None

class EdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    label: str
    type: str
    weight: float
    metadata: Optional[Dict[str, str]] = None

class GraphResponse(BaseModel):
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    source: str = "live" # "live" | "mock_fallback"

class ShortestPathResponse(BaseModel):
    path: List[str]
    edges: List[str]
    totalWeight: float

MOCK_NODES = [
  {"id": "gn_001", "label": "Meridian Corp.", "type": "organization", "metadata": {"role": "plaintiff", "headquarters": "San Jose, CA"}, "importance": 0.95, "description": "Plaintiff corporation claiming patent infringement."},
  {"id": "gn_002", "label": "Atlas Industries", "type": "organization", "metadata": {"role": "defendant", "headquarters": "Austin, TX"}, "importance": 0.92, "description": "Defendant corporation accused of trade secret theft."},
  {"id": "gn_003", "label": "Dr. James Whitfield", "type": "person", "metadata": {"role": "Lead Scientist", "employer": "Meridian Corp."}, "importance": 0.88, "description": "Co-inventor of the contested semiconductor process."},
  {"id": "gn_004", "label": "Patent US-2024-0089123", "type": "document", "metadata": {"type": "patent", "date": "2024-03-12"}, "importance": 0.90, "description": "Contested patent on semiconductor manufacturing."},
  {"id": "gn_005", "label": "San Jose, CA", "type": "location", "metadata": {"state": "California"}, "importance": 0.5},
  {"id": "gn_006", "label": "Greenfield Partners", "type": "organization", "metadata": {"role": "investor"}, "importance": 0.7},
  {"id": "gn_007", "label": "SEC", "type": "organization", "metadata": {"role": "regulatory_body"}, "importance": 0.8},
  {"id": "gn_008", "label": "Board Meeting Q1", "type": "event", "metadata": {"date": "2026-03-15"}, "importance": 0.65},
  {"id": "gn_009", "label": "Thornton Family", "type": "person", "metadata": {"role": "beneficiary"}, "importance": 0.75},
  {"id": "gn_010", "label": "Will Amendment", "type": "document", "metadata": {"year": "2019"}, "importance": 0.85},
  {"id": "gn_011", "label": "Dr. Linda Vance", "type": "person", "metadata": {"role": "Expert Witness", "field": "Semiconductors"}, "importance": 0.8},
  {"id": "gn_012", "label": "Source Code Repository", "type": "evidence", "metadata": {"type": "git_repo", "hash": "sha256:8f9a2b"}, "importance": 0.85},
  {"id": "gn_013", "label": "NDA Agreement", "type": "contract", "metadata": {"signed": "2023-05-14"}, "importance": 0.78},
  {"id": "gn_014", "label": "John Miller", "type": "person", "metadata": {"role": "Former Employee", "target": "Atlas Industries"}, "importance": 0.82},
  {"id": "gn_015", "label": "Email Thread #41", "type": "email", "metadata": {"subject": "Project Phoenix Specs"}, "importance": 0.75},
  {"id": "gn_016", "label": "Austin, TX", "type": "location", "metadata": {"state": "Texas"}, "importance": 0.4},
  {"id": "gn_017", "label": "IP Theft Allegation", "type": "legal_issue", "metadata": {"status": "contested"}, "importance": 0.9},
  {"id": "gn_018", "label": "Damages Estimation", "type": "legal_issue", "metadata": {"value": "$45M"}, "importance": 0.82},
  {"id": "gn_019", "label": "Deposition of Whitfield", "type": "event", "metadata": {"date": "2026-06-12"}, "importance": 0.72},
  {"id": "gn_020", "label": "Deposition of Miller", "type": "event", "metadata": {"date": "2026-06-18"}, "importance": 0.74},
  {"id": "gn_021", "label": "Meridian Lab Report", "type": "document", "metadata": {"type": "R&D"}, "importance": 0.65},
  {"id": "gn_022", "label": "Atlas Technical Spec", "type": "document", "metadata": {"type": "Blueprint"}, "importance": 0.78},
  {"id": "gn_023", "label": "David Ross", "type": "person", "metadata": {"role": "Attorney", "firm": "Westlake"}, "importance": 0.6},
  {"id": "gn_024", "label": "Patent Office", "type": "organization", "metadata": {"country": "US"}, "importance": 0.72},
  {"id": "gn_025", "label": "Court Hearing Q2", "type": "event", "metadata": {"date": "2026-05-20"}, "importance": 0.8},
  {"id": "gn_026", "label": "Bank Wire Transfer", "type": "evidence", "metadata": {"amount": "$1.2M"}, "importance": 0.79},
  {"id": "gn_027", "label": "Swiss Bank Account", "type": "location", "metadata": {"country": "Switzerland"}, "importance": 0.65},
  {"id": "gn_028", "label": "Consulting Contract", "type": "contract", "metadata": {"status": "terminated"}, "importance": 0.7},
  {"id": "gn_029", "label": "Robert Chen", "type": "person", "metadata": {"role": "CEO", "company": "Atlas Industries"}, "importance": 0.86},
  {"id": "gn_030", "label": "Alice Thompson", "type": "person", "metadata": {"role": "VP Engineering", "company": "Meridian"}, "importance": 0.81},
  {"id": "gn_031", "label": "Subpoena Document", "type": "document", "metadata": {"date": "2026-04-10"}, "importance": 0.75},
  {"id": "gn_032", "label": "Meeting Audio Recording", "type": "evidence", "metadata": {"type": "audio"}, "importance": 0.68},
  {"id": "gn_033", "label": "Chat Log Export", "type": "evidence", "metadata": {"platform": "Slack"}, "importance": 0.73},
  {"id": "gn_034", "label": "Vance Expert Report", "type": "document", "metadata": {"date": "2026-07-02"}, "importance": 0.84},
  {"id": "gn_035", "label": "Prior Art Search", "type": "document", "metadata": {"scope": "global"}, "importance": 0.62},
  {"id": "gn_036", "label": "Development Server Log", "type": "evidence", "metadata": {"type": "network_log"}, "importance": 0.77},
  {"id": "gn_037", "label": "System Access Log", "type": "evidence", "metadata": {"type": "security_log"}, "importance": 0.8},
  {"id": "gn_038", "label": "Joint Defense Agreement", "type": "contract", "metadata": {"type": "legal"}, "importance": 0.72},
  {"id": "gn_039", "label": "London, UK", "type": "location", "metadata": {"region": "Europe"}, "importance": 0.3},
  {"id": "gn_040", "label": "IPO Filing Draft", "type": "document", "metadata": {"status": "draft"}, "importance": 0.67},
  {"id": "gn_041", "label": "Forensic Copy Disk", "type": "evidence", "metadata": {"status": "verified"}, "importance": 0.85},
]

MOCK_EDGES = [
  {"id": "ge_001", "source": "gn_001", "target": "gn_002", "label": "filed against", "type": "relationship", "weight": 0.95},
  {"id": "ge_002", "source": "gn_003", "target": "gn_004", "label": "inventor of", "type": "relationship", "weight": 0.98},
  {"id": "ge_003", "source": "gn_001", "target": "gn_004", "label": "owns", "type": "ownership", "weight": 0.9},
  {"id": "ge_004", "source": "gn_003", "target": "gn_005", "label": "based in", "type": "relationship", "weight": 0.6},
  {"id": "ge_005", "source": "gn_006", "target": "gn_007", "label": "investigated by", "type": "relationship", "weight": 0.85},
  {"id": "ge_006", "source": "gn_006", "target": "gn_008", "label": "held", "type": "relationship", "weight": 0.7},
  {"id": "ge_007", "source": "gn_009", "target": "gn_010", "label": "contested", "type": "relationship", "weight": 0.88},
  {"id": "ge_008", "source": "gn_002", "target": "gn_004", "label": "allegedly infringes", "type": "citation", "weight": 0.84},
  {"id": "ge_009", "source": "gn_011", "target": "gn_001", "label": "retained by", "type": "relationship", "weight": 0.8},
  {"id": "ge_010", "source": "gn_012", "target": "gn_002", "label": "found on", "type": "evidence_link", "weight": 0.92},
  {"id": "ge_011", "source": "gn_014", "target": "gn_013", "label": "bound by", "type": "ownership", "weight": 0.85},
  {"id": "ge_012", "source": "gn_014", "target": "gn_001", "label": "formerly employed by", "type": "relationship", "weight": 0.75},
  {"id": "ge_013", "source": "gn_014", "target": "gn_002", "label": "hired by", "type": "relationship", "weight": 0.88},
  {"id": "ge_014", "source": "gn_015", "target": "gn_014", "label": "sent by", "type": "communication", "weight": 0.9},
  {"id": "ge_015", "source": "gn_015", "target": "gn_029", "label": "received by", "type": "communication", "weight": 0.9},
  {"id": "ge_016", "source": "gn_002", "target": "gn_016", "label": "headquartered in", "type": "relationship", "weight": 0.7},
  {"id": "ge_017", "source": "gn_017", "target": "gn_001", "label": "raised by", "type": "relationship", "weight": 0.95},
  {"id": "ge_018", "source": "gn_017", "target": "gn_002", "label": "concerns", "type": "relationship", "weight": 0.9},
  {"id": "ge_019", "source": "gn_018", "target": "gn_017", "label": "stems from", "type": "relationship", "weight": 0.8},
  {"id": "ge_020", "source": "gn_019", "target": "gn_003", "label": "questioned", "type": "relationship", "weight": 0.75},
  {"id": "ge_021", "source": "gn_020", "target": "gn_014", "label": "questioned", "type": "relationship", "weight": 0.78},
  {"id": "ge_022", "source": "gn_021", "target": "gn_003", "label": "authored by", "type": "relationship", "weight": 0.85},
  {"id": "ge_023", "source": "gn_022", "target": "gn_029", "label": "authorized by", "type": "relationship", "weight": 0.8},
  {"id": "ge_024", "source": "gn_021", "target": "gn_022", "label": "highly similar to", "type": "similarity", "weight": 0.89},
  {"id": "ge_025", "source": "gn_023", "target": "gn_001", "label": "represents", "type": "relationship", "weight": 0.9},
  {"id": "ge_026", "source": "gn_004", "target": "gn_024", "label": "registered with", "type": "relationship", "weight": 0.95},
  {"id": "ge_027", "source": "gn_025", "target": "gn_023", "label": "attended by", "type": "relationship", "weight": 0.75},
  {"id": "ge_028", "source": "gn_026", "target": "gn_027", "label": "routed to", "type": "evidence_link", "weight": 0.82},
  {"id": "ge_029", "source": "gn_026", "target": "gn_002", "label": "funded by", "type": "evidence_link", "weight": 0.88},
  {"id": "ge_030", "source": "gn_014", "target": "gn_026", "label": "beneficial owner", "type": "ownership", "weight": 0.93},
  {"id": "ge_031", "source": "gn_028", "target": "gn_014", "label": "executed with", "type": "ownership", "weight": 0.75},
  {"id": "ge_032", "source": "gn_030", "target": "gn_001", "label": "manages", "type": "relationship", "weight": 0.85},
  {"id": "ge_033", "source": "gn_030", "target": "gn_015", "label": "mentioned in", "type": "mentions", "weight": 0.7},
  {"id": "ge_034", "source": "gn_031", "target": "gn_002", "label": "served to", "type": "relationship", "weight": 0.85},
  {"id": "ge_035", "source": "gn_032", "target": "gn_014", "label": "records voice of", "type": "evidence_link", "weight": 0.82},
  {"id": "ge_036", "source": "gn_032", "target": "gn_029", "label": "records voice of", "type": "evidence_link", "weight": 0.84},
  {"id": "ge_037", "source": "gn_033", "target": "gn_014", "label": "involves chat of", "type": "evidence_link", "weight": 0.75},
  {"id": "ge_038", "source": "gn_034", "target": "gn_011", "label": "written by", "type": "relationship", "weight": 0.98},
  {"id": "ge_039", "source": "gn_034", "target": "gn_021", "label": "cites", "type": "citation", "weight": 0.9},
  {"id": "ge_040", "source": "gn_034", "target": "gn_022", "label": "cites", "type": "citation", "weight": 0.92},
  {"id": "ge_041", "source": "gn_035", "target": "gn_004", "label": "references", "type": "references", "weight": 0.85},
  {"id": "ge_042", "source": "gn_036", "target": "gn_012", "label": "logs access to", "type": "evidence_link", "weight": 0.87},
  {"id": "ge_043", "source": "gn_037", "target": "gn_014", "label": "records session of", "type": "evidence_link", "weight": 0.91},
  {"id": "ge_044", "source": "gn_038", "target": "gn_002", "label": "protects", "type": "relationship", "weight": 0.8},
  {"id": "ge_045", "source": "gn_014", "target": "gn_039", "label": "traveled to", "type": "relationship", "weight": 0.65},
  {"id": "ge_046", "source": "gn_040", "target": "gn_001", "label": "planned by", "type": "relationship", "weight": 0.78},
  {"id": "ge_047", "source": "gn_041", "target": "gn_014", "label": "cloned laptop of", "type": "evidence_link", "weight": 0.95},
  {"id": "ge_048", "source": "gn_029", "target": "gn_002", "label": "directs", "type": "relationship", "weight": 0.9},
  {"id": "ge_049", "source": "gn_028", "target": "gn_002", "label": "drafted by", "type": "references", "weight": 0.6},
  {"id": "ge_050", "source": "gn_013", "target": "gn_001", "label": "entered with", "type": "references", "weight": 0.8},
]

import json
from collections import Counter, defaultdict
from sqlalchemy import select
from app.models.case import Case
from app.models.document import Document
from app.auth.dependencies import UserRole
from app.services.entity_resolution import EntityResolutionService
from app.services.edge_weighting import EdgeWeightingService, should_suppress_edge, should_suppress_node
from app.services.centrality_service import CentralityService

def _resolve_link_node(raw_id: str, doc_node_id: str, doc_id_str: str, doc_filename: str, resolver: EntityResolutionService) -> str:
    if raw_id == doc_id_str or raw_id == doc_filename:
        return doc_node_id
    raw_str = str(raw_id)
    for cat_prefix in ("People_", "Organizations_", "Locations_", "Dates_", "Money_", "Cases_", "Courts_"):
        if raw_str.startswith(cat_prefix):
            cat = cat_prefix[:-1].lower()
            name = raw_str[len(cat_prefix):]
            return resolver.resolve(name, cat)[0]
    return resolver.resolve(raw_str, "entity")[0]

async def _build_knowledge_graph(
    db: AsyncSession,
    current_user: TokenPayload,
    case_id: Optional[uuid.UUID] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    if case_id and current_user.role != UserRole.ADMIN:
        case = await db.get(Case, case_id)
        if not case or case.created_by != current_user.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case graph")

    stmt = (
        select(Document.id, Document.original_filename, Document.file_size, Document.doc_metadata)
        .outerjoin(Case, Document.case_id == Case.id)
        .where(Document.doc_metadata.isnot(None))
        .order_by(Document.created_at.desc())
    )
    if case_id:
        stmt = stmt.where(Document.case_id == case_id)
    elif current_user.role != UserRole.ADMIN:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except (ValueError, TypeError):
            user_uuid = None
        filter_cond = (Case.created_by == current_user.sub)
        if user_uuid is not None:
            filter_cond = filter_cond | ((Document.case_id.is_(None)) & (Document.uploaded_by == user_uuid))
        stmt = stmt.where(filter_cond)

    if limit:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    docs = result.all()

    # Step 1: Collect all entity mentions across documents for global canonical resolution
    mentions_by_type: Dict[str, Counter] = defaultdict(Counter)
    for doc in docs:
        meta = doc.doc_metadata or {}
        doc_entities = meta.get("entities", {})
        if isinstance(doc_entities, dict):
            for cat, items in doc_entities.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str) and item.strip():
                            mentions_by_type[cat][item.strip()] += 1

    resolver = EntityResolutionService()
    resolver.cluster_entities(mentions_by_type)
    edge_weighting = EdgeWeightingService()

    live_nodes = []
    seen_nodes = set()
    entity_lookup = {}  # cid -> (label, type)

    # Accumulators for edge weighting & evidence retention
    doc_mentions_tf: Dict[Tuple[str, str], int] = Counter()  # (doc_node_id, cid) -> tf
    doc_mentions_cat: Dict[Tuple[str, str], str] = {}        # (doc_node_id, cid) -> cat

    inter_entity_pairs: Dict[Tuple[str, str], Set[str]] = defaultdict(set) # pair -> set(filenames)
    pair_freq: Dict[Tuple[str, str], int] = Counter()                       # pair -> int
    pair_relations: Dict[Tuple[str, str], Counter] = defaultdict(Counter)   # pair -> Counter(relations)
    pair_direction: Dict[Tuple[str, str], Tuple[str, str]] = {}             # pair -> (src_id, tgt_id)

    for doc in docs:
        doc_id_str = str(doc.id)
        doc_node_id = f"doc_{doc_id_str[:8]}"
        doc_filename = doc.original_filename
        meta = doc.doc_metadata or {}

        # Add document node
        if doc_node_id not in seen_nodes:
            seen_nodes.add(doc_node_id)
            live_nodes.append({
                "id": doc_node_id,
                "label": doc.original_filename,
                "type": "document",
                "metadata": {"file_size": str(doc.file_size or 0)},
                "importance": 0.9,
                "description": f"Document: {doc.original_filename}"
            })

        # Add canonical entity nodes & accumulate mentions containment
        doc_entities = meta.get("entities", {})
        if isinstance(doc_entities, dict):
            for cat, items in doc_entities.items():
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, str) or not item.strip():
                            continue
                        cid, clabel, ctype = resolver.resolve(item.strip(), cat)
                        entity_lookup[cid] = (clabel, ctype)
                        if should_suppress_node(clabel, ctype):
                            continue
                        if cid not in seen_nodes:
                            seen_nodes.add(cid)
                            live_nodes.append({
                                "id": cid,
                                "label": clabel,
                                "type": ctype,
                                "metadata": {"category": cat},
                                "importance": 0.75,
                                "description": f"Entity {clabel} ({ctype})"
                            })

                        mention_key = (doc_node_id, cid)
                        doc_mentions_tf[mention_key] += 1
                        doc_mentions_cat[mention_key] = cat

        # Remap and accumulate relationship links across documents
        graph_data = meta.get("graph_data") or meta.get("graph") or {}
        for link in graph_data.get("links", []):
            src_raw = link.get("source")
            tgt_raw = link.get("target")
            if not src_raw or not tgt_raw:
                continue

            src_id = _resolve_link_node(src_raw, doc_node_id, doc_id_str, doc_filename, resolver)
            tgt_id = _resolve_link_node(tgt_raw, doc_node_id, doc_id_str, doc_filename, resolver)

            if src_id == tgt_id:
                continue

            # Only accumulate genuine inter-entity links; document containment ties are synthesized in Section 1
            if str(src_id).startswith("doc_") or str(tgt_id).startswith("doc_"):
                continue

            pair_key = (src_id, tgt_id) if str(src_id) < str(tgt_id) else (tgt_id, str(src_id))
            if pair_key not in pair_direction:
                pair_direction[pair_key] = (src_id, tgt_id)

            inter_entity_pairs[pair_key].add(doc_filename)
            pair_freq[pair_key] += 1
            rel_label = link.get("relation") or link.get("label") or "communication"
            pair_relations[pair_key][rel_label] += 1

    live_edges = []

    # 1. Synthesize document-to-entity mentions edges
    for (doc_node_id, cid), tf in doc_mentions_tf.items():
        cat = doc_mentions_cat.get((doc_node_id, cid), "entity")
        weight = edge_weighting.compute_document_mention_weight(tf)
        live_edges.append({
            "id": f"ge_live_{uuid.uuid4().hex[:6]}",
            "source": doc_node_id,
            "target": cid,
            "label": f"MENTIONS_{cat.upper()}",
            "type": "relationship",
            "weight": weight,
            "metadata": {
                "term_frequency": str(tf),
                "containment_type": cat,
                "weight_rationale": f"Mentions containment weight {weight:.4f} derived from term_frequency={tf}"
            }
        })

    # 2. Synthesize calibrated inter-entity relationship edges
    for pair_key, dset in inter_entity_pairs.items():
        src_id, tgt_id = pair_direction[pair_key]
        src_info = entity_lookup.get(src_id, (src_id, "unknown"))
        tgt_info = entity_lookup.get(tgt_id, (tgt_id, "unknown"))
        src_name, src_cat = src_info[0], src_info[1]
        tgt_name, tgt_cat = tgt_info[0], tgt_info[1]

        # Policy 2 suppression: exclude protocol artifacts and unresolvable single-token person fragments
        if should_suppress_edge(src_name, src_cat, tgt_name, tgt_cat):
            continue

        d = len(dset)
        f = pair_freq[pair_key]
        relations = pair_relations[pair_key]
        primary_rel = relations.most_common(1)[0][0] if relations else "communication"

        weight = edge_weighting.compute_inter_entity_weight(d, f, primary_rel)
        rationale = edge_weighting.generate_weight_rationale(d, f, weight, primary_rel)
        doc_sample = sorted(list(dset))[:5]
        rel_breakdown = ", ".join(f"{r}: {c}" for r, c in relations.items())

        live_edges.append({
            "id": f"ge_live_{uuid.uuid4().hex[:6]}",
            "source": src_id,
            "target": tgt_id,
            "label": primary_rel,
            "type": "relationship",
            "weight": weight,
            "metadata": {
                "shared_doc_count": str(d),
                "interaction_count": str(f),
                "relation_types": rel_breakdown,
                "evidence_doc_ids": json.dumps(doc_sample),
                "weight_rationale": rationale
            }
        })


    if live_nodes:
        # Step 3: Compute real weighted degree centrality for entity nodes
        # Document nodes (type == 'document') retain their hardcoded importance (0.9).
        # Entity-entity edges are filtered from live_edges (excluding document-mention edges)
        # Note: Baseline latency is ~9.68s across 424 documents primarily due to the
        # full document metadata traversal and entity resolution loop (lines 206-330).
        centrality_service = CentralityService()
        inter_entity_edges = [
            e for e in live_edges
            if not str(e["source"]).startswith("doc_")
            and not str(e["target"]).startswith("doc_")
            and e.get("type") != "mentions"
        ]
        live_nodes = centrality_service.apply_centrality_to_nodes(live_nodes, inter_entity_edges)

        nodes = live_nodes
        edges = live_edges
        source_val = "live"
    else:
        # Fall back to mock with source set to mock_fallback
        nodes = []
        for n in MOCK_NODES:
            nodes.append(dict(n))
        edges = []
        for e in MOCK_EDGES:
            edges.append(dict(e))
        source_val = "mock_fallback"

    return {"nodes": nodes, "edges": edges, "source": source_val}


@router.get("", response_model=GraphResponse, summary="Get full knowledge graph data")
async def get_graph(
    min_weight: float = Query(0.1, ge=0.0, le=1.0, alias="minWeight"),
    node_types: Optional[List[str]] = Query(None, alias="nodeTypes"),
    edge_types: Optional[List[str]] = Query(None, alias="edgeTypes"),
    search: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, description="Optional limit of documents to process; defaults to all documents"),
    case_id: Optional[uuid.UUID] = Query(None, alias="caseId"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    graph_data = await _build_knowledge_graph(
        db=db,
        current_user=current_user,
        case_id=case_id,
        limit=limit,
    )
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]
    source_val = graph_data["source"]

    if node_types:
        nodes = [n for n in nodes if n["type"] in node_types]
        
    if search:
        query = search.lower()
        matched = []
        for n in nodes:
            score = 0
            if query in n["label"].lower():
                score += 10
            if n.get("description") and query in n["description"].lower():
                score += 4
            for val in n.get("metadata", {}).values():
                if query in str(val).lower():
                    score += 3
            if score > 0:
                matched.append(n)
        nodes = matched

    # Filter edges to only connect active nodes
    active_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in active_ids and e["target"] in active_ids]

    if edge_types:
        edges = [e for e in edges if e["type"] in edge_types]
    
    edges = [e for e in edges if e["weight"] >= min_weight]
    
    return {"nodes": nodes, "edges": edges, "source": source_val}

@router.get("/expand/{node_id}", response_model=GraphResponse, summary="Expand a node (fetch neighbors)")
async def expand_node(
    node_id: str,
    case_id: Optional[uuid.UUID] = Query(None, alias="caseId"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    graph_data = await _build_knowledge_graph(
        db=db,
        current_user=current_user,
        case_id=case_id,
    )
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]
    source_val = graph_data["source"]

    connected_edges = [e for e in edges if e["source"] == node_id or e["target"] == node_id]
    connected_node_ids = {node_id}
    for e in connected_edges:
        connected_node_ids.add(e["source"])
        connected_node_ids.add(e["target"])
        
    connected_nodes = [n for n in nodes if n["id"] in connected_node_ids]
    return {"nodes": connected_nodes, "edges": connected_edges, "source": source_val}

@router.get("/shortest-path", response_model=ShortestPathResponse, summary="Find shortest path between two nodes")
async def find_shortest_path(
    source: str,
    target: str,
    case_id: Optional[uuid.UUID] = Query(None, alias="caseId"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    graph_data = await _build_knowledge_graph(
        db=db,
        current_user=current_user,
        case_id=case_id,
    )
    edges = graph_data["edges"]

    G = nx.Graph()
    for e in edges:
        G.add_edge(e["source"], e["target"], id=e["id"], weight=e["weight"])

    if source not in G or target not in G or not nx.has_path(G, source, target):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No path discovered between target nodes."
        )

    path = nx.shortest_path(G, source=source, target=target)
    edges_path = []
    total_weight = 0.0
    for u, v in zip(path[:-1], path[1:]):
        edge_data = G.get_edge_data(u, v)
        edges_path.append(edge_data.get("id", ""))
        total_weight += edge_data.get("weight", 0.0)

    return {
        "path": path,
        "edges": edges_path,
        "totalWeight": round(total_weight, 4)
    }

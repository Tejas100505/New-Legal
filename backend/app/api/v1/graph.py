import uuid
import networkx as nx
from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Tuple
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
    source: str = "live"  # data provenance: "live" = from pipeline extraction

class ShortestPathResponse(BaseModel):
    path: List[str]
    edges: List[str]
    totalWeight: float



import json
from collections import Counter, defaultdict
from sqlalchemy import select
from app.models.case import Case
from app.models.document import Document
from app.auth.dependencies import UserRole
from app.services.entity_resolution import EntityResolutionService
from app.services.edge_weighting import EdgeWeightingService, should_suppress_edge, should_suppress_node
from app.services.centrality_service import CentralityService
import time
from loguru import logger


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

    t_start = time.perf_counter()
    result = await db.execute(stmt)
    docs = result.all()
    t_db = time.perf_counter() - t_start

    # Step 1: Collect all entity mentions across documents for global canonical resolution
    t_cluster_start = time.perf_counter()
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
    t_cluster = time.perf_counter() - t_cluster_start
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

    t_assembly_start = time.perf_counter()
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

    t_assembly = time.perf_counter() - t_assembly_start

    t_edges_start = time.perf_counter()
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

    t_edges = time.perf_counter() - t_edges_start

    t_centrality_start = time.perf_counter()
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
        # Honest empty state when no graph nodes or documents are available
        nodes = []
        edges = []
        source_val = "empty"

    t_centrality = time.perf_counter() - t_centrality_start
    t_total = time.perf_counter() - t_start
    logger.info(
        f"[KnowledgeGraph Build Timings] t_db={t_db:.3f}s, t_cluster={t_cluster:.3f}s, "
        f"t_assembly={t_assembly:.3f}s, t_edges={t_edges:.3f}s, t_centrality={t_centrality:.3f}s, "
        f"total={t_total:.3f}s"
    )

    return {"nodes": nodes, "edges": edges, "source": source_val}


# ── Process-Local State-Fingerprinted Graph Cache ─────────────────────────────

class GraphCache:
    """
    Process-local, in-memory, state-fingerprinted cache for Knowledge Graph responses.

    ARCHITECTURAL TRADEOFF & CONSTRAINTS (Zero-Cost / Free-Tier Decision):
    - This cache is process-local (in-memory dict with LRU eviction).
    - It does NOT synchronize across multiple Uvicorn worker processes.
      This is an explicitly accepted architectural tradeoff: the Knowledge Graph
      is a read-heavy analytical/investigative view, not a security-critical
      revocation path (such as JWT revocation).
    - Automatic invalidation is guaranteed by the state fingerprint key: any document
      insertion, deletion, or metadata update changes the (COUNT, MAX(updated_at))
      fingerprint, cleanly bypassing stale entries without external coordination.
    """

    def __init__(self, max_entries: int = 32):
        self._cache: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self._keys_lru: List[Tuple[str, str, str]] = []
        self._max_entries = max_entries
        self.hits: int = 0
        self.misses: int = 0

    def get(self, key: Tuple[str, str, str]) -> Optional[Dict[str, Any]]:
        if key in self._cache:
            self.hits += 1
            if key in self._keys_lru:
                self._keys_lru.remove(key)
            self._keys_lru.append(key)
            cached = self._cache[key]
            # Return shallow copy of node and edge lists to prevent in-place mutation
            return {
                "nodes": list(cached["nodes"]),
                "edges": list(cached["edges"]),
                "source": cached["source"]
            }
        self.misses += 1
        return None

    def set(self, key: Tuple[str, str, str], value: Dict[str, Any]) -> None:
        if key in self._cache:
            if key in self._keys_lru:
                self._keys_lru.remove(key)
        elif len(self._cache) >= self._max_entries:
            oldest_key = self._keys_lru.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = {
            "nodes": list(value["nodes"]),
            "edges": list(value["edges"]),
            "source": value["source"]
        }
        self._keys_lru.append(key)

    def clear(self) -> None:
        self._cache.clear()
        self._keys_lru.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self._cache),
            "max_entries": self._max_entries,
        }


graph_cache = GraphCache(max_entries=32)


def clear_graph_cache() -> None:
    """Helper for testing and cache reset."""
    graph_cache.clear()


async def compute_graph_fingerprint(
    db: AsyncSession,
    current_user: TokenPayload,
    case_id: Optional[uuid.UUID] = None,
    limit: Optional[int] = None,
) -> str:
    """
    Computes a lightweight state fingerprint for the current graph scope.
    Executes a fast aggregate query (COUNT + MAX(updated_at)) taking ~1-2ms,
    avoiding any loading or deserialization of heavy doc_metadata JSONB blobs.
    """
    from sqlalchemy import func
    fp_stmt = (
        select(
            func.count(Document.id),
            func.max(func.coalesce(Document.updated_at, Document.created_at))
        )
        .outerjoin(Case, Document.case_id == Case.id)
        .where(Document.doc_metadata.isnot(None))
    )
    if case_id:
        fp_stmt = fp_stmt.where(Document.case_id == case_id)
    elif current_user.role != UserRole.ADMIN:
        try:
            user_uuid = uuid.UUID(current_user.sub)
        except (ValueError, TypeError):
            user_uuid = None
        filter_cond = (Case.created_by == current_user.sub)
        if user_uuid is not None:
            filter_cond = filter_cond | ((Document.case_id.is_(None)) & (Document.uploaded_by == user_uuid))
        fp_stmt = fp_stmt.where(filter_cond)

    fp_res = await db.execute(fp_stmt)
    count_val, max_dt = fp_res.first()
    dt_str = max_dt.isoformat() if max_dt else "none"
    return f"{count_val}_{dt_str}_{limit or 'all'}"


async def get_knowledge_graph_cached(
    db: AsyncSession,
    current_user: TokenPayload,
    case_id: Optional[uuid.UUID] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieves knowledge graph from in-memory cache if state fingerprint matches,
    otherwise runs full _build_knowledge_graph and populates cache.
    """
    # Verify case access upfront
    if case_id and current_user.role != UserRole.ADMIN:
        case = await db.get(Case, case_id)
        if not case or case.created_by != current_user.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this case graph")

    t_fp_start = time.perf_counter()
    fingerprint = await compute_graph_fingerprint(db, current_user, case_id, limit)
    t_fp = time.perf_counter() - t_fp_start

    scope_case = str(case_id) if case_id else "global"
    scope_user = current_user.sub if current_user.role != UserRole.ADMIN else "admin"
    cache_key = (scope_case, scope_user, fingerprint)

    cached = graph_cache.get(cache_key)
    if cached is not None:
        logger.info(
            f"[KnowledgeGraph Cache HIT] key=({scope_case}, {scope_user}, {fingerprint}), "
            f"lookup_time={t_fp*1000:.2f}ms, nodes={len(cached['nodes'])}, edges={len(cached['edges'])}"
        )
        return cached

    logger.info(
        f"[KnowledgeGraph Cache MISS] key=({scope_case}, {scope_user}, {fingerprint}), "
        f"triggering full graph build"
    )
    built_graph = await _build_knowledge_graph(
        db=db,
        current_user=current_user,
        case_id=case_id,
        limit=limit,
    )
    graph_cache.set(cache_key, built_graph)
    return {
        "nodes": list(built_graph["nodes"]),
        "edges": list(built_graph["edges"]),
        "source": built_graph["source"],
    }


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
    graph_data = await get_knowledge_graph_cached(
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
    graph_data = await get_knowledge_graph_cached(
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
    graph_data = await get_knowledge_graph_cached(
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

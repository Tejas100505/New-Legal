"""
Case Intelligence Service.

Implements case-wide synthesis and executive summary generation from
pre-computed, structured document metadata without raw document text re-reading.
Follows the two-tier aggregation strategy, deterministic timeline aggregation,
and narrow top-N entity centrality queries.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.gemini_client import LLMClient, QuotaExhaustedException
from app.config import get_settings
from app.models.case import Case
from app.models.case_summary import CaseSummary, CaseSummaryStatus
from app.models.document import Document
from app.repositories.case_summary_repository import CaseSummaryRepository
from app.services.edge_weighting import EdgeWeightingService, should_suppress_edge, should_suppress_node
from app.services.centrality_service import CentralityService
from app.services.entity_resolution import EntityResolutionService


# Global LLM call tracker for test asserting and monitoring
_case_summary_llm_call_count = 0


def get_case_summary_llm_call_count() -> int:
    """Return the total number of LLM calls made by case_intelligence_service."""
    return _case_summary_llm_call_count


def reset_case_summary_llm_call_count() -> None:
    """Reset the LLM call counter."""
    global _case_summary_llm_call_count
    _case_summary_llm_call_count = 0


# ---------------------------------------------------------------------------
# 1. Deterministic Data Hashing (Staleness Invalidation)
# ---------------------------------------------------------------------------

def compute_case_data_hash(docs: Sequence[Document]) -> str:
    """
    Compute a deterministic SHA-256 hash over the case's document IDs and modification timestamps.
    Detects if documents are added, removed, or their processed state has changed.
    """
    sorted_docs = sorted(docs, key=lambda d: str(d.id))
    hasher = hashlib.sha256()
    for d in sorted_docs:
        ts = d.updated_at.isoformat() if d.updated_at else (d.created_at.isoformat() if d.created_at else "")
        status_val = str(d.status.value if hasattr(d.status, "value") else d.status)
        hasher.update(f"{d.id}:{status_val}:{ts};".encode("utf-8"))
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# 2. Narrow Top-N Entity Centrality Method
# ---------------------------------------------------------------------------

def _resolve_link_node_info(
    raw_id: str,
    doc_node_id: str,
    doc_id_str: str,
    doc_filename: str,
    resolver: EntityResolutionService,
) -> Tuple[str, str, str]:
    if raw_id == doc_id_str or raw_id == doc_filename:
        return doc_node_id, doc_filename, "document"
    raw_str = str(raw_id)
    for cat_prefix in ("People_", "Organizations_", "Locations_", "Dates_", "Money_", "Cases_", "Courts_"):
        if raw_str.startswith(cat_prefix):
            cat = cat_prefix[:-1].lower()
            name = raw_str[len(cat_prefix):]
            return resolver.resolve(name, cat)
    return resolver.resolve(raw_str, "entity")


async def get_case_top_entities(
    db: AsyncSession,
    case_id: uuid.UUID,
    n: int = 8,
    weight_floor: float = 0.5,
    docs: Optional[Sequence[Document]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve top-N canonical entity nodes by verified weighted degree centrality
    (CentralityService) and calibrated edge weights (EdgeWeightingService) for a case.
    Reuses Step 2 and Step 3 knowledge graph mathematical formulas directly against
    case-scoped entity metadata without assembling the full graph object, calling
    _build_knowledge_graph, or invoking internal system tokens.
    """
    if docs is None:
        stmt = (
            select(Document)
            .where(Document.case_id == case_id, Document.doc_metadata.isnot(None))
            .order_by(Document.created_at.desc())
        )
        result = await db.execute(stmt)
        docs = result.scalars().all()

    if not docs:
        return []

    # 1. Collect entity mentions across case documents for canonical resolution
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
    centrality_service = CentralityService()

    # 2. Extract entity nodes and inter-entity co-occurrence pairs
    entity_lookup: Dict[str, Tuple[str, str]] = {}  # cid -> (label, type)
    inter_entity_pairs: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    pair_freq: Dict[Tuple[str, str], int] = Counter()
    pair_relations: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    pair_direction: Dict[Tuple[str, str], Tuple[str, str]] = {}

    for doc in docs:
        doc_id_str = str(doc.id)
        doc_node_id = f"doc_{doc_id_str[:8]}"
        doc_filename = doc.original_filename
        meta = doc.doc_metadata or {}

        # Canonicalize doc entities
        doc_entities = meta.get("entities", {})
        if isinstance(doc_entities, dict):
            for cat, items in doc_entities.items():
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, str) or not item.strip():
                            continue
                        cid, clabel, ctype = resolver.resolve(item.strip(), cat)
                        if cid not in entity_lookup:
                            entity_lookup[cid] = (clabel, ctype)

        # Process relational links
        graph_data = meta.get("graph_data") or meta.get("graph") or {}
        for link in graph_data.get("links", []):
            src_raw = link.get("source")
            tgt_raw = link.get("target")
            if not src_raw or not tgt_raw:
                continue

            src_id, src_label, src_type = _resolve_link_node_info(src_raw, doc_node_id, doc_id_str, doc_filename, resolver)
            tgt_id, tgt_label, tgt_type = _resolve_link_node_info(tgt_raw, doc_node_id, doc_id_str, doc_filename, resolver)

            if src_id == tgt_id:
                continue
            if str(src_id).startswith("doc_") or str(tgt_id).startswith("doc_"):
                continue

            if src_id not in entity_lookup:
                entity_lookup[src_id] = (src_label, src_type)
            if tgt_id not in entity_lookup:
                entity_lookup[tgt_id] = (tgt_label, tgt_type)

            pair_key = (src_id, tgt_id) if str(src_id) < str(tgt_id) else (tgt_id, str(src_id))
            if pair_key not in pair_direction:
                pair_direction[pair_key] = (src_id, tgt_id)

            inter_entity_pairs[pair_key].add(doc_filename)
            pair_freq[pair_key] += 1
            rel_label = link.get("relation") or link.get("label") or "communication"
            pair_relations[pair_key][rel_label] += 1

    # 3. Calibrate inter-entity edge weights (EdgeWeightingService)
    inter_entity_edges: List[Dict[str, Any]] = []
    edges_by_node: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for pair_key, dset in inter_entity_pairs.items():
        src_id, tgt_id = pair_direction[pair_key]
        src_name, src_cat = entity_lookup.get(src_id, (src_id, "unknown"))
        tgt_name, tgt_cat = entity_lookup.get(tgt_id, (tgt_id, "unknown"))

        # Policy 2 suppression: exclude protocol artifacts and unresolvable single-token person fragments
        if should_suppress_edge(src_name, src_cat, tgt_name, tgt_cat):
            continue

        d = len(dset)
        f = pair_freq[pair_key]
        relations = pair_relations[pair_key]
        primary_rel = relations.most_common(1)[0][0] if relations else "communication"

        weight = edge_weighting.compute_inter_entity_weight(d, f, primary_rel)
        inter_entity_edges.append({
            "source": src_id,
            "target": tgt_id,
            "weight": weight,
            "type": "relationship",
        })

        if weight >= weight_floor:
            edges_by_node[src_id].append({
                "target": tgt_name,
                "relation": primary_rel,
                "weight": round(weight, 4),
                "shared_docs": d,
            })
            edges_by_node[tgt_id].append({
                "target": src_name,
                "relation": primary_rel,
                "weight": round(weight, 4),
                "shared_docs": d,
            })

    # 4. Compute node weighted degree centrality (CentralityService)
    candidate_nodes = [
        {"id": cid, "label": label, "type": ctype}
        for cid, (label, ctype) in entity_lookup.items()
    ]
    candidate_nodes = centrality_service.apply_centrality_to_nodes(candidate_nodes, inter_entity_edges)

    # Clean non-document entity nodes (suppress protocol/header noise & misclassified fragments)
    clean_nodes = [
        node for node in candidate_nodes
        if node.get("type") != "document"
        and node.get("metadata", {}).get("likely_misclassified") != "true"
        and not should_suppress_node(node.get("label", ""), node.get("type", ""))
        and node.get("type") not in ("date", "time")
    ]

    # Rank by verified importance score and weighted degree
    clean_nodes.sort(
        key=lambda x: (
            float(x.get("importance", 0.0)),
            float(x.get("metadata", {}).get("weighted_degree", 0.0)),
        ),
        reverse=True,
    )

    top_nodes = clean_nodes[:n]
    entities_output = []
    for node in top_nodes:
        nid = node["id"]
        deg_val = float(node.get("metadata", {}).get("weighted_degree", 0.0))
        incident_edges = sorted(edges_by_node[nid], key=lambda e: e["weight"], reverse=True)[:5]
        entities_output.append({
            "name": node.get("label"),
            "type": node.get("type"),
            "importance_score": node.get("importance", 0.05),
            "weighted_degree": round(deg_val, 4),
            "top_edges": incident_edges,
        })

    return entities_output


# ---------------------------------------------------------------------------
# 3. Deterministic Timeline Aggregation
# ---------------------------------------------------------------------------

def aggregate_case_timeline(
    docs: Sequence[Document],
    confidence_floor: float = 0.70,
) -> Dict[str, Any]:
    """
    Extract, deduplicate, and chronologically sort timeline events from doc_metadata.
    Computes case date range and chronological event sequence without LLM calls.
    Applies confidence floor and robustly separates core case activity period from historical citation outliers.
    """
    seen_events: Set[Tuple[str, str]] = set()
    events_list = []
    valid_dates = []

    for d in docs:
        meta = d.doc_metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        tl = meta.get("timeline") or []
        if isinstance(tl, list):
            for ev in tl:
                if not isinstance(ev, dict):
                    continue
                # Confidence floor check (Item 2)
                conf = float(ev.get("confidence", 1.0))
                if conf < confidence_floor:
                    continue

                date_str = str(ev.get("date") or ev.get("timestamp") or "").strip()
                title_str = str(ev.get("title") or ev.get("event") or ev.get("description") or "").strip()
                if not date_str or not title_str:
                    continue

                # Filter out obvious date parsing anomalies/artifacts:
                # E.g. '1930-05-20' caused by military time '1930 CET' on Sunday May 20
                # or '1979-12-31' Unix epoch zero fallback from corrupted email headers.
                try:
                    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    if dt.year < 1980 or dt.year > 2035:
                        continue
                    valid_dates.append(dt)
                except Exception:
                    # Non-standard date format; continue
                    pass

                event_key = (date_str[:10], title_str.lower()[:60])
                if event_key not in seen_events:
                    seen_events.add(event_key)
                    events_list.append({
                        "date": date_str,
                        "title": title_str,
                        "description": ev.get("description") or title_str,
                        "source_document": d.original_filename,
                        "source_doc_id": str(d.id)[:8],
                        "confidence": conf,
                    })

    # Sort chronologically
    events_list.sort(key=lambda e: e["date"])

    start_date = events_list[0]["date"] if events_list else None
    end_date = events_list[-1]["date"] if events_list else None

    # Robust core case activity boundary (2nd to 98th percentile when N >= 10)
    core_start = start_date
    core_end = end_date
    if len(valid_dates) >= 10:
        valid_dates.sort()
        ordinals = [d.toordinal() for d in valid_dates]
        p2_idx = max(0, int(len(ordinals) * 0.02))
        p98_idx = min(len(ordinals) - 1, int(len(ordinals) * 0.98))
        core_start = datetime.fromordinal(ordinals[p2_idx]).strftime("%Y-%m-%d")
        core_end = datetime.fromordinal(ordinals[p98_idx]).strftime("%Y-%m-%d")

    return {
        "total_timeline_events": len(events_list),
        "earliest_event_date": start_date,
        "latest_event_date": end_date,
        "core_activity_start_date": core_start,
        "core_activity_end_date": core_end,
        # Cap events passed into context to top 30 evenly distributed or key chronological events
        "chronological_events": events_list[:30],
    }


# ---------------------------------------------------------------------------
# 4. Tiered Input Aggregation Strategy
# ---------------------------------------------------------------------------

def build_tiered_inputs(
    docs: Sequence[Document],
    top_entities: List[Dict[str, Any]],
    timeline_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Assemble the bounded tiered input context:
    - Tier 1: All documents (minimal footprint: filename, risk, privilege, 120-char excerpt)
    - Tier 2: Notable documents only (privileged, high/critical risk, flagged)
    - Deterministic aggregates: counts, timeline, top entities
    """
    tier1_items = []
    tier2_items = []

    total_privileged = 0
    total_high_critical_risk = 0
    total_flagged = 0

    for d in docs:
        doc_id_str = str(d.id)
        doc_status_str = str(d.status.value if hasattr(d.status, "value") else d.status)
        meta = d.doc_metadata or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        # Authoritative privilege inspection
        pa = meta.get("privilege_analysis") or {}
        is_priv = pa.get("is_privileged") is True
        if is_priv:
            total_privileged += 1

        priv_type = None
        if is_priv:
            for det in pa.get("detections", []):
                if det.get("detected"):
                    priv_type = det.get("privilege_type")
                    break
            if not priv_type:
                priv_type = "Legal Counsel / Work Product Protection"

        # Risk inspection
        ra = meta.get("risk_analysis") or meta.get("risk") or {}
        risk_level = (ra.get("risk_level") or ra.get("overall_risk") or meta.get("risk_level") or "low").lower()
        if risk_level in ("high", "critical"):
            total_high_critical_risk += 1

        if doc_status_str == "flagged":
            total_flagged += 1

        # Summary excerpt
        sa = meta.get("summary") or {}
        exec_summary = ""
        if isinstance(sa, dict):
            exec_summary = sa.get("executive_summary") or sa.get("summary") or ""
        elif isinstance(sa, str):
            exec_summary = sa

        excerpt = exec_summary[:120].strip() if exec_summary else "Document processed in discovery corpus."

        # Tier 1 (All documents)
        tier1_items.append({
            "doc_id": doc_id_str[:8],
            "filename": d.original_filename,
            "risk": risk_level,
            "privileged": is_priv,
            "priv_type": priv_type if is_priv else None,
            "summary_excerpt": excerpt,
        })

        # Tier 2 (Notable documents: privileged, high/critical risk, or flagged)
        if is_priv or risk_level in ("high", "critical") or doc_status_str == "flagged":
            tier2_items.append({
                "doc_id": doc_id_str[:8],
                "filename": d.original_filename,
                "status": doc_status_str,
                "risk_level": risk_level,
                "risk_reasons": ra.get("risk_factors") or ra.get("key_risks") or ra.get("summary"),
                "is_privileged": is_priv,
                "privilege_type": priv_type,
                "privilege_reasoning": pa.get("reasoning"),
                "evidence_spans": pa.get("evidence_spans", [])[:3],
                "full_summary": exec_summary,
                "key_findings": sa.get("key_findings", []) if isinstance(sa, dict) else [],
            })

    return {
        "case_level_metrics": {
            "total_documents": len(docs),
            "privileged_documents_count": total_privileged,
            "high_or_critical_risk_count": total_high_critical_risk,
            "flagged_documents_count": total_flagged,
            "timeline_span": {
                "core_activity_start": timeline_summary.get("core_activity_start_date"),
                "core_activity_end": timeline_summary.get("core_activity_end_date"),
                "earliest_referenced_date": timeline_summary.get("earliest_event_date"),
                "latest_referenced_date": timeline_summary.get("latest_event_date"),
                "total_events": timeline_summary.get("total_timeline_events"),
            }
        },
        "tier1_corpus_overview": tier1_items,
        "tier2_notable_findings": tier2_items,
        "top_entities_centrality": top_entities,
        "timeline_events": timeline_summary.get("chronological_events", []),
    }


# ---------------------------------------------------------------------------
# 5. Core Case Summary Synthesis Function
# ---------------------------------------------------------------------------

async def generate_case_summary(
    db: AsyncSession,
    case_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> CaseSummary:
    """
    Synthesize and persist a case-level executive summary using the tiered aggregation strategy.
    
    Hard constraints:
    - Zero loop over individual documents
    - <= 3 LLM calls (hard ceiling 5)
    - Writes GENERATING row before LLM call starts
    - Atomic commit of COMPLETE status, summary_json, model_version, and generated_at
    - Concurrency check: returns 409 if GENERATING already in flight
    """
    global _case_summary_llm_call_count
    repo = CaseSummaryRepository(db)

    # 1. Concurrency guard check
    latest_existing = await repo.get_latest_by_case_id(case_id)
    if latest_existing and latest_existing.status == CaseSummaryStatus.GENERATING:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Summary generation already in progress for this case",
        )

    # 2. Fetch case and documents
    case = await db.get(Case, case_id)
    if not case:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    docs_stmt = select(Document).where(Document.case_id == case_id)
    docs_res = await db.execute(docs_stmt)
    docs = list(docs_res.scalars().all())

    if not docs:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate summary for a case with zero documents",
        )

    # 3. Compute data hash & write in-flight GENERATING record BEFORE LLM call
    current_hash = compute_case_data_hash(docs)
    summary_record = await repo.create(
        case_id=case_id,
        status=CaseSummaryStatus.GENERATING,
        source_doc_count=len(docs),
        source_data_hash=current_hash,
        generated_by=user_id,
        summary_json=None,
        model_version=None,
        generated_at=None,
    )
    await db.commit()
    summary_id = summary_record.id

    # 4. Prepare deterministic aggregates
    timeline_summary = aggregate_case_timeline(docs)
    top_entities = await get_case_top_entities(db, case_id, n=8, weight_floor=0.5, docs=docs)
    tiered_inputs = build_tiered_inputs(docs, top_entities, timeline_summary)

    # 5. Build prompt
    prompt = f"""You are a Senior Legal E-Discovery Architect producing an authoritative Case-Level Executive Summary for an active legal matter.

CASE DETAILS:
- Case Name: {case.name}
- Case Number: {case.case_number or "N/A"}
- Total Discovery Documents: {len(docs)}
- Case Metrics: {json.dumps(tiered_inputs["case_level_metrics"], indent=2)}

STRUCTURED INPUT DATA:
- TOP CENTRAL ENTITIES & RELATIONSHIPS (Weighted degree centrality & calibrated edges):
{json.dumps(tiered_inputs["top_entities_centrality"], indent=2)}

- KEY CHRONOLOGICAL TIMELINE EVENTS:
{json.dumps(tiered_inputs["timeline_events"], indent=2)}

TIMELINE CHRONOLOGY DIRECTIVE:
The case's active operational period is defined by:
- Core Case Activity Window: {tiered_inputs["case_level_metrics"]["timeline_span"]["core_activity_start"]} through {tiered_inputs["case_level_metrics"]["timeline_span"]["core_activity_end"]}
- Total Chronological Events: {tiered_inputs["case_level_metrics"]["timeline_span"]["total_events"]}
- Earliest Historical Reference: {tiered_inputs["case_level_metrics"]["timeline_span"]["earliest_referenced_date"]}
- Latest Document Date: {tiered_inputs["case_level_metrics"]["timeline_span"]["latest_referenced_date"]}
In the Executive section, characterize the case's active date range using the core activity period, clearly distinguishing any historical citations or external background dates from the core transactional conduct.

- TIER 2 NOTABLE FINDINGS (Privileged documents, high/critical risk files, flagged evidence):
{json.dumps(tiered_inputs["tier2_notable_findings"], indent=2)}

- TIER 1 CORPUS OVERVIEW (Summary excerpts across all {len(docs)} case documents):
{json.dumps(tiered_inputs["tier1_corpus_overview"], indent=2)}

CRITICAL INSTRUCTIONS:
1. Grounding: Only state claims strictly traceable to the structured input data provided above.
2. Citation: Cite source document filenames or doc_ids backing each key claim, liability finding, or privilege determination.
3. No Hallucination: Never invent case-wide contract clauses or facts not supported by the input findings.
4. Five Sections Required:
   - "executive": Concise high-level case summary and discovery narrative.
   - "legal": Legal posture, regulatory inquiries, litigation exposure, and primary defenses.
   - "notable_provisions_and_findings": Sourced strictly from the flagged privilege/risk/clustering findings.
   - "evidence": Analysis of key evidence, communications, and privileged document spans.
   - "key_people_and_relationships": Synthesis of the top central people, organizations, and their verified connections.

Respond with a single JSON object with the following exact keys:
{{
  "case_id": "{str(case_id)}",
  "case_name": "{case.name}",
  "generated_at": "{datetime.now(timezone.utc).isoformat()}",
  "metrics": {json.dumps(tiered_inputs["case_level_metrics"])},
  "sections": {{
    "executive": "...",
    "legal": "...",
    "notable_provisions_and_findings": "...",
    "evidence": "...",
    "key_people_and_relationships": "..."
  }},
  "top_entities": {json.dumps(top_entities)},
  "key_dates": {json.dumps(tiered_inputs["timeline_events"][:5])}
}}
"""

    # 6. Execute LLM call with structured instrumentation
    call_index = 1
    _case_summary_llm_call_count += 1
    logger.info(f"llm_call feature=case_summary case_id={case_id} call_index={call_index}")

    settings = get_settings()
    model_name = settings.google_model or "gemini-3.5-flash-lite"
    try:
        raw_response = await LLMClient.generate_text(
            prompt=prompt,
            model=model_name,
            json_mode=True,
        )

        # Parse JSON
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        summary_payload = json.loads(cleaned.strip())

        # Validate five required sections
        sections = summary_payload.get("sections", {})
        required_keys = ["executive", "legal", "notable_provisions_and_findings", "evidence", "key_people_and_relationships"]
        for rk in required_keys:
            if rk not in sections or not str(sections[rk]).strip():
                raise ValueError(f"Model output missing required section: '{rk}'")

        # 7. Success state: update row atomically to COMPLETE
        now = datetime.now(timezone.utc)
        completed_record = await repo.update_completed(
            summary_id,
            summary_json=summary_payload,
            model_version=model_name,
            generated_at=now,
        )
        await db.commit()
        return completed_record

    except QuotaExhaustedException as q_err:
        logger.warning(f"[CaseSummary] Quota exhausted for case {case_id}: {q_err}")
        await repo.update_status(summary_id, CaseSummaryStatus.QUOTA_PAUSED)
        await db.commit()
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM quota exhausted. Summary generation paused.",
        ) from q_err

    except Exception as exc:
        logger.error(f"[CaseSummary] Synthesis failed for case {case_id}: {exc}")
        await repo.update_status(summary_id, CaseSummaryStatus.FAILED)
        await db.commit()
        raise exc

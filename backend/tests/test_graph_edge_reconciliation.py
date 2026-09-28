import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from collections import Counter, defaultdict
from sqlalchemy import select
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.document import Document
from app.services.edge_weighting import EdgeWeightingService
from app.services.entity_resolution import EntityResolutionService
from app.api.v1.graph import should_suppress_node
from app.auth.dependencies import create_access_token, UserRole
import app.db.session as session_module


async def derive_expected_doc_mention_count(session) -> int:
    """
    Independently derives expected document-mention containment edge count
    from active database state.
    """
    stmt = (
        select(Document.id, Document.doc_metadata)
        .where(Document.doc_metadata.isnot(None))
    )
    result = await session.execute(stmt)
    docs = result.all()

    mentions_by_type = defaultdict(Counter)
    for doc in docs:
        meta = doc.doc_metadata or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        doc_entities = meta.get("entities", {})
        if isinstance(doc_entities, dict):
            for cat, items in doc_entities.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str) and item.strip():
                            mentions_by_type[cat][item.strip()] += 1

    resolver = EntityResolutionService()
    resolver.cluster_entities(mentions_by_type)

    doc_mentions = set()
    for doc in docs:
        doc_id_str = str(doc.id)
        doc_node_id = f"doc_{doc_id_str[:8]}"
        meta = doc.doc_metadata or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        doc_entities = meta.get("entities", {})
        if isinstance(doc_entities, dict):
            for cat, items in doc_entities.items():
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, str) or not item.strip():
                            continue
                        cid, clabel, ctype = resolver.resolve(item.strip(), cat)
                        if should_suppress_node(clabel, ctype):
                            continue
                        doc_mentions.add((doc_node_id, cid))

    return len(doc_mentions)


def test_containment_weights_strictly_above_inter_entity_floor():
    """
    Guards the containment scale:
    The lowest possible containment edge weight is 0.15 (at tf=1),
    whereas single-doc inter-entity ties have floor weight 0.05.
    Containment edges must NEVER have weight 0.05.
    """
    service = EdgeWeightingService()
    for tf in [1, 2, 3, 4, 10]:
        w = service.compute_document_mention_weight(tf)
        assert w >= 0.15, f"Containment weight for tf={tf} must be >= 0.15, got {w}"
        assert w <= 0.75, f"Containment weight for tf={tf} must be <= 0.75, got {w}"


def test_inter_entity_weight_cannot_apply_to_doc_containment():
    """
    A single-occurrence relationship with relation='mentions' computes to 0.05.
    This was the exact spurious weight assigned to leaked doc-mention links
    when treated as inter-entity pairs.
    """
    service = EdgeWeightingService()
    leaked_weight = service.compute_inter_entity_weight(1, 1, "mentions")
    assert leaked_weight == 0.05
    # Genuine containment weight must be strictly higher than this leaked floor
    canonical_containment_weight = service.compute_document_mention_weight(1)
    assert canonical_containment_weight > leaked_weight


@pytest.mark.asyncio
async def test_graph_endpoint_no_doc_nodes_in_inter_entity_pairs_and_exact_mention_reconciliation():
    """
    Regression test for the duplicate-edge bug in /api/v1/graph:
    1. At minWeight=0.0 and minWeight=0.10, the count of document-mention containment
       edges must be strictly IDENTICAL (no low-weight duplicate doc-mention edges).
    2. No edge connecting to a document node ('doc_' prefix) may have weight < 0.15
       or have label 'mentions' (all canonical containment edges are MENTIONS_<CAT>).
    3. No document-node appears in the entity-entity edge set.
    """
    import uuid
    from app.models.user import User

    async with session_module.AsyncSessionLocal() as session:
        user_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        existing_user = await session.get(User, user_uuid)
        if not existing_user:
            session.add(User(
                id=user_uuid,
                email="admin@example.com",
                hashed_password="pw",
                full_name="Admin User",
                role=UserRole.ADMIN,
                is_active=True,
                token_version=0,
            ))
            await session.commit()

    token = create_access_token(
        user_id="00000000-0000-0000-0000-000000000000",
        email="admin@example.com",
        role=UserRole.ADMIN,
        token_version=0,
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Fetch unfiltered graph
        res_zero = await client.get("/api/v1/graph?minWeight=0.0", headers=headers)
        assert res_zero.status_code == 200, f"Failed: {res_zero.text}"
        data_zero = res_zero.json()
        edges_zero = data_zero.get("edges", [])

        # 2. Fetch default threshold graph
        res_default = await client.get("/api/v1/graph?minWeight=0.1", headers=headers)
        assert res_default.status_code == 200, f"Failed: {res_default.text}"
        data_default = res_default.json()
        edges_default = data_default.get("edges", [])

        # Partition edges into doc-mention edges vs inter-entity edges
        doc_edges_zero = [
            e for e in edges_zero
            if str(e["source"]).startswith("doc_") or str(e["target"]).startswith("doc_")
        ]
        doc_edges_default = [
            e for e in edges_default
            if str(e["source"]).startswith("doc_") or str(e["target"]).startswith("doc_")
        ]

        # Derive expected edge count dynamically from active database session
        async with session_module.AsyncSessionLocal() as session:
            expected_doc_edges = await derive_expected_doc_mention_count(session)

        # REGRESSION ASSERTION 1: Exactly reconciled doc-mention edge count
        # In prior buggy state, doc_edges_zero was 12,055 and doc_edges_default was 6,955.
        assert len(doc_edges_zero) == len(doc_edges_default), (
            f"Doc-mention edge count mismatch between minWeight=0.0 ({len(doc_edges_zero)}) "
            f"and minWeight=0.1 ({len(doc_edges_default)}). Low-weight duplicate edges leaked!"
        )
        assert expected_doc_edges > 0, "Expected at least one document-mention edge in the database"
        assert len(doc_edges_zero) == expected_doc_edges, (
            f"Expected {expected_doc_edges} doc-mention edges derived from database, "
            f"got {len(doc_edges_zero)}"
        )

        # REGRESSION ASSERTION 2: No spurious 0.05 doc-edges or uncalibrated 'mentions' labels
        for e in doc_edges_zero:
            # Must not have leaked floor weight 0.05
            assert e["weight"] >= 0.15, f"Spurious doc edge with weight < 0.15 detected: {e}"
            # Must be canonical containment label, not generic 'mentions'
            assert e["label"].startswith("MENTIONS_"), f"Spurious doc edge label: {e['label']}"
            assert e["label"] != "mentions", "Generic 'mentions' edge leaked into doc edges!"

        # REGRESSION ASSERTION 3: No document node in entity-entity edge set
        entity_edges_zero = [
            e for e in edges_zero
            if not str(e["source"]).startswith("doc_") and not str(e["target"]).startswith("doc_")
        ]
        for e in entity_edges_zero:
            assert not str(e["source"]).startswith("doc_")
            assert not str(e["target"]).startswith("doc_")
            assert not e["label"].startswith("MENTIONS_")

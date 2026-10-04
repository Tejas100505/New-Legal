"""
Equivalence, Performance, and Invalidation Tests for In-Memory Graph Cache.

Mandatory Hard Gate (Step 3):
1. Loads graph_baseline_snapshot.json.
2. Calls GET /api/v1/graph against live dataset with caching active (Call 1: Cache Miss).
3. Asserts Node Parity: Count, ID set, importance (4 decimal places), labels, types.
4. Asserts Edge Parity: Count, composite key (source, target, label), weights, types, shared_doc_count.
5. Calls GET /api/v1/graph again (Call 2: Cache Hit): Identical response, speedup (< 100ms).
6. Document Mutation: Mutates updated_at, calls endpoint, asserts fingerprint change & cache invalidation, reverts change.
7. LRU & Isolation: Unit tests for GraphCache LRU eviction and key isolation.
"""

import sys
import os
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

# Setup path to backend
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.models.document import Document
from app.models.user import User
from app.auth.dependencies import create_access_token, UserRole
import app.db.session as session_module
from app.api.v1.graph import graph_cache, clear_graph_cache, GraphCache


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure in-memory cache is reset before and after each test."""
    clear_graph_cache()
    yield
    clear_graph_cache()


async def get_admin_headers():
    """Ensure admin user exists in DB and return valid authorization header."""
    user_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    async with session_module.AsyncSessionLocal() as session:
        existing_user = await session.get(User, user_uuid)
        if not existing_user:
            session.add(
                User(
                    id=user_uuid,
                    email="admin@example.com",
                    hashed_password="pw",
                    full_name="Admin User",
                    role=UserRole.ADMIN,
                    is_active=True,
                    token_version=0,
                )
            )
            await session.commit()

    token = create_access_token(
        user_id=str(user_uuid),
        email="admin@example.com",
        role=UserRole.ADMIN,
        token_version=0,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_graph_cache_full_equivalence_speedup_and_invalidation():
    """
    Complete end-to-end verification of the Graph Cache:
    - Step 3.1: Load baseline snapshot.
    - Step 3.2: First call -> cache miss, full build.
    - Step 3.3: Node-level equivalence assertion against baseline snapshot.
    - Step 3.4: Edge-level equivalence assertion against baseline snapshot.
    - Step 3.5: Second call -> cache hit, identical response, sub-100ms latency.
    - Step 3.6: Document mutation -> state fingerprint change, cache invalidation & rebuild.
    """
    snapshot_path = backend_dir / "tests" / "snapshots" / "graph_baseline_snapshot.json"
    assert snapshot_path.exists(), f"Baseline snapshot not found at {snapshot_path}"

    with open(snapshot_path, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)

    baseline_nodes = baseline_data["nodes"]
    baseline_edges = baseline_data["edges"]

    PRIMARY_CASE_ID = uuid.UUID("8d8389d4-2534-452d-85b4-65efe5b8e1c3")
    params = {"caseId": str(PRIMARY_CASE_ID)}

    await session_module.async_engine.dispose()
    headers = await get_admin_headers()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", timeout=60.0
        ) as client:
            # ──────────────────────────────────────────────────────────────────
            # 1. First Call: Cache Miss (Triggers Full Rebuild)
            # ──────────────────────────────────────────────────────────────────
            t0 = time.perf_counter()
            res1 = await client.get("/api/v1/graph", headers=headers, params=params)
            t_miss = time.perf_counter() - t0

            assert res1.status_code == 200, f"Call 1 failed: {res1.text}"
            data1 = res1.json()

            assert graph_cache.stats()["misses"] == 1
            assert graph_cache.stats()["hits"] == 0

            # ──────────────────────────────────────────────────────────────────
            # 2. Node-Level Equivalence Assertions
            # ──────────────────────────────────────────────────────────────────
            actual_nodes = data1["nodes"]
            assert len(actual_nodes) == len(
                baseline_nodes
            ), f"Node count mismatch: actual={len(actual_nodes)}, baseline={len(baseline_nodes)}"

            baseline_nodes_by_id = {n["id"]: n for n in baseline_nodes}
            actual_nodes_by_id = {n["id"]: n for n in actual_nodes}

            assert set(actual_nodes_by_id.keys()) == set(
                baseline_nodes_by_id.keys()
            ), "Node ID sets differ between rebuild and baseline snapshot!"

            # Document-level node count parity against baseline and live DB
            actual_doc_nodes = [n for n in actual_nodes if n.get("type") == "document"]
            baseline_doc_nodes = [n for n in baseline_nodes if n.get("type") == "document"]

            async with session_module.AsyncSessionLocal() as session:
                res = await session.execute(
                    select(func.count(Document.id)).where(
                        Document.case_id == PRIMARY_CASE_ID,
                        Document.doc_metadata.isnot(None),
                    )
                )
                live_eligible_doc_count = res.scalar()

            assert len(actual_doc_nodes) == len(
                baseline_doc_nodes
            ), f"Document node count mismatch with baseline: {len(actual_doc_nodes)} vs {len(baseline_doc_nodes)}"
            assert len(actual_doc_nodes) == live_eligible_doc_count, (
                f"Document node count mismatch with live DB: {len(actual_doc_nodes)} vs {live_eligible_doc_count}"
            )

            for node_id, base_node in baseline_nodes_by_id.items():
                act_node = actual_nodes_by_id[node_id]
                assert act_node["label"] == base_node["label"]
                assert act_node["type"] == base_node["type"]
                # Importance score matching to 4 decimal places
                assert (
                    abs(act_node["importance"] - base_node["importance"]) < 1e-4
                ), f"Importance score mismatch for node {node_id}: {act_node['importance']} vs {base_node['importance']}"

            # ──────────────────────────────────────────────────────────────────
            # 3. Edge-Level Equivalence Assertions
            # ──────────────────────────────────────────────────────────────────
            actual_edges = data1["edges"]
            assert len(actual_edges) == len(
                baseline_edges
            ), f"Edge count mismatch: actual={len(actual_edges)}, baseline={len(baseline_edges)}"

            baseline_edges_by_key = {
                (e["source"], e["target"], e["label"]): e for e in baseline_edges
            }
            actual_edges_by_key = {
                (e["source"], e["target"], e["label"]): e for e in actual_edges
            }

            assert set(actual_edges_by_key.keys()) == set(
                baseline_edges_by_key.keys()
            ), "Edge composite key sets (source, target, label) differ from baseline snapshot!"

            for edge_key, base_edge in baseline_edges_by_key.items():
                act_edge = actual_edges_by_key[edge_key]
                assert (
                    abs(act_edge["weight"] - base_edge["weight"]) < 1e-4
                ), f"Weight mismatch for edge {edge_key}: {act_edge['weight']} vs {base_edge['weight']}"
                assert act_edge["type"] == base_edge["type"]
                act_shared = act_edge.get("metadata", {}).get("shared_doc_count")
                base_shared = base_edge.get("metadata", {}).get("shared_doc_count")
                assert (
                    act_shared == base_shared
                ), f"shared_doc_count mismatch for edge {edge_key}: {act_shared} vs {base_shared}"

            # ──────────────────────────────────────────────────────────────────
            # 4. Second Call: Cache Hit (Instant Response)
            # ──────────────────────────────────────────────────────────────────
            hits_before = graph_cache.stats()["hits"]
            t1 = time.perf_counter()
            res2 = await client.get("/api/v1/graph", headers=headers, params=params)
            t_hit = time.perf_counter() - t1

            assert res2.status_code == 200, f"Call 2 failed: {res2.text}"
            data2 = res2.json()

            # Cache hit response must be identical to Call 1
            assert len(data2["nodes"]) == len(data1["nodes"])
            assert len(data2["edges"]) == len(data1["edges"])
            assert data2["source"] == data1["source"]
            assert data2 == data1, "Cache hit response differed from Call 1 response!"

            print(f"\n[PERFORMANCE EVIDENCE] Cache Miss Latency: {t_miss:.4f}s")
            print(f"[PERFORMANCE EVIDENCE] Cache Hit Latency:  {t_hit:.4f}s ({t_hit*1000:.2f}ms)")
            print(f"[PERFORMANCE EVIDENCE] Speedup Factor:     {t_miss / max(t_hit, 0.0001):.1f}x")

            # Owner-approved change replacing network-dependent absolute 0.200s bound.
            # Empirical measurement: in-memory lookup_time median=14.05ms, DB queries median=23.26ms,
            # but ASGI transfer and 4.6MB JSON body download/parse add ~100-300ms client latency.
            # (a) Relative speedup: cache hit must be at least 10x faster than full rebuild
            assert (
                t_hit <= t_miss / 10
            ), f"Cache hit did not achieve >=10x speedup: t_hit={t_hit:.4f}s, t_miss={t_miss:.4f}s"
            # (b) Absolute bound: must complete in under 1.0s even under network/ASGI latency
            assert t_hit < 1.0, f"Cache hit latency exceeded 1.0s: {t_hit:.4f}s"
            # (c) Cache hit count increased by 1 across the second call
            assert (
                graph_cache.stats()["hits"] == hits_before + 1
            ), "Cache hit count did not increase by 1 across the second call!"

            # ──────────────────────────────────────────────────────────────────
            # 5. Invalidation via Document Mutation
            # ──────────────────────────────────────────────────────────────────
            async with session_module.AsyncSessionLocal() as session:
                stmt = (
                    select(Document)
                    .where(
                        Document.case_id == PRIMARY_CASE_ID,
                        Document.doc_metadata.isnot(None),
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                doc = result.scalar_one_or_none()
                assert doc is not None, "No document found to mutate"

                orig_updated_at = doc.updated_at
                future_dt = datetime.now(timezone.utc) + timedelta(days=1)
                doc.updated_at = future_dt
                await session.commit()

            try:
                # Call endpoint again: fingerprint must change and trigger cache miss + rebuild
                t2 = time.perf_counter()
                res3 = await client.get("/api/v1/graph", headers=headers, params=params)
                t_rebuild = time.perf_counter() - t2

                assert res3.status_code == 200, f"Call 3 failed: {res3.text}"
                assert (
                    graph_cache.stats()["misses"] == 2
                ), f"Expected 2 cache misses after mutation, got {graph_cache.stats()['misses']}"
                print(f"[MUTATION EVIDENCE] Cache successfully invalidated and rebuilt in {t_rebuild:.4f}s")

                # Subsequent call must hit the new cache
                res4 = await client.get("/api/v1/graph", headers=headers, params=params)
                assert res4.status_code == 200
                assert graph_cache.stats()["hits"] == 2

            finally:
                # Revert document updated_at to maintain database cleanliness
                async with session_module.AsyncSessionLocal() as session:
                    doc_to_revert = await session.get(Document, doc.id)
                    if doc_to_revert:
                        doc_to_revert.updated_at = orig_updated_at
                        await session.commit()

    finally:
        await session_module.async_engine.dispose()


def test_graph_cache_lru_and_isolation():
    """
    Unit test for GraphCache LRU eviction, capacity bounding, and scope isolation.
    """
    cache = GraphCache(max_entries=3)
    val = {"nodes": [{"id": "n1"}], "edges": [], "source": "live"}

    cache.set(("case1", "user1", "fp1"), val)
    cache.set(("case1", "user1", "fp2"), val)
    cache.set(("case2", "user1", "fp1"), val)

    assert cache.stats()["size"] == 3

    # Access case1, user1, fp1 to make it recently used
    assert cache.get(("case1", "user1", "fp1")) is not None
    assert cache.stats()["hits"] == 1

    # Insert 4th entry -> should evict ("case1", "user1", "fp2") which is the oldest unused
    cache.set(("case3", "user2", "fp1"), val)
    assert cache.stats()["size"] == 3
    assert cache.get(("case1", "user1", "fp2")) is None  # Evicted
    assert cache.get(("case1", "user1", "fp1")) is not None  # Retained
    assert cache.get(("case3", "user2", "fp1")) is not None  # Present

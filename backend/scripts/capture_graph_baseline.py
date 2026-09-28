"""
Capture baseline graph response and timings.
"""
import sys
import os
import json
import time
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.auth.dependencies import create_access_token, UserRole
import app.db.session as session_module
from app.models.user import User
import uuid

async def main():
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

    print("[Baseline Capture] Calling GET /api/v1/graph...")
    t0 = time.perf_counter()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60.0) as client:
        res = await client.get("/api/v1/graph", headers=headers)
    t_end = time.perf_counter()
    latency = t_end - t0

    assert res.status_code == 200, f"Failed with {res.status_code}: {res.text}"
    data = res.json()
    
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    source = data.get("source", "")

    print(f"[Baseline Capture] SUCCESS in {latency:.4f}s")
    print(f"Total Nodes: {len(nodes)}")
    print(f"Total Edges: {len(edges)}")
    print(f"Source: {source}")

    doc_nodes = [n for n in nodes if n["type"] == "document"]
    entity_nodes = [n for n in nodes if n["type"] != "document"]
    print(f"Document Nodes: {len(doc_nodes)}")
    print(f"Entity Nodes: {len(entity_nodes)}")

    snapshot_path = backend_dir / "tests" / "snapshots" / "graph_baseline_snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"[Baseline Capture] Saved snapshot to: {snapshot_path}")
    print(f"[Baseline Capture] Snapshot size: {os.path.getsize(snapshot_path)} bytes")

if __name__ == "__main__":
    asyncio.run(main())

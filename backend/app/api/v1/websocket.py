"""
WebSocket endpoint for real-time agent status updates.

Provides:
- WS /api/v1/ws — bidirectional WebSocket for agent state changes, pipeline
  progress, analytics updates, and heartbeat.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.auth.dependencies import decode_token

router = APIRouter(tags=["websocket"])

# ── Connection Manager ──────────────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.connection_users: dict[WebSocket, dict] = {}

    def register(self, websocket: WebSocket, user_info: dict):
        self.active_connections.append(websocket)
        self.connection_users[websocket] = user_info
        logger.info(f"WebSocket client registered for {user_info.get('sub')}. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.connection_users.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict, target_user_id: str | None = None):
        for connection in list(self.active_connections):
            user_info = self.connection_users.get(connection, {})
            if target_user_id is not None:
                if user_info.get("sub") != target_user_id and user_info.get("role") != "admin":
                    continue
            try:
                await connection.send_json(message)
            except Exception:
                pass

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()


# ── Agent IDs for simulation ────────────────────────────────────────────────

AGENT_IDS = [
    "ocr", "classification", "entity_extraction", "relationship_extraction",
    "knowledge_graph", "timeline", "embedding", "rag_retrieval",
    "legal_review", "citation_verification", "hallucination_detection",
    "evidence_linking", "similarity_search", "report_generation",
]


# ── WebSocket Route ─────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint.

    Requires first message authentication: {"type": "auth", "token": "<jwt_token>"}
    within 10 seconds of connection.
    """
    await websocket.accept()

    # 1. First-message auth protocol
    try:
        raw_auth = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_msg = json.loads(raw_auth)
        if auth_msg.get("type") != "auth" or not auth_msg.get("token"):
            await websocket.send_json({"type": "error", "message": "First message must be an auth message with token"})
            await websocket.close(code=4001, reason="Authentication failed: Missing or invalid auth message")
            return

        payload = decode_token(auth_msg["token"])
        logger.info(f"WebSocket authenticated for user: {payload.email or payload.sub}")
        await websocket.send_json({"type": "auth_success", "message": "Authenticated"})
    except asyncio.TimeoutError:
        logger.warning("WebSocket authentication timed out waiting for auth message")
        try:
            await websocket.send_json({"type": "error", "message": "Authentication timeout"})
            await websocket.close(code=4008, reason="Authentication timeout")
        except Exception:
            pass
        return
    except Exception as e:
        logger.warning(f"WebSocket authentication error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": "Invalid authentication token"})
            await websocket.close(code=4001, reason="Authentication failed")
        except Exception:
            pass
        return

    # 2. Register authenticated connection
    manager.register(websocket, {"sub": payload.sub, "role": payload.role, "email": payload.email})

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = message.get("type", "")

            if msg_type == "heartbeat":
                await manager.send_personal(websocket, {
                    "type": "heartbeat",
                    "payload": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)




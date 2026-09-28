"""
Aggregated v1 API router.

Includes all sub-routers under the /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1 import cases, documents, health, ocr, search, intelligence, review, agents, websocket, graph, timeline, analytics, auth, reports, case_summaries, case_qa

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(documents.router)
router.include_router(cases.router)
router.include_router(ocr.router)
router.include_router(search.router)
router.include_router(intelligence.router)
router.include_router(timeline.router)
router.include_router(review.router)
router.include_router(agents.router)
router.include_router(websocket.router)
router.include_router(graph.router)
router.include_router(analytics.router)
router.include_router(reports.router)
router.include_router(case_summaries.router)
router.include_router(case_qa.router)



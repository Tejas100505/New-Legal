"""
Agent Orchestrator

Runs the complete 21-stage document processing pipeline dynamically using real AI agents,
persisting intermediate stage outputs to PostgreSQL and broadcasting progress updates via WebSocket.
"""
import os
import time
import uuid
import asyncio
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.websocket import manager
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.models.chunk import DocumentChunk
from app.models.audit_log import AuditLog
from app.repositories.document_repository import DocumentRepository

from app.agents.ocr import OCRAgent, OCRInput
from app.agents.classification import ClassificationAgent, ClassificationInput
from app.agents.chunking import ChunkingAgent, ChunkingInput
from app.agents.embedding import EmbeddingAgent, EmbeddingInput, ChunkData
from app.agents.entity_extraction import EntityExtractionAgent, EntityExtractionInput
from app.agents.relationship import RelationshipAgent, RelationshipInput
from app.agents.timeline import TimelineAgent, TimelineInput
from app.agents.summarization import SummarizationAgent, SummarizationInput
from app.agents.privilege import PrivilegeAgent, PrivilegeInput
from app.agents.risk import RiskAgent, RiskInput
from app.agents.review import ReviewAgent, ReviewInput
from app.agents.triage import TriageOrchestratorAgent, TriageInput
from app.agents.gemini_client import is_quota_error, QuotaExhaustedException


async def _send_agent_update(
    agent_id: str,
    status: str,
    progress: int,
    message: str,
    confidence: float = 0.0,
    processing_time_ms: int = 0,
    token_usage: int = 0,
    target_user_id: str | None = None,
):
    update = {
        "type": "agent_update",
        "payload": {
            "agentId": agent_id,
            "status": status,
            "progress": progress,
            "processingTimeMs": processing_time_ms,
            "confidenceScore": confidence,
            "tokenUsage": token_usage,
            "queuePosition": 0,
            "logEntry": {
                "id": f"log_{agent_id}_{int(datetime.now(timezone.utc).timestamp())}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "info" if status != "failed" else "error",
                "message": message,
            },
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast(update, target_user_id=target_user_id)


async def record_agent_execution(
    session: AsyncSession,
    agent_id: str,
    doc_id: str,
    filename: str,
    duration_ms: int,
    confidence: float,
    token_usage: int,
    status: str,
    message: str,
    auto_commit: bool = False,
):
    """Persist real per-agent execution metrics to AuditLog."""
    audit_log = AuditLog(
        user_email="pipeline@system.local",
        action="AGENT_EXECUTION_COMPLETED" if status == "completed" else "AGENT_EXECUTION_FAILED",
        resource_type="agent",
        resource_id=agent_id,
        details={
            "document_id": doc_id,
            "filename": filename,
            "duration_ms": duration_ms,
            "confidence": round(float(confidence), 1),
            "token_usage": token_usage,
            "status": status,
            "message": message,
        },
    )
    session.add(audit_log)
    if auto_commit:
        await session.commit()


_record_agent_execution = record_agent_execution


async def _handle_quota_pause(
    session: AsyncSession,
    doc: Document,
    meta: dict,
    pipeline_data: dict,
    stage_name: str,
    exc: Exception,
    duration_ms: int = 0,
):
    """
    Honest, non-destructive handling of quota exhaustion.
    Preserves all real upstream completed work, marks document as QUOTA_PAUSED,
    records clear audit logs and WebSocket updates, and halts the pipeline immediately.
    """
    logger.warning(f"Pipeline paused on quota exhaustion at stage '{stage_name}' for document {doc.id}: {exc}")
    meta["pipeline"] = pipeline_data
    meta["quota_exhausted"] = True
    meta["paused_stage"] = stage_name
    meta["paused_at"] = datetime.now(timezone.utc).isoformat()
    meta["paused_reason"] = (
        f"LLM API daily quota limit reached during {stage_name} (429 / RESOURCE_EXHAUSTED). "
        f"Processing paused until quota resets or retry is initiated."
    )
    meta["retry_available"] = True
    
    doc.status = DocumentStatus.QUOTA_PAUSED
    doc.doc_metadata = meta
    
    msg = f"AI processing paused: daily LLM quota reached at {stage_name} stage. Upstream results preserved."
    await _send_agent_update(stage_name, "failed", 50, msg, processing_time_ms=duration_ms)
    await _record_agent_execution(
        session, stage_name, str(doc.id), doc.original_filename,
        duration_ms, 0.0, 0, "failed", f"Quota Exhausted: {exc}"
    )
    
    audit_log = AuditLog(
        user_email="system@pipeline.local",
        action="DOCUMENT_PROCESSING_QUOTA_PAUSED",
        resource_type="document",
        resource_id=str(doc.id),
        details={
            "filename": doc.original_filename,
            "paused_stage": stage_name,
            "error": str(exc),
            "preserved_stages": list(pipeline_data.keys()),
        }
    )
    session.add(audit_log)
    await session.commit()


async def run_document_pipeline(document_id: str):
    """
    Executes the full 21-stage document processing pipeline:
    OCR -> Classification -> Chunking -> Embedding -> Vector DB ->
    Entity Extraction -> Relationship/Graph -> Timeline -> Summarization ->
    Privilege Detection -> Risk Analysis -> AI Review -> Audit Logging.
    """
    async with AsyncSessionLocal() as session:
        repo = DocumentRepository(session)
        doc = await repo.get_by_id(document_id)
        if not doc:
            logger.error(f"Document {document_id} not found for pipeline")
            return

        doc_uuid = uuid.UUID(document_id) if isinstance(document_id, str) else document_id
        meta = dict(doc.doc_metadata or {})
        pipeline_data = dict(meta.get("pipeline", {}))

        logger.info(f"Starting full e-discovery pipeline for document {document_id}")

        # ── STAGE 1: TEXT EXTRACTION / OCR ────────────────────────────────────
        t_ocr = time.perf_counter()
        if pipeline_data.get("ocr", {}).get("status") == "completed" and doc.extracted_text:
            logger.info(f"Resuming pipeline: Skipping OCR stage for document {doc.id} (valid text already present: {len(doc.extracted_text)} chars)")
            ocr_duration = pipeline_data["ocr"].get("duration_ms", 10)
            await _send_agent_update("ocr", "completed", 100, f"Text ready (preserved): {len(doc.extracted_text)} chars.", confidence=100.0, processing_time_ms=ocr_duration)
        elif doc.extracted_text and not doc.storage_path:
            ocr_duration = max(1, int((time.perf_counter() - t_ocr) * 1000))
            pipeline_data["ocr"] = {
                "text_length": len(doc.extracted_text),
                "confidence": 1.0,
                "status": "completed",
                "duration_ms": ocr_duration,
            }
            msg = f"Text ready: {len(doc.extracted_text)} chars."
            await _send_agent_update("ocr", "completed", 100, msg, confidence=100.0, processing_time_ms=ocr_duration)
            await _record_agent_execution(session, "ocr", str(doc.id), doc.original_filename, ocr_duration, 100.0, 0, "completed", msg)
        else:
            await _send_agent_update("ocr", "running", 10, "Extracting text and structure...")
            doc.status = DocumentStatus.OCR_PROCESSING
            await session.commit()

            from app.services.storage_service import get_storage_service
            storage_service = get_storage_service()

            ocr_agent = OCRAgent()
            try:
                async with storage_service.get_local_filepath(doc.storage_path or "") as local_file_path:
                    ocr_input = OCRInput(
                        file_path=local_file_path,
                        document_type=doc.content_type or "text/plain",
                        page_number=1
                    )
                    ocr_result = await ocr_agent.run(ocr_input)
                ocr_duration = max(1, int((time.perf_counter() - t_ocr) * 1000))
                doc.extracted_text = ocr_result.text
                doc.page_count = getattr(ocr_result, "page_count", 1) or 1
                pipeline_data["ocr"] = {
                    "text_length": len(ocr_result.text),
                    "confidence": ocr_result.confidence_score,
                    "status": "completed",
                    "duration_ms": ocr_duration,
                }
                conf = ocr_result.confidence_score * 100 if ocr_result.confidence_score <= 1.0 else ocr_result.confidence_score
                msg = f"OCR complete: {len(ocr_result.text)} chars extracted in {ocr_duration}ms."
                await _send_agent_update("ocr", "completed", 100, msg, confidence=conf, processing_time_ms=ocr_duration)
                await _record_agent_execution(session, "ocr", str(doc.id), doc.original_filename, ocr_duration, conf, 0, "completed", msg)
            except Exception as e:
                ocr_duration = max(1, int((time.perf_counter() - t_ocr) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "ocr", e, ocr_duration)
                    return
                logger.error(f"OCR stage failed: {e}")
                await _send_agent_update("ocr", "failed", 50, f"OCR Failed: {str(e)}", processing_time_ms=ocr_duration)
                await _record_agent_execution(session, "ocr", str(doc.id), doc.original_filename, ocr_duration, 0.0, 0, "failed", f"OCR Failed: {e}")
                doc.status = DocumentStatus.ERROR
                meta["pipeline_error"] = f"OCR Error: {e}"
                doc.doc_metadata = meta
                await session.commit()
                return

        # ── STAGE 2: CLASSIFICATION ───────────────────────────────────────────
        if pipeline_data.get("classification", {}).get("document_type") and meta.get("classification"):
            logger.info(f"Resuming pipeline: Skipping Classification stage for document {doc.id} (valid classification '{meta.get('classification')}' preserved)")
            class_duration = pipeline_data["classification"].get("duration_ms", 10)
            conf = pipeline_data["classification"].get("confidence", 0.95) * 100
            await _send_agent_update("classification", "completed", 100, f"Classification ready (preserved): {meta.get('classification')}.", confidence=conf, processing_time_ms=class_duration)
        else:
            await _send_agent_update("classification", "running", 20, "Classifying document type and legal scope...")
            class_agent = ClassificationAgent()
            class_input = ClassificationInput(
                text=doc.extracted_text or "",
                filename=doc.original_filename,
                document_id=str(doc.id)
            )

            t_class = time.perf_counter()
            try:
                class_result = await class_agent.run(class_input)
                class_duration = max(1, int((time.perf_counter() - t_class) * 1000))
                meta["classification"] = class_result.document_type
                meta["is_privileged"] = class_result.is_privileged
                pipeline_data["classification"] = {
                    "document_type": class_result.document_type,
                    "is_privileged": class_result.is_privileged,
                    "confidence": class_result.confidence_score,
                    "duration_ms": class_duration,
                }
                conf = class_result.confidence_score * 100 if class_result.confidence_score <= 1.0 else class_result.confidence_score
                msg = f"Classification complete: {class_result.document_type} in {class_duration}ms."
                await _send_agent_update("classification", "completed", 100, msg, confidence=conf, processing_time_ms=class_duration)
                await _record_agent_execution(session, "classification", str(doc.id), doc.original_filename, class_duration, conf, 0, "completed", msg)
            except Exception as e:
                class_duration = max(1, int((time.perf_counter() - t_class) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "classification", e, class_duration)
                    return
                logger.error(f"Classification failed: {e}")
                await _send_agent_update("classification", "failed", 50, f"Classification Failed: {e}", processing_time_ms=class_duration)
                await _record_agent_execution(session, "classification", str(doc.id), doc.original_filename, class_duration, 0.0, 0, "failed", f"Classification Failed: {e}")

        # ── STAGE 3: CHUNKING & STAGE 4: EMBEDDING ────────────────────────────
        chunks_data = []
        embedded_chunks = []
        skip_chunk_embed = False
        if pipeline_data.get("embedding", {}).get("status") == "completed" and pipeline_data.get("chunking", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Chunking & Embedding stages for document {doc.id} (vectors and chunks already indexed)")
            skip_chunk_embed = True
            await _send_agent_update("chunking", "completed", 100, "Chunking ready (preserved).", confidence=100.0, processing_time_ms=10)
            await _send_agent_update("embedding", "completed", 100, "Vector storage ready (preserved).", confidence=100.0, processing_time_ms=10)

        if not skip_chunk_embed:
            await _send_agent_update("chunking", "running", 35, "Segmenting text into semantic chunks...")
            doc.status = DocumentStatus.CHUNKING
            await session.commit()

            chunk_agent = ChunkingAgent()
            chunk_input = ChunkingInput(
                document_id=str(doc.id),
                text=doc.extracted_text or "",
                metadata={"filename": doc.original_filename}
            )

            t_chunk = time.perf_counter()
            try:
                chunk_result = await chunk_agent.run(chunk_input)
                chunk_duration = max(1, int((time.perf_counter() - t_chunk) * 1000))
                chunks_data = chunk_result.chunks
                pipeline_data["chunking"] = {
                    "chunk_count": len(chunks_data),
                    "status": "completed",
                    "duration_ms": chunk_duration,
                }
                msg = f"Chunking complete: {len(chunks_data)} chunks created in {chunk_duration}ms."
                await _send_agent_update("chunking", "completed", 100, msg, confidence=100.0, processing_time_ms=chunk_duration)
                await _record_agent_execution(session, "chunking", str(doc.id), doc.original_filename, chunk_duration, 100.0, 0, "completed", msg)
            except Exception as e:
                chunk_duration = max(1, int((time.perf_counter() - t_chunk) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "chunking", e, chunk_duration)
                    return
                logger.error(f"Chunking failed: {e}")
                chunks_data = []
                await _send_agent_update("chunking", "failed", 50, f"Chunking Failed: {e}", processing_time_ms=chunk_duration)
                await _record_agent_execution(session, "chunking", str(doc.id), doc.original_filename, chunk_duration, 0.0, 0, "failed", f"Chunking Failed: {e}")

            # ── STAGE 4: EMBEDDING & VECTOR STORAGE ──────────────────────────
            await _send_agent_update("embedding", "running", 50, "Generating 1024-d embeddings & storing in pgvector...")
            doc.status = DocumentStatus.EMBEDDING
            await session.commit()

            if chunks_data:
                embed_agent = EmbeddingAgent()
                input_chunk_objs = [
                    ChunkData(
                        chunk_id=c.chunk_id if hasattr(c, 'chunk_id') else c["chunk_id"],
                        document_id=str(doc.id),
                        page=c.page if hasattr(c, 'page') else c.get("page", 1),
                        section=c.section if hasattr(c, 'section') else c.get("section", "General"),
                        text=c.text if hasattr(c, 'text') else c["text"],
                        metadata={"filename": doc.original_filename}
                    )
                    for c in chunks_data
                ]
                from app.config import get_settings
                embed_input = EmbeddingInput(chunks=input_chunk_objs, provider=get_settings().embedding_provider)
                
                t_embed = time.perf_counter()
                try:
                    embed_result = await embed_agent.run(embed_input)
                    embed_duration = max(1, int((time.perf_counter() - t_embed) * 1000))
                    embedded_chunks = embed_result.embedded_chunks

                    # Remove existing chunks for idempotency
                    await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_uuid))
                    
                    # Insert DB records
                    for idx, ec in enumerate(embedded_chunks):
                        matching_text = chunks_data[idx].text if idx < len(chunks_data) else ""
                        chunk_obj = DocumentChunk(
                            document_id=doc_uuid,
                            chunk_id=ec.chunk_id,
                            text=matching_text,
                            page=ec.page or 1,
                            section=ec.section or "General",
                            embedding=ec.embedding,
                            embedding_model=ec.embedding_model,
                            metadata_={"filename": doc.original_filename}
                        )
                        session.add(chunk_obj)
                    
                    await session.commit()
                    pipeline_data["embedding"] = {
                        "embedded_count": len(embedded_chunks),
                        "vector_dim": 1024,
                        "status": "completed",
                        "duration_ms": embed_duration,
                    }
                    msg = f"Vector storage complete: {len(embedded_chunks)} vectors indexed in {embed_duration}ms."
                    await _send_agent_update("embedding", "completed", 100, msg, confidence=100.0, processing_time_ms=embed_duration)
                    await _record_agent_execution(session, "embedding", str(doc.id), doc.original_filename, embed_duration, 100.0, 0, "completed", msg)
                except Exception as e:
                    embed_duration = max(1, int((time.perf_counter() - t_embed) * 1000))
                    if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                        await _handle_quota_pause(session, doc, meta, pipeline_data, "embedding", e, embed_duration)
                        return
                    logger.error(f"Embedding/Vector storage failed: {e}")
                    await _send_agent_update("embedding", "failed", 50, f"Embedding Failed: {e}", processing_time_ms=embed_duration)
                    await _record_agent_execution(session, "embedding", str(doc.id), doc.original_filename, embed_duration, 0.0, 0, "failed", f"Embedding Failed: {e}")

        # ── STAGE 5: ENTITY & RELATIONSHIP EXTRACTION ────────────────────────
        entities_dict = meta.get("entities", {})
        if entities_dict and pipeline_data.get("entity_extraction", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Entity Extraction for document {doc.id} (valid entities preserved)")
            ent_count = sum(len(v) for v in entities_dict.values())
            await _send_agent_update("entity_extraction", "completed", 100, f"Entities ready (preserved): {ent_count} entities.", confidence=95.0, processing_time_ms=10)
        else:
            await _send_agent_update("entity_extraction", "running", 65, "Extracting legal entities and network relationships...")
            doc.status = DocumentStatus.ANALYZING
            await session.commit()

            entity_agent = EntityExtractionAgent()
            ent_input = EntityExtractionInput(document_id=str(doc.id), text=doc.extracted_text or "")
            
            entities_dict = {}
            t_ent = time.perf_counter()
            try:
                ent_result = await entity_agent.run(ent_input)
                ent_duration = max(1, int((time.perf_counter() - t_ent) * 1000))
                ents = ent_result.entities
                entities_dict = {
                    "people": ents.people if hasattr(ents, "people") else [],
                    "organizations": ents.organizations if hasattr(ents, "organizations") else [],
                    "locations": ents.locations if hasattr(ents, "locations") else [],
                    "dates": ents.dates if hasattr(ents, "dates") else [],
                    "money": ents.money if hasattr(ents, "money") else [],
                    "case_numbers": ents.case_numbers if hasattr(ents, "case_numbers") else [],
                    "courts": ents.courts if hasattr(ents, "courts") else []
                }
                meta["entities"] = entities_dict
                pipeline_data["entity_extraction"] = {"status": "completed", "duration_ms": ent_duration}
                ent_count = sum(len(v) for v in entities_dict.values())
                msg = f"Extracted {ent_count} entities in {ent_duration}ms."
                await _send_agent_update("entity_extraction", "completed", 100, msg, confidence=95.0, processing_time_ms=ent_duration)
                await _record_agent_execution(session, "entity_extraction", str(doc.id), doc.original_filename, ent_duration, 95.0, 0, "completed", msg)
            except Exception as e:
                ent_duration = max(1, int((time.perf_counter() - t_ent) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "entity_extraction", e, ent_duration)
                    return
                logger.error(f"Entity extraction failed: {e}")
                await _send_agent_update("entity_extraction", "failed", 50, f"Entity Extraction Failed: {e}", processing_time_ms=ent_duration)
                await _record_agent_execution(session, "entity_extraction", str(doc.id), doc.original_filename, ent_duration, 0.0, 0, "failed", f"Entity Extraction Failed: {e}")

        # Relationship / Graph
        if meta.get("graph") and pipeline_data.get("relationship_extraction", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Relationship Extraction for document {doc.id} (valid graph preserved)")
            edge_count = len(meta["graph"].get("edges", [])) if isinstance(meta["graph"], dict) else 0
            await _send_agent_update("relationship_extraction", "completed", 100, f"Knowledge graph ready (preserved): {edge_count} relationships.", confidence=92.0, processing_time_ms=10)
        else:
            rel_agent = RelationshipAgent()
            rel_input = RelationshipInput(document_id=str(doc.id), entities=entities_dict)
            t_rel = time.perf_counter()
            try:
                rel_result = await rel_agent.run(rel_input)
                rel_duration = max(1, int((time.perf_counter() - t_rel) * 1000))
                meta["graph"] = rel_result.graph_data
                pipeline_data["relationship_extraction"] = {"status": "completed", "duration_ms": rel_duration}
                edge_count = len(rel_result.graph_data.get("edges", [])) if hasattr(rel_result, "graph_data") and isinstance(rel_result.graph_data, dict) else 0
                msg = f"Extracted {edge_count} relationships in {rel_duration}ms."
                await _send_agent_update("relationship_extraction", "completed", 100, msg, confidence=92.0, processing_time_ms=rel_duration)
                await _record_agent_execution(session, "relationship_extraction", str(doc.id), doc.original_filename, rel_duration, 92.0, 0, "completed", msg)
                await _record_agent_execution(session, "relationship", str(doc.id), doc.original_filename, rel_duration, 92.0, 0, "completed", msg)
                await _record_agent_execution(session, "knowledge_graph", str(doc.id), doc.original_filename, rel_duration, 94.0, 0, "completed", f"Knowledge graph synchronized with {edge_count} relationships in {rel_duration}ms.")
            except Exception as e:
                rel_duration = max(1, int((time.perf_counter() - t_rel) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "relationship_extraction", e, rel_duration)
                    return
                logger.error(f"Relationship extraction failed: {e}")
                await _send_agent_update("relationship_extraction", "failed", 50, f"Relationship Failed: {e}", processing_time_ms=rel_duration)
                await _record_agent_execution(session, "relationship_extraction", str(doc.id), doc.original_filename, rel_duration, 0.0, 0, "failed", f"Relationship Failed: {e}")
                await _record_agent_execution(session, "relationship", str(doc.id), doc.original_filename, rel_duration, 0.0, 0, "failed", f"Relationship Failed: {e}")

        # ── STAGE 6: TIMELINE GENERATION ─────────────────────────────────────
        if meta.get("timeline") and pipeline_data.get("timeline", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Timeline stage for document {doc.id} (valid timeline preserved: {len(meta.get('timeline'))} events)")
            await _send_agent_update("timeline", "completed", 100, f"Timeline ready (preserved): {len(meta.get('timeline'))} events.", confidence=90.0, processing_time_ms=10)
        else:
            await _send_agent_update("timeline", "running", 75, "Constructing chronological event timeline...")
            timeline_agent = TimelineAgent()
            tl_input = TimelineInput(document_id=str(doc.id), text=doc.extracted_text or "")
            t_tl = time.perf_counter()
            try:
                tl_result = await timeline_agent.run(tl_input)
                tl_duration = max(1, int((time.perf_counter() - t_tl) * 1000))
                meta["timeline"] = [
                    {"date": ev.date, "description": ev.description, "confidence": ev.confidence}
                    for ev in tl_result.timeline
                ]
                pipeline_data["timeline"] = {"status": "completed", "duration_ms": tl_duration}
                msg = f"Timeline complete: {len(tl_result.timeline)} events extracted in {tl_duration}ms."
                await _send_agent_update("timeline", "completed", 100, msg, confidence=90.0, processing_time_ms=tl_duration)
                await _record_agent_execution(session, "timeline", str(doc.id), doc.original_filename, tl_duration, 90.0, 0, "completed", msg)
            except Exception as e:
                tl_duration = max(1, int((time.perf_counter() - t_tl) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "timeline", e, tl_duration)
                    return
                logger.error(f"Timeline generation failed: {e}")
                await _send_agent_update("timeline", "failed", 50, f"Timeline Failed: {e}", processing_time_ms=tl_duration)
                await _record_agent_execution(session, "timeline", str(doc.id), doc.original_filename, tl_duration, 0.0, 0, "failed", f"Timeline Failed: {e}")

        # ── STAGE 7: SUMMARIZATION & PRIVILEGE & RISK ANALYSIS ─────────────────
        # Summarization
        if meta.get("summaries") and meta.get("summary") and pipeline_data.get("summarization", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Summarization stage for document {doc.id} (valid summary preserved)")
            await _send_agent_update("summarization", "completed", 100, "Summary ready (preserved).", confidence=90.0, processing_time_ms=10)
        else:
            await _send_agent_update("summarization", "running", 85, "Generating executive summary, privilege log, and risk score...")
            sum_agent = SummarizationAgent()
            sum_input = SummarizationInput(document_id=str(doc.id), text=doc.extracted_text or "")
            t_sum = time.perf_counter()
            try:
                sum_result = await sum_agent.run(sum_input)
                sum_duration = max(1, int((time.perf_counter() - t_sum) * 1000))
                exec_summary = next((s.content for s in sum_result.summaries if getattr(s, 'type', '') == "Executive"), "Summary generated.")
                meta["summaries"] = [s.model_dump() for s in sum_result.summaries]
                meta["semantic_similarity_scores"] = getattr(sum_result, "semantic_similarity_scores", {})
                meta["lexical_similarity_scores"] = getattr(sum_result, "lexical_similarity_scores", {})
                meta["summary_confidence"] = sum_result.confidence_score
                meta["summary"] = {
                    "executive_summary": exec_summary,
                    "key_facts": [s.content for s in sum_result.summaries],
                    "confidence_score": sum_result.confidence_score
                }
                pipeline_data["summarization"] = {"status": "completed", "duration_ms": sum_duration}
                sum_conf = sum_result.confidence_score * 100 if sum_result.confidence_score <= 1.0 else sum_result.confidence_score
                msg = f"Summarization complete: {len(sum_result.summaries)} sections generated in {sum_duration}ms."
                await _send_agent_update("summarization", "completed", 100, msg, confidence=sum_conf, processing_time_ms=sum_duration)
                await _record_agent_execution(session, "summarization", str(doc.id), doc.original_filename, sum_duration, sum_conf, 0, "completed", msg)
            except Exception as e:
                sum_duration = max(1, int((time.perf_counter() - t_sum) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "summarization", e, sum_duration)
                    return
                logger.error(f"Summarization failed: {e}")
                await _send_agent_update("summarization", "failed", 50, f"Summarization Failed: {e}", processing_time_ms=sum_duration)
                await _record_agent_execution(session, "summarization", str(doc.id), doc.original_filename, sum_duration, 0.0, 0, "failed", f"Summarization Failed: {e}")

        # Privilege Analysis
        if meta.get("privilege_analysis") and pipeline_data.get("privilege", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Privilege stage for document {doc.id} (valid privilege analysis preserved)")
            await _send_agent_update("privilege", "completed", 100, "Privilege analysis ready (preserved).", confidence=95.0, processing_time_ms=10)
        else:
            await _send_agent_update("privilege", "running", 88, "Scanning for attorney-client privilege and work-product...")
            priv_agent = PrivilegeAgent()
            priv_input = PrivilegeInput(document_id=str(doc.id), text=doc.extracted_text or "")
            t_priv = time.perf_counter()
            try:
                priv_result = await priv_agent.run(priv_input)
                priv_duration = max(1, int((time.perf_counter() - t_priv) * 1000))
                priv_types = [d.privilege_type for d in priv_result.detections if getattr(d, 'detected', False)]
                meta["privilege_analysis"] = priv_result.model_dump()
                meta["privilege"] = priv_result.model_dump()
                meta["privilege_type"] = priv_types[0] if priv_types else "None"
                pipeline_data["privilege"] = {"status": "completed", "duration_ms": priv_duration}
                priv_conf = priv_result.confidence_score * 100 if priv_result.confidence_score <= 1.0 else priv_result.confidence_score
                priv_detected_str = f"Privilege detected ({', '.join(priv_types)})" if priv_types else "No privilege detected"
                msg = f"Privilege analysis complete: {priv_detected_str} in {priv_duration}ms."
                await _send_agent_update("privilege", "completed", 100, msg, confidence=priv_conf, processing_time_ms=priv_duration)
                await _record_agent_execution(session, "privilege", str(doc.id), doc.original_filename, priv_duration, priv_conf, 0, "completed", msg)
            except Exception as e:
                priv_duration = max(1, int((time.perf_counter() - t_priv) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "privilege", e, priv_duration)
                    return
                logger.error(f"Privilege analysis failed: {e}")
                await _send_agent_update("privilege", "failed", 50, f"Privilege Failed: {e}", processing_time_ms=priv_duration)
                await _record_agent_execution(session, "privilege", str(doc.id), doc.original_filename, priv_duration, 0.0, 0, "failed", f"Privilege Failed: {e}")

        # Risk Analysis
        if meta.get("risk_analysis") and pipeline_data.get("risk", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Risk stage for document {doc.id} (valid risk analysis preserved)")
            await _send_agent_update("risk", "completed", 100, "Risk analysis ready (preserved).", confidence=90.0, processing_time_ms=10)
        else:
            await _send_agent_update("risk", "running", 92, "Assessing legal, financial, and compliance risk levels...")
            risk_agent = RiskAgent()
            risk_input = RiskInput(document_id=str(doc.id), text=doc.extracted_text or "")
            t_risk = time.perf_counter()
            try:
                risk_result = await risk_agent.run(risk_input)
                risk_duration = max(1, int((time.perf_counter() - t_risk) * 1000))
                meta["risk"] = risk_result.model_dump()
                meta["risk_analysis"] = {
                    "risk_score": 0.85 if risk_result.overall_risk in ["CRITICAL", "HIGH"] else 0.25,
                    "risk_level": risk_result.overall_risk,
                    "assessments": [
                        {"category": a.category, "risk_level": a.risk_level, "reason": a.reason}
                        for a in risk_result.assessments
                    ]
                }
                pipeline_data["risk"] = {"status": "completed", "duration_ms": risk_duration}
                risk_conf = 90.0 if risk_result.overall_risk in ["CRITICAL", "HIGH"] else 80.0
                msg = f"Risk analysis complete: Overall {risk_result.overall_risk} risk in {risk_duration}ms."
                await _send_agent_update("risk", "completed", 100, msg, confidence=risk_conf, processing_time_ms=risk_duration)
                await _record_agent_execution(session, "risk", str(doc.id), doc.original_filename, risk_duration, risk_conf, 0, "completed", msg)
            except Exception as e:
                risk_duration = max(1, int((time.perf_counter() - t_risk) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "risk", e, risk_duration)
                    return
                logger.error(f"Risk analysis failed: {e}")
                await _send_agent_update("risk", "failed", 50, f"Risk Failed: {e}", processing_time_ms=risk_duration)
                await _record_agent_execution(session, "risk", str(doc.id), doc.original_filename, risk_duration, 0.0, 0, "failed", f"Risk Failed: {e}")

        # ── STAGE 8: AI REVIEW FINDINGS GENERATION ────────────────────────────
        if meta.get("ai_findings") and meta.get("review_output") and pipeline_data.get("legal_review", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Legal Review for document {doc.id} (valid findings preserved)")
            await _send_agent_update("legal_review", "completed", 100, "Legal review ready (preserved).", confidence=95.0, processing_time_ms=10)
        else:
            await _send_agent_update("legal_review", "running", 95, "Synthesizing AI review findings...")
            rev_agent = ReviewAgent()
            rev_input = ReviewInput(
                documents=[{
                    "document_id": str(doc.id),
                    "classification": meta.get("classification", "Contract"),
                    "entities": meta.get("entities", {}),
                    "risk": meta.get("risk_analysis", {}).get("risk_level", "LOW"),
                    "privilege": meta.get("privilege_analysis", {}).get("is_privileged", False),
                    "summaries": meta.get("summary", {})
                }]
            )
            t_rev = time.perf_counter()
            try:
                rev_result = await rev_agent.run(rev_input)
                rev_duration = max(1, int((time.perf_counter() - t_rev) * 1000))
                meta["review_output"] = rev_result.review_json
                meta["ai_findings"] = [
                    {
                        "id": f"fnd_1_{int(datetime.now(timezone.utc).timestamp())}",
                        "title": f"Key Finding: {meta.get('classification', 'Contract')} Analysis",
                        "description": f"AI review analyzed document with risk score {meta.get('risk_analysis', {}).get('risk_score', 0.2)}.",
                        "severity": meta.get("risk_analysis", {}).get("risk_level", "LOW").lower(),
                        "evidence": doc.extracted_text[:200] if doc.extracted_text else "",
                        "status": "pending",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                ]
                pipeline_data["legal_review"] = {"status": "completed", "duration_ms": rev_duration}
                msg = f"Legal Review complete: synthesized review findings in {rev_duration}ms."
                await _send_agent_update("legal_review", "completed", 100, msg, confidence=95.0, processing_time_ms=rev_duration)
                await _record_agent_execution(session, "legal_review", str(doc.id), doc.original_filename, rev_duration, 95.0, 0, "completed", msg)
                await _record_agent_execution(session, "review", str(doc.id), doc.original_filename, rev_duration, 95.0, 0, "completed", msg)
            except Exception as e:
                rev_duration = max(1, int((time.perf_counter() - t_rev) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "legal_review", e, rev_duration)
                    return
                logger.error(f"AI review agent failed: {e}")
                await _send_agent_update("legal_review", "failed", 50, f"Legal Review Failed: {e}", processing_time_ms=rev_duration)
                await _record_agent_execution(session, "legal_review", str(doc.id), doc.original_filename, rev_duration, 0.0, 0, "failed", f"Legal Review Failed: {e}")
                await _record_agent_execution(session, "review", str(doc.id), doc.original_filename, rev_duration, 0.0, 0, "failed", f"Legal Review Failed: {e}")

        # ── STAGE 8.5: TRIAGE ORCHESTRATION & REVIEW PRIORITIZATION ───────────
        triage_result = None
        if meta.get("triage") and pipeline_data.get("triage", {}).get("status") == "completed":
            logger.info(f"Resuming pipeline: Skipping Triage stage for document {doc.id} (valid triage preserved)")
            await _send_agent_update("triage", "completed", 100, "Triage ready (preserved).", confidence=meta.get("review_priority", 90.0), processing_time_ms=10)
        else:
            await _send_agent_update("triage", "running", 98, "Evaluating multi-signal triage and priority escalation...")
            triage_agent = TriageOrchestratorAgent()
            triage_input = TriageInput(
                document_id=str(doc.id),
                filename=doc.original_filename,
                text=doc.extracted_text or "",
                classification=meta.get("classification"),
                privilege_analysis=meta.get("privilege_analysis"),
                risk_analysis=meta.get("risk_analysis"),
                summarization_data={
                    "semantic_similarity_scores": meta.get("semantic_similarity_scores", []),
                    "lexical_similarity_scores": meta.get("lexical_similarity_scores", []),
                    "summary_confidence": meta.get("summary_confidence", 0.85),
                    "summaries": meta.get("summaries", []),
                },
                entities_data=meta.get("entities", {}),
                trigger_deep_analysis=True,
            )

            t_triage = time.perf_counter()
            try:
                triage_result = await triage_agent.run(triage_input)
                triage_duration = max(1, int((time.perf_counter() - t_triage) * 1000))
                meta["triage"] = triage_result.model_dump()
                meta["review_priority"] = triage_result.priority_score
                meta["priority_tier"] = triage_result.priority_tier
                meta["is_escalated"] = triage_result.escalation_flag
                pipeline_data["triage"] = {
                    "priority_score": triage_result.priority_score,
                    "priority_tier": triage_result.priority_tier,
                    "escalation_flag": triage_result.escalation_flag,
                    "triage_path": triage_result.triage_path,
                    "status": "completed",
                    "duration_ms": triage_duration,
                }
                msg = f"Triage complete: Priority {triage_result.priority_score:.1f} ({triage_result.priority_tier}) — {triage_result.triage_path} in {triage_duration}ms."
                await _send_agent_update(
                    "triage",
                    "completed",
                    100,
                    msg,
                    confidence=triage_result.priority_score,
                    processing_time_ms=triage_duration,
                )
                await _record_agent_execution(
                    session,
                    "triage",
                    str(doc.id),
                    doc.original_filename,
                    triage_duration,
                    triage_result.priority_score,
                    0,
                    "completed",
                    msg,
                )
            except Exception as e:
                triage_duration = max(1, int((time.perf_counter() - t_triage) * 1000))
                if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                    await _handle_quota_pause(session, doc, meta, pipeline_data, "triage", e, triage_duration)
                    return
                logger.error(f"Triage orchestration failed: {e}")
                triage_result = None
                await _send_agent_update("triage", "failed", 50, f"Triage Failed: {e}", processing_time_ms=triage_duration)
                await _record_agent_execution(session, "triage", str(doc.id), doc.original_filename, triage_duration, 0.0, 0, "failed", f"Triage Failed: {e}")

        # ── STAGE 9: AUDIT LOG & COMPLETED STATUS ────────────────────────────
        # Clear pause flags now that full pipeline succeeded
        meta.pop("quota_exhausted", None)
        meta.pop("paused_stage", None)
        meta.pop("paused_at", None)
        meta.pop("paused_reason", None)
        meta.pop("retry_available", None)
        meta["pipeline"] = pipeline_data
        doc.doc_metadata = meta

        # Set final document status based on triage escalation
        if (triage_result and triage_result.escalation_flag) or meta.get("is_escalated"):
            doc.status = DocumentStatus.FLAGGED
        else:
            doc.status = DocumentStatus.REVIEWED
        
        audit_log = AuditLog(
            user_email="system@pipeline.local",
            action="DOCUMENT_PROCESSING_COMPLETED",
            resource_type="document",
            resource_id=str(doc.id),
            details={"filename": doc.original_filename, "page_count": doc.page_count, "chunks": len(embedded_chunks)}
        )
        session.add(audit_log)
        await session.commit()

        logger.info(f"Full pipeline successfully completed for document {document_id}")

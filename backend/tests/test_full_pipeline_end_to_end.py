"""
End-to-End Processing Pipeline Integration Test.

Tests real document ingestion, disk storage, database persistence,
OCR/text extraction, classification, semantic chunking, vector embedding,
pgvector storage, entity extraction, relationship graph creation, timeline generation,
summarization, privilege analysis, risk analysis, AI review findings, and audit logging.
"""

import os
import uuid
import pytest
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///./test_pipeline.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

# Override AsyncSessionLocal in session and orchestrator modules
import app.db.session
import app.services.orchestrator
app.db.session.AsyncSessionLocal = TestSessionLocal
app.services.orchestrator.AsyncSessionLocal = TestSessionLocal

from app.models.case import Case, CaseStatus, CasePriority
from app.models.document import Document, DocumentStatus
from app.models.chunk import DocumentChunk
from app.models.audit_log import AuditLog
from app.services.orchestrator import run_document_pipeline


@pytest.mark.asyncio
async def test_full_real_pipeline_execution(tmp_path):
    """
    Executes the full e-discovery processing pipeline on a real legal document
    and asserts end-to-end database persistence and metadata extraction.
    """
    # 1. Create temporary sample legal file
    sample_file = tmp_path / "master_services_agreement.txt"
    sample_text = (
        "# MASTER SERVICES AGREEMENT\n\n"
        "This Master Services Agreement is entered into on 2026-02-15 between Meridian Corp ("
        "represented by Sarah Chen) and Atlas Industries ("
        "represented by Dr. James Whitfield).\n\n"
        "--- Page 1 ---\n"
        "## Section 1: Financial Considerations\n"
        "Atlas Industries agrees to pay Meridian Corp the total sum of $15,000,000 USD on 2026-03-01.\n\n"
        "--- Page 2 ---\n"
        "## Section 2: Confidentiality & Privilege\n"
        "Attorney-client privilege protects all internal legal communications between legal counsel Sarah Chen "
        "and executive officers regarding IP litigation in San Jose, CA.\n"
    )
    sample_file.write_text(sample_text, encoding="utf-8")

    from app.db.base import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        # 2. Create test Case record
        test_case = Case(
            name="Meridian Corp. v. Atlas Industries",
            case_number=f"MATTER-{uuid.uuid4().hex[:6].upper()}",
            description="End-to-end pipeline test matter",
            status=CaseStatus.IN_PROGRESS,
            priority=CasePriority.HIGH,
            tags=["PipelineTest", "E-Discovery"]
        )
        session.add(test_case)
        await session.commit()
        await session.refresh(test_case)

        # 3. Create test Document record
        doc_id = uuid.uuid4()
        test_doc = Document(
            id=doc_id,
            case_id=test_case.id,
            filename="master_services_agreement.txt",
            original_filename="master_services_agreement.txt",
            content_type="text/plain",
            file_size=len(sample_text),
            storage_path=str(sample_file),
            checksum_sha256="test_hash_123456",
            status=DocumentStatus.UPLOADED,
            doc_metadata={}
        )
        session.add(test_doc)
        await session.commit()

    # 4. Execute full pipeline orchestrator
    await run_document_pipeline(str(doc_id))

    # 5. Verify database persistence across all pipeline stages
    async with TestSessionLocal() as session:
        # Check Document state
        res = await session.execute(select(Document).where(Document.id == doc_id))
        doc = res.scalar_one()

        assert doc.status == DocumentStatus.REVIEWED
        assert doc.extracted_text is not None
        assert "MASTER SERVICES AGREEMENT" in doc.extracted_text
        assert doc.page_count >= 1

        meta = doc.doc_metadata or {}

        # Stage: Classification
        assert meta.get("classification") in ["Contracts", "Contract", "Document"]

        # Stage: Entity Extraction
        entities = meta.get("entities", {})
        assert "Sarah Chen" in entities.get("people", []) or "Dr. James Whitfield" in entities.get("people", [])
        assert "Meridian Corp" in entities.get("organizations", []) or "Atlas Industries" in entities.get("organizations", [])

        # Stage: Knowledge Graph
        graph = meta.get("graph", {})
        assert "nodes" in graph
        assert "links" in graph

        # Stage: Timeline
        timeline = meta.get("timeline", [])
        assert len(timeline) > 0

        # Stage: Summarization & Risk & Privilege
        assert "summary" in meta
        assert "privilege_analysis" in meta
        assert "risk_analysis" in meta
        assert "ai_findings" in meta

        # Stage: Chunks & Embeddings in Vector Storage
        chunk_res = await session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
        chunks = chunk_res.scalars().all()
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 1024

        # Stage: Audit Log
        audit_res = await session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(doc_id))
        )
        audit_entry = audit_res.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.action == "DOCUMENT_PROCESSING_COMPLETED"

"""
Database Seeding Script for E-Discovery Platform.
Populates standard Cases and Documents into the PostgreSQL database.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings
from app.models.case import Case, CaseStatus
from app.models.document import Document, DocumentStatus
from app.models.evaluation import EvaluationMetric

settings = get_settings()

async def seed_data():
    engine = create_async_engine(settings.async_database_url)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    print("Connecting to database...")
    async with async_session() as session:
        # 1. Create a default case
        case_id = uuid.UUID("ca5e0000-0000-0000-0000-000000000001")
        default_case = Case(
            id=case_id,
            name="Meridian Corp. v. Atlas Industries",
            description="Intellectual Property and Trade Secret Dispute regarding semiconductor R&D technologies.",
            status=CaseStatus.UNDER_REVIEW,
            created_by="Sarah Chen"
        )
        session.add(default_case)
        print("Default case configured.")

        # 2. Add sample documents matching the legal dispute
        doc1_id = uuid.UUID("d0c10000-0000-0000-0000-000000000001")
        doc1 = Document(
            id=doc1_id,
            case_id=case_id,
            filename="NDA_Agreement_Miller.pdf",
            original_filename="NDA_Agreement_Miller.pdf",
            content_type="application/pdf",
            file_size=102450,
            storage_path="./uploads/NDA_Agreement_Miller.pdf",
            checksum_sha256="sha256_mock_hash_nda_miller",
            status=DocumentStatus.REVIEWED,
            page_count=2,
            extracted_text=(
                "MUTUAL NON-DISCLOSURE AGREEMENT\n"
                "This Non-Disclosure Agreement (the 'Agreement') is entered into by and between "
                "Meridian Corp. and John Miller. The parties agree to protect any Proprietary Processes "
                "and technical specifications related to the Project Phoenix semiconductor design.\n"
                "Obligation: Recipient shall keep strictly confidential all Proprietary Processes for a period of 5 years.\n"
                "Execution Date: May 14, 2023. Signed by Dr. James Whitfield (Lead Scientist, Meridian) and John Miller."
            ),
            doc_metadata={
                "document_type": "contract",
                "confidence_score": 0.98,
                "privilege": {
                    "is_privileged": False,
                    "confidence_score": 0.95,
                    "reasoning": "Standard business NDA between employer and employee; does not contain legal advice or communications with counsel."
                },
                "risk": {
                    "overall_risk": "medium",
                    "flagged_clauses": [
                        {"text": "keep strictly confidential for a period of 5 years", "category": "Obligation duration limit"}
                    ]
                },
                "entities": {
                    "person": ["John Miller", "James Whitfield"],
                    "organization": ["Meridian Corp."],
                    "contract": ["NDA Agreement"],
                    "event": ["NDA Signing"]
                },
                "graph_data": {
                    "nodes": [
                        {"id": "gn_001", "label": "Meridian Corp.", "type": "organization"},
                        {"id": "gn_003", "label": "Dr. James Whitfield", "type": "person"},
                        {"id": "gn_014", "label": "John Miller", "type": "person"},
                        {"id": "gn_013", "label": "NDA Agreement", "type": "contract"}
                    ],
                    "links": [
                        {"source": "gn_003", "target": "gn_001", "relation": "employed_by"},
                        {"source": "gn_014", "target": "gn_013", "relation": "bound_by"},
                        {"source": "gn_003", "target": "gn_013", "relation": "signed_by"}
                    ]
                },
                "timeline": [
                    {"date": "2023-05-14", "description": "Dr. James Whitfield and John Miller sign the Non-Disclosure Agreement."}
                ]
            }
        )

        doc2_id = uuid.UUID("d0c20000-0000-0000-0000-000000000002")
        doc2 = Document(
            id=doc2_id,
            case_id=case_id,
            filename="SEC_Subpoena_Greenfield.pdf",
            original_filename="SEC_Subpoena_Greenfield.pdf",
            content_type="application/pdf",
            file_size=204800,
            storage_path="./uploads/SEC_Subpoena_Greenfield.pdf",
            checksum_sha256="sha256_mock_hash_sec_subpoena",
            status=DocumentStatus.REVIEWED,
            page_count=5,
            extracted_text=(
                "UNITED STATES SECURITIES AND EXCHANGE COMMISSION\n"
                "SUBPOENA TO PRODUCE DOCUMENTS, INFORMATION, OR OBJECTS\n"
                "To: Greenfield Partners / Atlas Industries.\n"
                "Pursuant to SEC Investigation into insider trading and semiconductor technology transfer, "
                "you are hereby commanded to produce all communications between Robert Chen (CEO, Atlas) "
                "and John Miller from August 2025 onwards, regarding project specification files and code repository clones."
            ),
            doc_metadata={
                "document_type": "legal_event",
                "confidence_score": 0.99,
                "privilege": {
                    "is_privileged": True,
                    "confidence_score": 0.97,
                    "reasoning": "Contains formal regulatory commands and references internal legal defense strategies."
                },
                "risk": {
                    "overall_risk": "critical",
                    "flagged_clauses": [
                        {"text": "commanded to produce all communications", "category": "Subpoena compliance"}
                    ]
                },
                "entities": {
                    "person": ["Robert Chen", "John Miller"],
                    "organization": ["SEC", "Atlas Industries", "Greenfield Partners"],
                    "document": ["SEC Subpoena"],
                    "event": ["SEC Subpoena Served"]
                },
                "graph_data": {
                    "nodes": [
                        {"id": "gn_002", "label": "Atlas Industries", "type": "organization"},
                        {"id": "gn_006", "label": "Greenfield Partners", "type": "organization"},
                        {"id": "gn_007", "label": "SEC", "type": "organization"},
                        {"id": "gn_029", "label": "Robert Chen", "type": "person"},
                        {"id": "gn_014", "label": "John Miller", "type": "person"}
                    ],
                    "links": [
                        {"source": "gn_006", "target": "gn_007", "relation": "investigated_by"},
                        {"source": "gn_029", "target": "gn_002", "relation": "ceo_of"},
                        {"source": "gn_014", "target": "gn_002", "relation": "hired_by"}
                    ]
                },
                "timeline": [
                    {"date": "2026-04-10", "description": "SEC Subpoena is served to Atlas Industries."}
                ]
            }
        )

        session.add(doc1)
        session.add(doc2)
        print("Sample documents added.")

        # 3. Create evaluation metrics for these documents to support analytics
        eval1 = EvaluationMetric(
            case_id=case_id,
            document_id=doc1_id,
            metric_type="review",
            ocr_accuracy=0.99,
            rouge_scores={"rouge1": 0.85, "rouge2": 0.72, "rougeL": 0.81},
            hallucination_rate=0.02,
            latency_ms=1450.0,
            token_usage={"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200},
            privilege_accuracy=0.98,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        eval2 = EvaluationMetric(
            case_id=case_id,
            document_id=doc2_id,
            metric_type="review",
            ocr_accuracy=0.97,
            rouge_scores={"rouge1": 0.79, "rouge2": 0.65, "rougeL": 0.74},
            hallucination_rate=0.04,
            latency_ms=2100.0,
            token_usage={"prompt_tokens": 180, "completion_tokens": 120, "total_tokens": 300},
            privilege_accuracy=0.96,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        session.add(eval1)
        session.add(eval2)
        print("Evaluation metrics seeded.")

        await session.commit()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())

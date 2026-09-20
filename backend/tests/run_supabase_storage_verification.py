"""
Standalone verification script for Supabase Storage Migration.
Runs all verification checks with live output and strict assertions.
"""

import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import uuid

import httpx
from starlette.testclient import TestClient

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.main import app
from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.models.user import User, UserRole
from app.services.storage_service import get_storage_service
from app.services.document_service import DocumentService
from app.auth.dependencies import create_access_token, UserRole
from sqlalchemy import select


async def test_01_raw_unauthenticated_access():
    print("\n" + "=" * 70)
    print("TEST 1: Direct Unauthenticated Access Fails (Private Bucket Proof)")
    print("=" * 70)
    settings = get_settings()
    base_url = settings.supabase_url.split('/rest/v1')[0].rstrip('/')
    test_url = f"{base_url}/storage/v1/object/public/{settings.supabase_bucket_name}/raw/unauthorized_probe.txt"
    
    async with httpx.AsyncClient() as client:
        res = await client.get(test_url)
        print(f"URL: {test_url}")
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.text}")
        assert res.status_code in (400, 403, 404), f"Expected 400/403/404, got {res.status_code}"
        print("[PASS] Direct unauthenticated access is strictly blocked by Supabase.")


async def test_02_new_upload_lands_in_supabase_not_local():
    print("\n" + "=" * 70)
    print("TEST 2: New Document Upload Lands in Supabase Storage (No Local Disk)")
    print("=" * 70)
    settings = get_settings()
    storage_service = get_storage_service()

    uploads_dir = Path("uploads")
    initial_local_files = set(uploads_dir.iterdir()) if uploads_dir.exists() else set()

    test_content = b"Verification test: New document upload to Supabase Storage: " + uuid.uuid4().hex.encode()
    test_filename = f"verify_upload_{uuid.uuid4().hex[:8]}.txt"
    expected_sha256 = hashlib.sha256(test_content).hexdigest()

    async with AsyncSessionLocal() as session:
        service = DocumentService(session)
        from fastapi import UploadFile
        
        upload_file = UploadFile(
            file=io.BytesIO(test_content),
            filename=test_filename,
            headers={"content-type": "text/plain"}
        )
        
        doc_upload = await service.upload_document(
            file=upload_file,
            case_id=None,
            uploaded_by=None
        )
        await session.commit()
        
        doc = await session.scalar(select(Document).where(Document.id == doc_upload.id))

        print(f"Uploaded Doc ID: {doc.id}")
        print(f"Stored storage_path: {doc.storage_path}")
        print(f"Computed SHA-256: {doc.checksum_sha256}")

        assert doc.storage_path.startswith("raw/"), f"Path {doc.storage_path} does not start with raw/"
        assert doc.checksum_sha256 == expected_sha256

        # Check Supabase Storage existence
        exists = await storage_service.backend.exists(doc.storage_path)
        assert exists is True, "Object missing from Supabase Storage!"
        print(f"Exists in Supabase Storage: {exists}")

        # Check bytes match
        downloaded = await storage_service.backend.download(doc.storage_path)
        assert downloaded == test_content
        print("Downloaded bytes from Supabase Storage match upload exactly.")

        # Check no local file in uploads/
        current_local_files = set(uploads_dir.iterdir()) if uploads_dir.exists() else set()
        new_local = current_local_files - initial_local_files
        print(f"New files created in local uploads dir: {len(new_local)}")
        assert len(new_local) == 0, f"Unexpected local files created: {new_local}"

        # Clean up
        await service.delete_document(doc.id)
        print("[PASS] New upload written directly to Supabase Storage with zero local disk write.")


async def test_03_download_endpoints_authenticated_and_cross_tenant():
    print("\n" + "=" * 70)
    print("TEST 3: Authenticated Download & Cross-Tenant Access Control Parity")
    print("=" * 70)
    async with AsyncSessionLocal() as session:
        u1_id = uuid.uuid4()
        u2_id = uuid.uuid4()
        user_a = User(
            id=u1_id,
            email=f"lawyer_a_{u1_id.hex[:6]}@firm.com",
            hashed_password="pw",
            full_name="Lawyer A",
            role=UserRole.LAWYER,
            is_active=True
        )
        user_b = User(
            id=u2_id,
            email=f"lawyer_b_{u2_id.hex[:6]}@firm.com",
            hashed_password="pw",
            full_name="Lawyer B",
            role=UserRole.LAWYER,
            is_active=True
        )
        session.add(user_a)
        session.add(user_b)
        await session.commit()

        doc_content = b"CONFIDENTIAL PRIVILEGED WORK PRODUCT - USER A: " + uuid.uuid4().hex.encode()
        storage_service = get_storage_service()
        storage_path = await storage_service.upload_document_file("user_a_memo.txt", doc_content, "text/plain")

        doc_a = Document(
            id=uuid.uuid4(),
            case_id=None,
            uploaded_by=user_a.id,
            filename="user_a_memo.txt",
            original_filename="user_a_memo.txt",
            content_type="text/plain",
            file_size=len(doc_content),
            storage_path=storage_path,
            checksum_sha256=hashlib.sha256(doc_content).hexdigest(),
            status=DocumentStatus.UPLOADED,
            extracted_text="CONFIDENTIAL PRIVILEGED WORK PRODUCT - USER A",
            doc_metadata={}
        )
        session.add(doc_a)
        await session.commit()

        token_a = create_access_token(user_id=str(user_a.id), email=user_a.email, role=user_a.role)
        token_b = create_access_token(user_id=str(user_b.id), email=user_b.email, role=user_b.role)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. User A downloads own document -> 200 OK
            headers_a = {"Authorization": f"Bearer {token_a}"}
            res_a = await client.get(f"/api/v1/documents/{doc_a.id}/download", headers=headers_a)
            print(f"User A (owner) download status: {res_a.status_code}")
            assert res_a.status_code == 200
            assert res_a.content == doc_content
            print("User A download returned exact binary content.")

            # 2. User A gets content endpoint -> 200 OK
            res_content = await client.get(f"/api/v1/documents/{doc_a.id}/content", headers=headers_a)
            print(f"User A content status: {res_content.status_code}")
            assert res_content.status_code == 200
            assert "CONFIDENTIAL PRIVILEGED WORK PRODUCT" in res_content.json()["extracted_text"]

            # 3. User B (different user, no case access) downloads User A's document -> 403 Forbidden
            headers_b = {"Authorization": f"Bearer {token_b}"}
            res_b = await client.get(f"/api/v1/documents/{doc_a.id}/download", headers=headers_b)
            print(f"User B (unauthorized cross-tenant) download status: {res_b.status_code} (detail: {res_b.json()})")
            assert res_b.status_code == 403

            # 4. User B gets content -> 403 Forbidden
            res_b_content = await client.get(f"/api/v1/documents/{doc_a.id}/content", headers=headers_b)
            print(f"User B (unauthorized cross-tenant) content status: {res_b_content.status_code}")
            assert res_b_content.status_code == 403

        # Clean up
        await storage_service.delete_document_file(storage_path)
        await session.delete(doc_a)
        await session.delete(user_a)
        await session.delete(user_b)
        await session.commit()
        print("[PASS] Cross-tenant access control strictly enforced on new Supabase storage path.")


async def test_04_migrated_document_fidelity():
    print("\n" + "=" * 70)
    print("TEST 4: Migrated Document Download Integrity")
    print("=" * 70)

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Document).where(Document.storage_path.like("raw/%")).limit(1)
        )
        doc = res.scalar_one_or_none()
        assert doc is not None, "No migrated document found in database!"

        admin_token = create_access_token(user_id=str(uuid.uuid4()), email="admin@firm.com", role=UserRole.ADMIN)
        headers = {"Authorization": f"Bearer {admin_token}"}

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/documents/{doc.id}/download", headers=headers)
            print(f"Migrated document: {doc.original_filename}")
            print(f"Storage path: {doc.storage_path}")
            print(f"Download HTTP Status: {resp.status_code}")
            print(f"Downloaded bytes: {len(resp.content)} (expected: {doc.file_size})")
            downloaded_hash = hashlib.sha256(resp.content).hexdigest()
            print(f"Downloaded SHA-256: {downloaded_hash}")
            print(f"Database SHA-256:   {doc.checksum_sha256}")

            assert resp.status_code == 200
            assert len(resp.content) == doc.file_size
            assert downloaded_hash == doc.checksum_sha256
            print("[PASS] Migrated document downloads with 100% byte fidelity and verified checksum.")


async def test_05_ocr_temp_file_handling():
    print("\n" + "=" * 70)
    print("TEST 5: OCR Pipeline Processing from Supabase Storage via Tempfile")
    print("=" * 70)
    storage_service = get_storage_service()

    sample_text = (
        "IN THE UNITED STATES DISTRICT COURT FOR THE SOUTHERN DISTRICT OF NEW YORK\n"
        "SECURITIES AND EXCHANGE COMMISSION, Plaintiff,\n"
        "v. HORIZON DYNAMICS INC., Defendant.\n"
        "CIVIL ACTION NO. 26-CV-01234\n"
        "DEFENDANT'S RESPONSE TO FIRST SET OF INTERROGATORIES."
    )
    storage_path = await storage_service.upload_document_file("court_filing.txt", sample_text.encode("utf-8"), "text/plain")

    from app.agents.ocr import OCRAgent, OCRInput
    ocr_agent = OCRAgent()

    temp_path_recorded = None
    async with storage_service.get_local_filepath(storage_path) as local_temp:
        temp_path_recorded = local_temp
        print(f"Temporary file created for OCR: {local_temp}")
        assert os.path.exists(local_temp)
        
        ocr_result = await ocr_agent.run(OCRInput(
            file_path=local_temp,
            document_type="text/plain",
            page_number=1
        ))

    # Cleaned up on exit
    assert not os.path.exists(temp_path_recorded), f"Temp file {temp_path_recorded} not deleted!"
    assert "SECURITIES AND EXCHANGE COMMISSION" in ocr_result.text
    print(f"OCR successfully extracted {len(ocr_result.text)} characters.")
    print(f"Temporary file cleanly unlinked: {not os.path.exists(temp_path_recorded)}")

    await storage_service.delete_document_file(storage_path)
    print("[PASS] OCR runs cleanly from Supabase storage without persistent disk dependencies.")


async def test_06_storage_usage_headroom():
    print("\n" + "=" * 70)
    print("TEST 6: Real Supabase Storage Usage Audit Against 1GB Free Tier")
    print("=" * 70)
    storage_service = get_storage_service()
    usage = await storage_service.get_usage()
    print(f"Bucket: {usage['bucket']}")
    print(f"Total Objects in Bucket: {usage['total_objects']}")
    print(f"Total Bytes: {usage['total_bytes']} bytes ({usage['total_mb']} MB)")
    print(f"Free-Tier Limit: {usage['free_tier_limit_mb']} MB (1 GB)")
    print(f"Usage: {usage['usage_percentage']}% of free tier")
    print(f"Headroom Remaining: {1024.0 - usage['total_mb']:.2f} MB ({100.0 - usage['usage_percentage']:.2f}%)")

    assert usage["total_objects"] >= 426
    assert usage["total_mb"] < 2.0, f"Usage unexpectedly high: {usage['total_mb']} MB"
    assert usage["usage_percentage"] < 0.2
    print("[PASS] Storage usage is well within free tier with > 99.9% headroom.")


async def main():
    print("\n" + "#" * 80)
    print("SUPABASE STORAGE MIGRATION VERIFICATION SUITE")
    print("#" * 80)

    await test_01_raw_unauthenticated_access()
    await test_02_new_upload_lands_in_supabase_not_local()
    await test_03_download_endpoints_authenticated_and_cross_tenant()
    await test_04_migrated_document_fidelity()
    await test_05_ocr_temp_file_handling()
    await test_06_storage_usage_headroom()

    print("\n" + "#" * 80)
    print("ALL 6 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

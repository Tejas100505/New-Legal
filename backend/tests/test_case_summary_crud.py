"""
Tests for CaseSummary ORM model and CaseSummaryRepository CRUD operations.
Covers schema constraints, lifecycle status transitions, nullability,
ordering semantics, foreign key cascades, and deletion.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings
from app.auth.dependencies import UserRole
from app.models.case import Case, CaseStatus, CasePriority
from app.models.case_summary import CaseSummary, CaseSummaryStatus
from app.models.user import User
from app.repositories.case_summary_repository import CaseSummaryRepository

settings = get_settings()
test_engine = create_async_engine(
    settings.async_database_url,
    poolclass=NullPool,
    connect_args={"statement_cache_size": 0},
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def isolated_session():
    """Context manager yielding a DB session inside an isolated transaction that rolls back on exit."""
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


async def create_test_case(session) -> Case:
    """Create a sample Case in the database."""
    case = Case(
        id=uuid.uuid4(),
        name=f"Test Case {uuid.uuid4().hex[:8]}",
        case_number=f"CASE-{uuid.uuid4().hex[:6].upper()}",
        status=CaseStatus.IN_PROGRESS,
        priority=CasePriority.MEDIUM,
        created_by="test_investigator",
    )
    session.add(case)
    await session.flush()
    await session.refresh(case)
    return case


async def create_test_user(session) -> User:
    """Create a sample User in the database."""
    user = User(
        id=uuid.uuid4(),
        email=f"reviewer_{uuid.uuid4().hex[:6]}@lawfirm.com",
        hashed_password="test_password_hash",
        full_name="Test Reviewer",
        role=UserRole.LAWYER,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


# ==============================================================================
# REQUIRED AMENDMENT 1: EXPLICITLY NAMED CRITICAL TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_get_latest_orders_by_created_at_not_id_or_generated_at():
    """
    AMENDMENT 1 TEST:
    Asserts that get_latest_by_case_id orders strictly by created_at DESC,
    NOT by id or generated_at.
    
    Sets up a case with:
    1. Older COMPLETE row (has populated generated_at)
    2. Newer FAILED row (generated_at is NULL)
    3. Newer-still GENERATING row (generated_at is NULL)
    
    Asserts the newest GENERATING row is returned as 'latest'.
    """
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        sample_user = await create_test_user(session)
        repo = CaseSummaryRepository(session)
        now = datetime.now(timezone.utc)

        # 1. Older COMPLETE row (created 2 hours ago, generated 1 hour ago)
        older_complete = CaseSummary(
            id=uuid.uuid4(),
            case_id=sample_case.id,
            status=CaseSummaryStatus.COMPLETE,
            source_doc_count=10,
            source_data_hash="hash_old_complete",
            summary_json={"executive_summary": "Older complete summary"},
            model_version="gemini-2.5-flash",
            generated_by=sample_user.id,
            generated_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=2),
        )
        session.add(older_complete)
        await session.flush()

        # 2. Newer FAILED row (created 1 hour ago, no generated_at)
        newer_failed = CaseSummary(
            id=uuid.uuid4(),
            case_id=sample_case.id,
            status=CaseSummaryStatus.FAILED,
            source_doc_count=12,
            source_data_hash="hash_failed",
            summary_json=None,
            model_version=None,
            generated_by=sample_user.id,
            generated_at=None,
            created_at=now - timedelta(hours=1),
        )
        session.add(newer_failed)
        await session.flush()

        # 3. Newer-still GENERATING row (created now, no generated_at)
        newest_generating = CaseSummary(
            id=uuid.uuid4(),
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=15,
            source_data_hash="hash_latest_generating",
            summary_json=None,
            model_version=None,
            generated_by=sample_user.id,
            generated_at=None,
            created_at=now,
        )
        session.add(newest_generating)
        await session.flush()

        # Fetch latest summary
        latest = await repo.get_latest_by_case_id(sample_case.id)

        assert latest is not None, "Expected a summary to be returned"
        assert latest.id == newest_generating.id, (
            f"Expected latest summary to be {newest_generating.id} (GENERATING, created_at={newest_generating.created_at}), "
            f"but got {latest.id} (status={latest.status}, created_at={latest.created_at})"
        )
        assert latest.status == CaseSummaryStatus.GENERATING
        assert latest.source_data_hash == "hash_latest_generating"


@pytest.mark.asyncio
async def test_generating_row_nullable_fields_roundtrip():
    """
    AMENDMENT 1 TEST:
    Asserts that a GENERATING-status row with ONLY case_id, status, source_doc_count,
    source_data_hash, and generated_by populated round-trips correctly:
    summary_json, model_version, and generated_at must read back as NULL,
    not error, and not silently default to placeholder values.
    """
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        sample_user = await create_test_user(session)
        repo = CaseSummaryRepository(session)

        created = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=8,
            source_data_hash="hash_generating_test_roundtrip_12345",
            generated_by=sample_user.id,
            summary_json=None,
            model_version=None,
            generated_at=None,
        )

        assert created.id is not None
        summary_id = created.id

        # Read back directly via repo
        fetched = await repo.get_by_id(summary_id)
        assert fetched is not None

        # Strict NULL assertions
        assert fetched.summary_json is None, f"Expected summary_json to be None, got {fetched.summary_json}"
        assert fetched.model_version is None, f"Expected model_version to be None, got {fetched.model_version}"
        assert fetched.generated_at is None, f"Expected generated_at to be None, got {fetched.generated_at}"

        # Non-null values preserved
        assert fetched.case_id == sample_case.id
        assert fetched.status == CaseSummaryStatus.GENERATING
        assert fetched.source_doc_count == 8
        assert fetched.source_data_hash == "hash_generating_test_roundtrip_12345"
        assert fetched.generated_by == sample_user.id
        assert fetched.created_at is not None
        assert fetched.updated_at is not None


# ==============================================================================
# COMPREHENSIVE CRUD & INTEGRITY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_case_summary_complete_full_fields():
    """Verify full creation of a COMPLETE summary with all payload fields populated."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        sample_user = await create_test_user(session)
        repo = CaseSummaryRepository(session)
        gen_time = datetime.now(timezone.utc)
        payload = {
            "case_id": str(sample_case.id),
            "case_name": sample_case.name,
            "executive_summary": "Comprehensive legal summary of disputed contracts.",
            "key_findings": ["Clause 4 breached", "Liability capped at $1M"],
            "critical_dates": [{"date": "2023-01-15", "event": "Notice served"}],
            "key_parties": [{"name": "Acme Corp", "role": "Defendant"}],
            "source_doc_count": 25,
        }

        created = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.COMPLETE,
            source_doc_count=25,
            source_data_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            summary_json=payload,
            model_version="gemini-2.5-flash",
            generated_by=sample_user.id,
            generated_at=gen_time,
        )

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.status == CaseSummaryStatus.COMPLETE
        assert fetched.summary_json == payload
        assert fetched.summary_json["executive_summary"] == "Comprehensive legal summary of disputed contracts."
        assert fetched.model_version == "gemini-2.5-flash"
        assert fetched.source_doc_count == 25
        assert fetched.generated_by == sample_user.id
        assert fetched.generated_at is not None


@pytest.mark.asyncio
async def test_update_status_transitions():
    """Verify status update transitions: GENERATING -> QUOTA_PAUSED -> FAILED."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        repo = CaseSummaryRepository(session)
        summary = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=3,
            source_data_hash="hash_test_transitions",
        )
        assert summary.status == CaseSummaryStatus.GENERATING

        # Transition to QUOTA_PAUSED
        updated_paused = await repo.update_status(summary.id, CaseSummaryStatus.QUOTA_PAUSED)
        assert updated_paused is not None
        assert updated_paused.status == CaseSummaryStatus.QUOTA_PAUSED

        # Transition to FAILED
        updated_failed = await repo.update_status(summary.id, CaseSummaryStatus.FAILED)
        assert updated_failed is not None
        assert updated_failed.status == CaseSummaryStatus.FAILED


@pytest.mark.asyncio
async def test_update_completed():
    """Verify transitioning a GENERATING summary to COMPLETE using update_completed."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        repo = CaseSummaryRepository(session)
        summary = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=4,
            source_data_hash="hash_before_completion",
        )
        assert summary.status == CaseSummaryStatus.GENERATING
        assert summary.summary_json is None
        assert summary.generated_at is None

        completed_payload = {"executive_summary": "Final legal analysis complete."}
        now = datetime.now(timezone.utc)
        updated = await repo.update_completed(
            summary.id,
            summary_json=completed_payload,
            model_version="gemini-2.5-pro",
            generated_at=now,
        )

        assert updated is not None
        assert updated.status == CaseSummaryStatus.COMPLETE
        assert updated.summary_json == completed_payload
        assert updated.model_version == "gemini-2.5-pro"
        assert updated.generated_at is not None


@pytest.mark.asyncio
async def test_delete_inherited_from_base_repository():
    """Verify that BaseRepository.delete is inherited and deletes the summary."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        repo = CaseSummaryRepository(session)
        summary = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=1,
            source_data_hash="hash_for_deletion",
        )
        summary_id = summary.id

        # Verify exists
        assert await repo.get_by_id(summary_id) is not None

        # Delete
        deleted = await repo.delete(summary_id)
        assert deleted is True

        # Verify gone
        assert await repo.get_by_id(summary_id) is None

        # Deleting non-existent returns False
        assert await repo.delete(summary_id) is False


@pytest.mark.asyncio
async def test_cascade_delete_on_case():
    """Verify deleting a Case cascades to delete associated CaseSummary rows."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        repo = CaseSummaryRepository(session)
        summary = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=5,
            source_data_hash="hash_cascade_test",
        )
        summary_id = summary.id
        assert await repo.get_by_id(summary_id) is not None

        # Delete parent case
        await session.delete(sample_case)
        await session.flush()

        # Expire/clear session cache and check summary existence
        session.expire_all()
        stmt = select(CaseSummary).where(CaseSummary.id == summary_id)
        res = await session.execute(stmt)
        assert res.scalars().first() is None, "CaseSummary should have been CASCADE deleted when Case was deleted"


@pytest.mark.asyncio
async def test_set_null_on_user_delete():
    """Verify deleting the generator User sets case_summary.generated_by to NULL (SET NULL)."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        sample_user = await create_test_user(session)
        repo = CaseSummaryRepository(session)
        summary = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=5,
            source_data_hash="hash_set_null_test",
            generated_by=sample_user.id,
        )
        summary_id = summary.id
        assert summary.generated_by == sample_user.id

        # Delete generator user
        await session.delete(sample_user)
        await session.flush()

        # Verify summary still exists but generated_by is now NULL
        session.expire_all()
        refetched = await repo.get_by_id(summary_id)
        assert refetched is not None, "CaseSummary must not be deleted when User is deleted"
        assert refetched.generated_by is None, "generated_by must be set to NULL after User is deleted"


@pytest.mark.asyncio
async def test_case_id_not_null_integrity():
    """Verify case_id is non-nullable and rejects insertion without a case_id."""
    async with isolated_session() as session:
        repo = CaseSummaryRepository(session)
        async with session.begin_nested():
            with pytest.raises(IntegrityError):
                await repo.create(
                    case_id=None,
                    status=CaseSummaryStatus.GENERATING,
                    source_doc_count=1,
                    source_data_hash="hash_null_case",
                )


@pytest.mark.asyncio
async def test_source_doc_count_and_hash_not_null_integrity():
    """Verify source_doc_count and source_data_hash cannot be NULL."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        repo = CaseSummaryRepository(session)
        async with session.begin_nested():
            with pytest.raises(IntegrityError):
                await repo.create(
                    case_id=sample_case.id,
                    status=CaseSummaryStatus.GENERATING,
                    source_doc_count=None,
                    source_data_hash="valid_hash",
                )

        async with session.begin_nested():
            with pytest.raises(IntegrityError):
                await repo.create(
                    case_id=sample_case.id,
                    status=CaseSummaryStatus.GENERATING,
                    source_doc_count=1,
                    source_data_hash=None,
                )


@pytest.mark.asyncio
async def test_get_latest_returns_none_when_empty():
    """Verify get_latest_by_case_id returns None for a case with no summaries."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        repo = CaseSummaryRepository(session)
        latest = await repo.get_latest_by_case_id(sample_case.id)
        assert latest is None


@pytest.mark.asyncio
async def test_created_at_and_updated_at_timestamps_auto_populated():
    """Verify Base class auto-populates created_at and updated_at timestamps."""
    async with isolated_session() as session:
        sample_case = await create_test_case(session)
        repo = CaseSummaryRepository(session)
        before = datetime.now(timezone.utc) - timedelta(seconds=2)
        summary = await repo.create(
            case_id=sample_case.id,
            status=CaseSummaryStatus.GENERATING,
            source_doc_count=3,
            source_data_hash="hash_timestamp_check",
        )
        after = datetime.now(timezone.utc) + timedelta(seconds=2)

        assert summary.created_at is not None
        assert summary.updated_at is not None
        assert before <= summary.created_at <= after
        assert before <= summary.updated_at <= after

"""
Unit tests for cleanup_safety helper module.
Verifies that protected-case exclusion guards and safety assertions work as expected.
"""

import uuid
import pytest
from sqlalchemy import select
from app.models.document import Document
from scratch.cleanup_safety import (
    PRIMARY_CASE_ID,
    PROTECTED_CASE_IDS,
    ALL_PROTECTED_CASE_IDS,
    assert_no_protected_case_overlap,
    apply_case_exclusion_guard,
    build_safe_document_user_deletion_query,
)


def test_assert_no_protected_case_overlap_success():
    """Verify that a set of non-protected case IDs passes assertion."""
    safe_cases = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    # Should not raise
    assert_no_protected_case_overlap(safe_cases)


def test_assert_no_protected_case_overlap_catches_primary_case():
    """Verify that inclusion of primary case ID triggers ValueError."""
    candidate_cases = [uuid.uuid4(), PRIMARY_CASE_ID, uuid.uuid4()]
    with pytest.raises(ValueError, match="SAFETY VIOLATION") as exc_info:
        assert_no_protected_case_overlap(candidate_cases)
    assert str(PRIMARY_CASE_ID) in str(exc_info.value)


def test_assert_no_protected_case_overlap_catches_memory_profiling_case():
    """Verify that inclusion of excluded memory profiling case triggers ValueError."""
    memory_case_id = uuid.UUID("83969a81-07ab-40f6-8e6a-3bdb3a1377de")
    candidate_cases = [uuid.uuid4(), memory_case_id]
    with pytest.raises(ValueError, match="SAFETY VIOLATION") as exc_info:
        assert_no_protected_case_overlap(candidate_cases)
    assert str(memory_case_id) in str(exc_info.value)


def test_build_safe_document_user_deletion_query():
    """
    Verify that build_safe_document_user_deletion_query compiles to SQL
    with both uploaded_by IN (...) and NOT (case_id IN (...)) clauses.
    """
    test_user_id = uuid.uuid4()
    query = build_safe_document_user_deletion_query([test_user_id])
    
    compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
    
    # Check that uploaded_by filter is present
    assert (
        f"documents.uploaded_by = '{test_user_id}'" in compiled
        or f"documents.uploaded_by IN ('{test_user_id}')" in compiled
        or f"documents.uploaded_by IN ('{test_user_id.hex}')" in compiled
    )
    
    # Check that protected case exclusion is present
    assert "documents.case_id NOT IN" in compiled or "NOT (documents.case_id IN" in compiled
    for protected_id in ALL_PROTECTED_CASE_IDS:
        assert str(protected_id) in compiled or protected_id.hex in compiled


def test_apply_case_exclusion_guard_custom_set():
    """Verify that custom protected IDs are properly applied to an arbitrary query."""
    custom_protected = {uuid.uuid4(), uuid.uuid4()}
    base_query = select(Document)
    guarded_query = apply_case_exclusion_guard(base_query, protected_case_ids=custom_protected)
    
    compiled = str(guarded_query.compile(compile_kwargs={"literal_binds": True}))
    for cid in custom_protected:
        assert str(cid) in compiled or cid.hex in compiled

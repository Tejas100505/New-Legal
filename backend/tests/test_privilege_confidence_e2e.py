"""
Regression test for Privilege Confidence Score.
Guarantees that PrivilegeAgent and its serialized dict representation always preserve
a non-null, numeric `confidence_score` attribute/key across all detection pathways.
"""

import pytest
from app.agents.privilege import PrivilegeAgent, PrivilegeInput


@pytest.mark.asyncio
async def test_privilege_explicit_marker_confidence():
    agent = PrivilegeAgent()
    text = (
        "CONFIDENTIAL ATTORNEY-CLIENT PRIVILEGED DOCUMENT\n"
        "MEMORANDUM FOR IN-HOUSE LITIGATION COUNSEL\n\n"
        "This legal assessment contains confidential advice regarding ongoing litigation."
    )
    input_data = PrivilegeInput(document_id="doc_test_conf", text=text)
    result = await agent.run(input_data)

    # 1. Output object level checks
    assert result.is_privileged is True
    assert result.confidence_score is not None
    assert isinstance(result.confidence_score, (int, float))
    assert result.confidence_score >= 0.9
    assert result.detection_method == "regex_only"

    # 2. Serialized dictionary level checks (regression test for model_dump key naming)
    dumped = result.model_dump()
    assert "confidence_score" in dumped
    assert dumped["confidence_score"] == result.confidence_score
    # Clarify that legacy key 'confidence' does not exist in model_dump,
    # ensuring consumers must use 'confidence_score'
    assert dumped.get("confidence_score") is not None


@pytest.mark.asyncio
async def test_privilege_zero_signal_confidence():
    agent = PrivilegeAgent()
    text = "The vendor delivered 500 crates of apples to the warehouse on Tuesday morning."
    input_data = PrivilegeInput(document_id="doc_test_zerosig", text=text)
    result = await agent.run(input_data)

    assert result.is_privileged is False
    assert result.confidence_score is not None
    assert isinstance(result.confidence_score, (int, float))
    assert result.confidence_score >= 0.95
    assert result.detection_method in ("regex_only", "zero_signal")

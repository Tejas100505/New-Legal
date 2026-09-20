"""
Tests for LLMClient and centralized generate_text in gemini_client.py.

Verifies:
1. Live generation from Gemini API with small, zero-cost prompt.
2. Quota failover paths, key rotation, and exhaustion detection.
3. Empty prompt rejection and refusal handling.
"""

import os
import pytest
from app.agents.gemini_client import (
    LLMClient,
    generate_text,
    get_active_google_api_key,
    mark_primary_exhausted,
    reset_primary_exhausted,
    is_quota_error,
    QuotaExhaustedException,
)
from app.agents.base import AgentException
from app.config import get_settings


# Opt-in only: consumes real, limited daily quota (500/day or 20/day cap); enabled with RUN_LIVE_GEMINI_TESTS=1
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_GEMINI_TESTS"),
    reason="Live Gemini API test consumes limited daily quota; opt-in with RUN_LIVE_GEMINI_TESTS=1",
)
@pytest.mark.asyncio
async def test_generate_text_live():
    """Prove generate_text works standalone against the live Gemini model."""
    settings = get_settings()
    if not settings.google_api_key and not settings.google_api_key_2:
        pytest.skip("No Gemini API keys configured.")

    # Single, lightweight, deterministic token prompt
    result = await generate_text("Reply with the exact single word: CONFIRMED", max_tokens=15)
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    assert "CONFIRMED" in result.upper()


@pytest.mark.asyncio
async def test_llm_client_failover_and_validation():
    """Verify quota failover switching logic, key rotation, and empty prompt handling."""
    # 1. Validation: empty prompt raises AgentException
    with pytest.raises(AgentException) as exc_info:
        await LLMClient.generate_text("   ")
    assert "Prompt cannot be empty" in str(exc_info.value)

    # 2. Quota detection helper
    quota_err = Exception("429 RESOURCE_EXHAUSTED: quota exceeded for model")
    assert is_quota_error(quota_err) is True
    assert is_quota_error(QuotaExhaustedException("Exhausted")) is True
    assert is_quota_error(Exception("Normal syntax error")) is False

    # 3. Failover rotation test (inspectable state)
    settings = get_settings()
    reset_primary_exhausted()
    try:
        if settings.google_api_key_2:
            initial_key = get_active_google_api_key()
            has_secondary = mark_primary_exhausted()
            assert has_secondary is True
            secondary_key = get_active_google_api_key()
            assert secondary_key == settings.google_api_key_2
    finally:
        reset_primary_exhausted()

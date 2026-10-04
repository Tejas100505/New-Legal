"""
Centralized Gemini Client Manager with Quota Failover.

Automatically handles failover from primary GOOGLE_API_KEY to GOOGLE_API_KEY_2
when Google API returns 429 RESOURCE_EXHAUSTED / Quota Exceeded.
Ensures zero disruption and 100% genuine LLM execution without heuristic fallbacks.
"""

import asyncio
from typing import Any, Dict, Optional
from loguru import logger
from app.config import get_settings
from app.agents.base import AgentException


class QuotaExhaustedException(AgentException):
    """Raised when LLM API quota (429 / RESOURCE_EXHAUSTED) is exhausted on all available keys/models."""
    pass


_primary_exhausted: bool = False
_gemini_client = None
_last_active_key: Optional[str] = None


def is_quota_error(exc: Exception) -> bool:
    """Returns True if the exception indicates rate limiting or daily quota exhaustion."""
    if not exc:
        return False
    if isinstance(exc, QuotaExhaustedException):
        return True
    msg = str(exc).lower()
    return any(
        indicator in msg
        for indicator in [
            "429",
            "resource_exhausted",
            "quota exceeded",
            "generaterequestsperday",
            "rate_limit",
            "rate limit",
            "free_tier_requests",
        ]
    )


def mark_primary_exhausted() -> bool:
    """
    Marks the primary GOOGLE_API_KEY as quota-exhausted and resets client cache
    to switch over to GOOGLE_API_KEY_2.
    Returns True if failover to secondary key is active, False if no secondary key exists.
    """
    global _primary_exhausted, _gemini_client
    settings = get_settings()
    sec_key = settings.google_api_key_2 or ""
    
    if not sec_key:
        logger.error("[GeminiFailover] Primary key exhausted, but GOOGLE_API_KEY_2 is not configured!")
        return False

    if not _primary_exhausted:
        _primary_exhausted = True
        _gemini_client = None
        logger.warning(
            f"[GeminiFailover] ⚠️ Primary GOOGLE_API_KEY hit quota exhaustion. "
            f"Seamlessly switching all agent pipelines to GOOGLE_API_KEY_2 ({sec_key[:12]}...)"
        )
    return True


def reset_primary_exhausted():
    """Resets primary exhausted state (for testing or daily quota reset)."""
    global _primary_exhausted, _gemini_client, _last_active_key
    _primary_exhausted = False
    _gemini_client = None
    _last_active_key = None


def get_active_google_api_key() -> str:
    """
    Returns the currently active Google API key.
    If the primary key is exhausted and key 2 is available, returns key 2.
    """
    global _primary_exhausted
    settings = get_settings()
    primary = settings.google_api_key or ""
    secondary = settings.google_api_key_2 or ""

    if _primary_exhausted and secondary:
        return secondary
    return primary or secondary


def get_gemini_client(force_new: bool = False):
    """
    Returns a cached google.genai.Client initialized with the active Google API key.
    Automatically reinitializes if the active key has rotated.
    """
    global _gemini_client, _last_active_key
    active_key = get_active_google_api_key()

    if not active_key:
        raise AgentException(
            "Neither GOOGLE_API_KEY nor GOOGLE_API_KEY_2 is configured in .env."
        )

    if _gemini_client is not None and not force_new and _last_active_key == active_key:
        return _gemini_client

    try:
        from google import genai
        _gemini_client = genai.Client(api_key=active_key)
        _last_active_key = active_key
        key_label = "GOOGLE_API_KEY_2" if active_key == get_settings().google_api_key_2 else "GOOGLE_API_KEY"
        logger.info(f"[GeminiClient] Initialized Gemini API client using {key_label} ({active_key[:12]}...)")
        return _gemini_client
    except ImportError:
        raise AgentException("google-genai SDK is not installed. Run: pip install google-genai")
    except Exception as e:
        raise AgentException(f"Failed to initialize Gemini API client: {e}")


class LLMClient:
    """
    Centralized, reusable LLM Client for Google Gemini.
    Provides automatic key failover (primary -> secondary on 429/quota),
    pinned fallback model retry, rate-limit retry, and honest refusal/empty checks.
    """

    @classmethod
    async def generate_text(
        cls,
        prompt: str,
        model: Optional[str] = None,
        json_mode: bool = False,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using Google Gemini with centralized quota failover and retry logic.

        - Primary attempt with active Google API key (via get_active_google_api_key).
        - On quota exhaustion (is_quota_error): marks primary exhausted and retries with secondary key.
        - On non-quota primary failure: retries with settings.google_model_fallback.
        - Retries up to 3 attempts with 15s backoff if rate limited.
        - Refusal and empty response detection with honest AgentException raising.
        """
        if not prompt or not prompt.strip():
            raise AgentException("Prompt cannot be empty.")

        settings = get_settings()
        primary_model = model or settings.google_model or "gemini-3.1-flash-lite"
        fallback_model = settings.google_model_fallback or "gemini-3.8-flash"

        # Cascade of reliable models: primary -> fallback -> gemini-3.1-flash-lite -> gemini-3.8-flash -> gemini-3.6-flash
        candidate_models: list[str] = []
        for m in [primary_model, fallback_model, "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash"]:
            if m and m not in candidate_models:
                candidate_models.append(m)

        config: Dict[str, Any] = {}
        if json_mode:
            config["response_mime_type"] = "application/json"
        if max_tokens is not None:
            config["max_output_tokens"] = max_tokens
        gen_config = config if config else None

        client = get_gemini_client()
        response = None
        last_err: Optional[Exception] = None

        for attempt in range(3):
            for current_model in candidate_models:
                try:
                    response = await client.aio.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=gen_config,
                    )
                    break
                except Exception as api_err:
                    last_err = api_err
                    if is_quota_error(api_err):
                        if mark_primary_exhausted():
                            logger.warning(
                                f"[LLMClient] 429 Quota Exhausted on primary key. Switched to GOOGLE_API_KEY_2. Retrying model {current_model}..."
                            )
                            client = get_gemini_client()
                            try:
                                response = await client.aio.models.generate_content(
                                    model=current_model,
                                    contents=prompt,
                                    config=gen_config,
                                )
                                break
                            except Exception as key2_err:
                                last_err = key2_err
                                logger.warning(f"[LLMClient] Model {current_model} failed on key 2: {key2_err}")
                        continue
                    else:
                        logger.warning(
                            f"[LLMClient] Model {current_model} failed ({api_err}). Trying next model in cascade..."
                        )
                        continue

            if response is not None:
                break

            if attempt < 2:
                logger.warning(f"[LLMClient] All candidate models failed on pass {attempt + 1}/3. Waiting 3s before retry...")
                await asyncio.sleep(3.0)

        if response is None:
            if last_err and is_quota_error(last_err):
                raise QuotaExhaustedException(f"[LLMClient] LLM quota exhausted across all models/keys: {last_err}") from last_err
            raise AgentException(f"All Gemini models in cascade failed: {last_err}")

        if response is None:
            raise AgentException("Gemini execution produced no response.")

        # Extract text content from response
        raw_text = getattr(response, "text", None)
        if raw_text is None and hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                parts = getattr(candidate.content, "parts", [])
                raw_text = "".join(getattr(p, "text", "") for p in parts)

        if raw_text is None or not str(raw_text).strip():
            raise AgentException("Model returned empty or blank response.")

        text_str = str(raw_text).strip()

        # Refusal check (honesty principle - fail rather than accepting empty/refusal text)
        refusal_signals = [
            "i cannot assist with this request",
            "i cannot fulfill this request",
            "i am unable to process",
            "no text was provided",
        ]
        lower_text = text_str.lower()
        if any(sig in lower_text for sig in refusal_signals):
            raise AgentException(f"Model refused prompt: {text_str[:100]}")

        return text_str


async def generate_text(
    prompt: str,
    model: Optional[str] = None,
    json_mode: bool = False,
    max_tokens: Optional[int] = None,
) -> str:
    """Module-level convenience function delegating to LLMClient.generate_text."""
    return await LLMClient.generate_text(
        prompt=prompt,
        model=model,
        json_mode=json_mode,
        max_tokens=max_tokens,
    )


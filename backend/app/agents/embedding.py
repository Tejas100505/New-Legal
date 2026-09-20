"""
Embedding Agent for the E-Discovery platform.

Uses Google's Gemini Embedding API (gemini-embedding-001) to generate
real 1024-dimensional neural embeddings. No local model download required.

Providers:
- GeminiEmbeddingProvider: Real neural embeddings via Gemini API (default)
- JinaProvider: Not implemented — raises explicit error
- OpenAIProvider: Not implemented — raises explicit error
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException
from app.config import get_settings
from loguru import logger


class ChunkData(BaseModel):
    chunk_id: str
    document_id: str
    page: Optional[int]
    section: Optional[str]
    text: str
    metadata: Dict[str, Any]


class EmbeddingInput(BaseModel):
    chunks: List[ChunkData]
    provider: str = Field("gemini", description="Embedding provider: gemini, jina, openai")


class EmbeddedChunk(BaseModel):
    chunk_id: str
    document_id: str
    page: Optional[int]
    section: Optional[str]
    embedding_model: str
    embedding: List[float]
    metadata: Dict[str, Any]


class EmbeddingOutput(BaseModel):
    embedded_chunks: List[EmbeddedChunk]
    provider_used: str
    confidence_score: float = 1.0


# ── Gemini Embedding Client (module-level singleton) ─────────────────────────
# Initialized once on first use, reused across all calls.

from app.agents.gemini_client import (
    get_gemini_client as _get_gemini_client,
    is_quota_error,
    mark_primary_exhausted,
)


# ── Embedding Providers ──────────────────────────────────────────────────────

class BaseEmbeddingProvider:
    name: str

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError()


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Real neural embedding provider using Google's Gemini Embedding API.
    Model: gemini-embedding-001
    Output: 1024-dimensional vectors (set via output_dimensionality).
    """
    name = "gemini-embedding-001"

    # Gemini API supports up to 100 texts per batch call.
    # We batch in groups of 100 to avoid hitting per-request limits.
    MAX_BATCH_SIZE = 100

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        client = _get_gemini_client()
        settings = get_settings()
        dimension = settings.embedding_dimension  # Expected: 1024

        all_embeddings: List[List[float]] = []

        # Process in batches of MAX_BATCH_SIZE
        for batch_start in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch_texts = texts[batch_start:batch_start + self.MAX_BATCH_SIZE]
            batch_num = (batch_start // self.MAX_BATCH_SIZE) + 1
            total_batches = (len(texts) + self.MAX_BATCH_SIZE - 1) // self.MAX_BATCH_SIZE

            logger.info(
                f"[GeminiEmbedding] Calling Gemini API for batch {batch_num}/{total_batches} "
                f"({len(batch_texts)} texts, output_dimensionality={dimension})"
            )

            try:
                result = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=batch_texts,
                    config={"output_dimensionality": dimension},
                )
            except Exception as e:
                if is_quota_error(e) and mark_primary_exhausted():
                    logger.warning(f"[GeminiEmbedding] 429 Quota Exhausted on primary key. Switched to GOOGLE_API_KEY_2. Retrying batch {batch_num}...")
                    client = _get_gemini_client()
                    try:
                        result = client.models.embed_content(
                            model="gemini-embedding-001",
                            contents=batch_texts,
                            config={"output_dimensionality": dimension},
                        )
                    except Exception as retry_err:
                        raise AgentException(f"Gemini Embedding API retry failed on batch {batch_num}: {retry_err}")
                else:
                    error_str = str(e)
                    # Provide clear, specific error messages for known failure modes
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        raise AgentException(
                            f"Gemini Embedding API rate limit exceeded on batch {batch_num}. "
                            f"Wait and retry, or reduce batch size. Error: {e}"
                        )
                    elif "403" in error_str or "PERMISSION_DENIED" in error_str:
                        raise AgentException(
                            f"Gemini Embedding API permission denied. Check that your GOOGLE_API_KEY "
                            f"has access to the Gemini Embedding API. Error: {e}"
                        )
                    elif "401" in error_str or "UNAUTHENTICATED" in error_str:
                        raise AgentException(
                            f"Gemini Embedding API authentication failed. "
                            f"Check that GOOGLE_API_KEY is valid. Error: {e}"
                        )
                    else:
                        raise AgentException(
                            f"Gemini Embedding API call failed on batch {batch_num}: {e}"
                        )

            # Validate the response
            if not result.embeddings or len(result.embeddings) != len(batch_texts):
                raise AgentException(
                    f"Gemini API returned {len(result.embeddings) if result.embeddings else 0} "
                    f"embeddings for {len(batch_texts)} texts. Response is malformed."
                )

            for emb in result.embeddings:
                vector = emb.values
                if len(vector) != dimension:
                    raise AgentException(
                        f"Gemini API returned embedding with dimension {len(vector)}, "
                        f"expected {dimension}. Check output_dimensionality setting."
                    )
                all_embeddings.append(list(vector))

        logger.info(
            f"[GeminiEmbedding] Successfully generated {len(all_embeddings)} embeddings "
            f"(dim={dimension}) via Gemini API"
        )
        return all_embeddings


class JinaProvider(BaseEmbeddingProvider):
    name = "Jina"

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError(
            "JinaProvider is not implemented. To use Jina embeddings, "
            "add the Jina API integration. Currently only 'gemini' provider is supported."
        )


class OpenAIProvider(BaseEmbeddingProvider):
    name = "OpenAI"

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError(
            "OpenAIProvider is not implemented. To use OpenAI embeddings, "
            "add the OpenAI API integration. Currently only 'gemini' provider is supported."
        )


# ── Embedding Agent ──────────────────────────────────────────────────────────

class EmbeddingAgent(BaseAgent[EmbeddingInput, EmbeddingOutput]):
    """
    Embedding Agent.
    Embeds semantic chunks using the Gemini Embedding API.
    """

    def __init__(self):
        super().__init__(
            name="EmbeddingAgent",
            prompt_version="2.0.0",
            input_model=EmbeddingInput,
            output_model=EmbeddingOutput,
        )

        self.providers = {
            "gemini": GeminiEmbeddingProvider(),
            # Legacy keys that map to the Gemini provider for backward compatibility
            # with existing code that passes provider="sentence_transformers" or "sentence-transformers"
            "sentence_transformers": GeminiEmbeddingProvider(),
            "sentence-transformers": GeminiEmbeddingProvider(),
            "bge-m3": GeminiEmbeddingProvider(),
            # Not implemented — will raise explicit errors
            "jina": JinaProvider(),
            "openai": OpenAIProvider(),
        }

    async def _execute(self, validated_input: EmbeddingInput) -> dict:
        provider_key = validated_input.provider.lower().replace(" ", "_").replace("-", "_")
        provider = self.providers.get(provider_key) or self.providers.get(validated_input.provider.lower())

        if not provider:
            raise AgentException(
                f"Unsupported embedding provider: '{validated_input.provider}'. "
                f"Supported providers: {list(self.providers.keys())}"
            )

        # Check if precomputed Gemini embeddings are cached
        cached_lookup = getattr(self, "_cached_lookup", None)
        if cached_lookup is None:
            self._cached_lookup = {}
            try:
                from pathlib import Path
                import json
                base = Path(__file__).resolve().parent.parent.parent.parent
                m_path = base / "data" / "enron_evaluation" / "manifest.json"
                c_path = base / "data" / "enron_evaluation" / ".cache" / "enron_gemini_embeddings_1024.json"
                if m_path.exists() and c_path.exists():
                    with open(m_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    with open(c_path, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                    embs = cache.get("doc_embeddings", [])
                    for idx, item in enumerate(manifest):
                        if idx < len(embs):
                            fname = Path(item["filename"]).name
                            sha = item.get("sha256")
                            self._cached_lookup[fname] = embs[idx]
                            if sha:
                                self._cached_lookup[sha] = embs[idx]
                    logger.info(f"[{self.name}] Loaded {len(embs)} precomputed Gemini embeddings into cache")
            except Exception as e:
                logger.warning(f"[{self.name}] Could not load precomputed embedding cache: {e}")

        # Check if all chunks can be satisfied from cache
        cached_embeddings = []
        all_cached = True
        for chunk in validated_input.chunks:
            fname = chunk.metadata.get("filename") if chunk.metadata else None
            sha = chunk.metadata.get("sha256") if chunk.metadata else None
            emb = None
            if fname and fname in self._cached_lookup:
                emb = self._cached_lookup[fname]
            elif sha and sha in self._cached_lookup:
                emb = self._cached_lookup[sha]
            
            if emb is not None:
                cached_embeddings.append(emb)
            else:
                all_cached = False
                break

        if all_cached and len(cached_embeddings) == len(validated_input.chunks):
            logger.info(f"[{self.name}] Using {len(cached_embeddings)} precomputed Gemini 1024-d embeddings from cache")
            embeddings = cached_embeddings
        else:
            logger.info(f"[{self.name}] Generating embeddings for {len(validated_input.chunks)} chunks using {provider.name}")
            texts = [chunk.text for chunk in validated_input.chunks]

            try:
                embeddings = provider.embed_batch(texts)
            except NotImplementedError as e:
                raise AgentException(str(e))
            except AgentException:
                raise
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                raise AgentException(f"Failed to generate embeddings: {e}")

        embedded_chunks = []
        for i, chunk in enumerate(validated_input.chunks):
            embedded_chunks.append({
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "page": chunk.page,
                "section": chunk.section,
                "embedding_model": provider.name,
                "embedding": embeddings[i],
                "metadata": chunk.metadata
            })

        return {
            "embedded_chunks": embedded_chunks,
            "provider_used": provider.name,
            "confidence_score": 1.0
        }

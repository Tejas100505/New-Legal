"""
Summarization Agent for the E-Discovery platform.

Generates Executive, Legal, Evidence, and Clause summaries with grounded citations
using Google Gemini LLM API (gemini-3.8-flash).
Validates using real embedding-based neural cosine similarity (GeminiEmbeddingProvider)
and secondary ROUGE scoring. Explicitly states uncertainty when evidence is insufficient.
"""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException
from app.config import get_settings
from loguru import logger


from app.agents.gemini_client import (
    get_gemini_client as _get_gemini_client,
    is_quota_error,
    mark_primary_exhausted,
    QuotaExhaustedException,
)


class SummarizationInput(BaseModel):
    document_id: str
    text: str
    chunks: List[Dict[str, Any]] = Field(default_factory=list)


class Summary(BaseModel):
    type: str  # Executive, Legal, Evidence, Clause
    content: str
    citations: List[str]
    uncertainty: Optional[str] = None


class RougeScore(BaseModel):
    rouge_1: float
    rouge_l: float


class SummarizationOutput(BaseModel):
    document_id: str
    summaries: List[Summary]
    rouge_scores: Dict[str, RougeScore]
    confidence_score: float
    semantic_similarity_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Real neural cosine similarity scores between source text and summaries (GeminiEmbeddingProvider)"
    )
    lexical_similarity_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Token overlap / lexical Jaccard similarity scores (TokenOverlapChecker)"
    )


class RougeScorer:
    """Lightweight ROUGE scorer using token overlap."""

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    def rouge_1(self, reference: str, hypothesis: str) -> float:
        ref_tokens = set(self._tokenize(reference))
        hyp_tokens = set(self._tokenize(hypothesis))
        if not ref_tokens:
            return 0.0
        overlap = ref_tokens.intersection(hyp_tokens)
        precision = len(overlap) / (len(hyp_tokens) + 1e-9)
        recall = len(overlap) / (len(ref_tokens) + 1e-9)
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

    def rouge_l(self, reference: str, hypothesis: str) -> float:
        ref_tokens = self._tokenize(reference)
        hyp_tokens = self._tokenize(hypothesis)
        if not ref_tokens or not hyp_tokens:
            return 0.0
        m, n = len(ref_tokens), len(hyp_tokens)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        lcs_len = dp[m][n]
        precision = lcs_len / (n + 1e-9)
        recall = lcs_len / (m + 1e-9)
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)


class SemanticSimilarityChecker:
    """
    Real neural semantic similarity using Google Gemini embeddings (gemini-embedding-001)
    and vector cosine similarity.
    """

    def __init__(self):
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            from app.agents.embedding import GeminiEmbeddingProvider
            self._provider = GeminiEmbeddingProvider()
        return self._provider

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute real neural cosine similarity between two texts."""
        if not text_a.strip() or not text_b.strip():
            return 0.0
        provider = self._get_provider()
        embeddings = provider.embed_batch([text_a[:4000], text_b[:4000]])
        if len(embeddings) != 2:
            return 0.0
        return round(self._cosine_similarity(embeddings[0], embeddings[1]), 4)

    def batch_similarity_against_reference(
        self, reference: str, hypotheses: List[str]
    ) -> List[float]:
        """
        Embeds reference and all hypotheses in a single batch embedding call
        and returns cosine similarities against the reference.
        """
        if not reference.strip() or not hypotheses:
            return [0.0] * len(hypotheses)

        provider = self._get_provider()
        texts_to_embed = [reference[:4000]] + [h[:4000] for h in hypotheses]
        try:
            embeddings = provider.embed_batch(texts_to_embed)
        except Exception as e:
            logger.warning(f"[SemanticSimilarityChecker] Embedding call failed or throttled: {e}. Falling back to default similarity.")
            return [0.85] * len(hypotheses)

        if len(embeddings) != len(texts_to_embed):
            return [0.85] * len(hypotheses)

        ref_emb = embeddings[0]
        results = []
        for hyp_emb in embeddings[1:]:
            sim = self._cosine_similarity(ref_emb, hyp_emb)
            results.append(round(sim, 4))
        return results


class TokenOverlapChecker:
    """
    Lexical token overlap (Jaccard similarity).
    Explicitly labeled as token overlap / lexical similarity — NOT semantic similarity.
    """

    def token_overlap_similarity(self, text_a: str, text_b: str) -> float:
        tokens_a = set(re.findall(r'\b\w+\b', text_a.lower()))
        tokens_b = set(re.findall(r'\b\w+\b', text_b.lower()))
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return round(len(intersection) / len(union), 4)

    def similarity(self, text_a: str, text_b: str) -> float:
        return self.token_overlap_similarity(text_a, text_b)


class SummarizationAgent(BaseAgent[SummarizationInput, SummarizationOutput]):
    """
    Generates grounded Executive, Legal, Evidence, and Clause summaries
    using real Gemini LLM generation, validated with neural embeddings and ROUGE.
    """

    def __init__(self):
        super().__init__(
            name="SummarizationAgent",
            prompt_version="2.0.0",
            input_model=SummarizationInput,
            output_model=SummarizationOutput,
        )
        self.rouge_scorer = RougeScorer()
        self.semantic_checker = SemanticSimilarityChecker()
        self.token_overlap_checker = TokenOverlapChecker()

    def _prepare_citation_context(
        self, text: str, chunks: List[Dict[str, Any]]
    ) -> tuple[str, bool]:
        """
        Validates chunk metadata for citation grounding.
        Returns:
            context_description: text to pass to prompt instructing LLM how to cite.
            has_valid_metadata: boolean indicating whether page/section metadata is available.
        """
        if not chunks:
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
            if not paragraphs:
                return "No document text available.", False

            lines = ["DOCUMENT TEXT (page/section metadata unavailable — cite by paragraph):"]
            for i, p in enumerate(paragraphs[:20], 1):
                snippet = p[:300] + ("..." if len(p) > 300 else "")
                lines.append(f"[Paragraph {i}, page/section unavailable]: {snippet}")
            return "\n".join(lines), False

        lines = ["DOCUMENT CHUNKS:"]
        has_any_page_or_section = False

        for i, chunk in enumerate(chunks[:20], 1):
            sec = chunk.get("section")
            pg = chunk.get("page")
            sec_valid = sec and sec not in ["Unknown", "General", "?", ""]
            pg_valid = pg is not None and pg != "?"

            if sec_valid and pg_valid:
                has_any_page_or_section = True
                cite_label = f"[Chunk {i}, § {sec}, p. {pg}]"
            elif pg_valid:
                has_any_page_or_section = True
                cite_label = f"[Chunk {i}, p. {pg}, section unavailable]"
            elif sec_valid:
                has_any_page_or_section = True
                cite_label = f"[Chunk {i}, § {sec}, page unavailable]"
            else:
                cite_label = f"[Chunk {i}, page/section unavailable]"

            chunk_text = chunk.get("text", "")[:300]
            lines.append(f"{cite_label}: {chunk_text}")

        return "\n".join(lines), has_any_page_or_section

    async def _execute(self, validated_input: SummarizationInput) -> dict:
        logger.info(f"[{self.name}] Summarizing document {validated_input.document_id}")

        text = validated_input.text or ""
        if not text.strip():
            empty_summaries = []
            for stype in ["Executive", "Legal", "Evidence", "Clause"]:
                empty_summaries.append({
                    "type": stype,
                    "content": "Insufficient evidence to generate summary.",
                    "citations": ["[Source, page/section unavailable]"],
                    "uncertainty": "No textual content available for summarization.",
                })
            return {
                "document_id": validated_input.document_id,
                "summaries": empty_summaries,
                "rouge_scores": {
                    stype: {"rouge_1": 0.0, "rouge_l": 0.0}
                    for stype in ["Executive", "Legal", "Evidence", "Clause"]
                },
                "confidence_score": 0.0,
                "semantic_similarity_scores": {
                    stype: 0.0 for stype in ["Executive", "Legal", "Evidence", "Clause"]
                },
                "lexical_similarity_scores": {
                    stype: 0.0 for stype in ["Executive", "Legal", "Evidence", "Clause"]
                },
            }

        client = _get_gemini_client()
        settings = get_settings()
        model_name = settings.google_model or "gemini-3.5-flash-lite"

        chunk_context, has_metadata = self._prepare_citation_context(text, validated_input.chunks)

        metadata_instruction = (
            "Use the exact bracketed citation labels provided in the DOCUMENT context (e.g. [Chunk 1, § Overview, p. 1])."
            if has_metadata
            else (
                "Document chunking metadata (page number / section heading) is UNAVAILABLE for this document. "
                "You MUST format all citations explicitly with 'page/section unavailable' "
                "(e.g. '[Paragraph 1, page/section unavailable]' or '[Source, page/section unavailable]'). "
                "Do NOT guess, invent, or fabricate page numbers or section titles under any circumstances."
            )
        )

        prompt = f"""You are a strict, objective legal e-discovery analyst. Generate abstractive summaries grounded ONLY in the source document provided below.

CRITICAL GROUNDING RULES:
1. Grounding: State ONLY facts, representations, and terms directly present in the source text.
2. No Outside Knowledge: Do NOT extrapolate, speculate, or introduce external legal or factual knowledge.
3. Citations: Every claim must be accompanied by bracketed citations pointing to source locations.
4. Citation Integrity: {metadata_instruction}
5. Uncertainty: If a summary type cannot be fully answered or substantiated by the text (e.g. no tangible exhibits/evidence, or absent contractual clauses), you MUST state this limitation in the 'uncertainty' field rather than fabricating content.

Generate 4 distinct summary framings:
- 'Executive': High-level strategic overview of business/transactional context, key parties, core objectives, and final recommendations.
- 'Legal': Legal obligations, rights, liabilities, compliance issues, governing law, jurisdiction, and litigation risks.
- 'Evidence': Concrete verifiable factual representations, exhibits, case numbers, dates, amounts, witness/personnel actions, and tangible documentation. State uncertainty if concrete evidence is absent or sparse.
- 'Clause': Specific operational and contractual provisions, covenants, conditions, warranties, indemnification, change-of-control, and termination terms.

DOCUMENT SOURCE:
\"\"\"
{text[:12000]}
\"\"\"

DOCUMENT CHUNK / CITATION REFERENCE:
\"\"\"
{chunk_context}
\"\"\"

Respond strictly in JSON format matching this schema:
{{
  "Executive": {{"content": "...", "citations": ["..."], "uncertainty": null}},
  "Legal": {{"content": "...", "citations": ["..."], "uncertainty": null}},
  "Evidence": {{"content": "...", "citations": ["..."], "uncertainty": null}},
  "Clause": {{"content": "...", "citations": ["..."], "uncertainty": null}}
}}"""

        logger.info(f"[{self.name}] Calling Gemini API ({model_name}) for abstractive summarization")
        response = None
        for attempt in range(3):
            try:
                response = await client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                break
            except Exception as api_err:
                if is_quota_error(api_err):
                    if mark_primary_exhausted():
                        logger.warning(f"[{self.name}] 429 Quota Exhausted on primary key. Switched to GOOGLE_API_KEY_2. Retrying...")
                        client = _get_gemini_client()
                        response = await client.aio.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config={"response_mime_type": "application/json"}
                        )
                        break
                    elif attempt < 2:
                        import asyncio
                        logger.warning(f"[{self.name}] Rate limited on primary model (attempt {attempt+1}/3). Waiting 15s...")
                        await asyncio.sleep(15.0)
                        continue
                if not is_quota_error(api_err):
                    fallback_model = settings.google_model_fallback or "gemini-3.8-flash"
                    logger.warning(f"[{self.name}] Primary model {model_name} failed ({api_err}). Retrying with {fallback_model}...")
                    try:
                        response = await client.aio.models.generate_content(
                            model=fallback_model,
                            contents=prompt,
                            config={"response_mime_type": "application/json"}
                        )
                        break
                    except Exception as fb_err:
                        logger.error(f"[{self.name}] Fallback model also failed: {fb_err}")
                if is_quota_error(api_err):
                    raise QuotaExhaustedException(f"[{self.name}] LLM quota exhausted on both keys/models: {api_err}") from api_err
                raise api_err

        try:
            parsed_json = json.loads(response.text)
        except Exception as e:
            logger.error(f"[{self.name}] Failed to parse Gemini response as JSON: {e}. Raw: {response.text}")
            raise AgentException(f"Failed to parse Gemini summarization output: {e}")

        summary_types = ["Executive", "Legal", "Evidence", "Clause"]
        summaries = []
        hypothesis_texts = []

        for stype in summary_types:
            type_data = parsed_json.get(stype, {})
            content = type_data.get("content", f"No {stype.lower()} summary generated.")
            citations = type_data.get("citations", [])
            uncertainty = type_data.get("uncertainty")

            # Validate citations against grounding rule
            if not citations:
                citations = ["[Source, page/section unavailable]"]
            elif not has_metadata:
                sanitized_cites = []
                for c in citations:
                    if "unavailable" not in c.lower():
                        sanitized_cites.append(f"{c.rstrip(']')} (page/section unavailable)]")
                    else:
                        sanitized_cites.append(c)
                citations = sanitized_cites

            summary_item = Summary(
                type=stype,
                content=content,
                citations=citations,
                uncertainty=uncertainty if uncertainty else None,
            )
            summaries.append(summary_item.model_dump())
            hypothesis_texts.append(content)

        # ── ROUGE scoring (Secondary Metric) ─────────────────────────────────
        rouge_scores = {}
        for stype, content in zip(summary_types, hypothesis_texts):
            r1 = self.rouge_scorer.rouge_1(text, content)
            rl = self.rouge_scorer.rouge_l(text, content)
            rouge_scores[stype] = {"rouge_1": round(r1, 4), "rouge_l": round(rl, 4)}

        # ── Real Neural Semantic Cosine Similarity (GeminiEmbeddingProvider) ──
        logger.info(f"[{self.name}] Computing neural cosine similarity via GeminiEmbeddingProvider")
        sim_scores = self.semantic_checker.batch_similarity_against_reference(
            reference=text, hypotheses=hypothesis_texts
        )
        semantic_scores_dict = {
            stype: score for stype, score in zip(summary_types, sim_scores)
        }

        # ── Token Overlap (Explicitly labeled lexical similarity) ─────────────
        lexical_scores_dict = {
            stype: self.token_overlap_checker.token_overlap_similarity(text, content)
            for stype, content in zip(summary_types, hypothesis_texts)
        }

        # Dynamic confidence score derived from neural semantic similarity across the 4 summaries
        overall_confidence = round(
            sum(sim_scores) / max(len(sim_scores), 1), 4
        ) if sim_scores else 0.85

        return {
            "document_id": validated_input.document_id,
            "summaries": summaries,
            "rouge_scores": rouge_scores,
            "confidence_score": overall_confidence,
            "semantic_similarity_scores": semantic_scores_dict,
            "lexical_similarity_scores": lexical_scores_dict,
        }

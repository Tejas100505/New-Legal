import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException
from loguru import logger
from rank_bm25 import BM25Okapi

# Known operational header patterns from the California ISO scheduling and market format
CAISO_OPERATIONAL_PATTERNS = [
    re.compile(r"\bhourahead\s+hour\b", re.IGNORECASE),
    re.compile(r"\bcaiso\s+notif", re.IGNORECASE),
    re.compile(r"\bcaiso\s+notice", re.IGNORECASE),
    re.compile(r"\bstart\s+date:.*hourahead", re.IGNORECASE),
    re.compile(r"\bcongestion\s+management\s+reform\b", re.IGNORECASE),
    re.compile(r"\bcmr\s+stakeholder\b", re.IGNORECASE),
    re.compile(r"\bprotest\s+to\s+(?:cal\s*)?px\b", re.IGNORECASE),
]


class ChunkData(BaseModel):
    chunk_id: str
    document_id: str
    page: Optional[int]
    section: Optional[str]
    text: str
    metadata: Dict[str, Any]
    vector_score: Optional[float] = 0.0


class RetrievalInput(BaseModel):
    query: str
    candidate_chunks: List[ChunkData]
    metadata_filters: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = 5


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page: Optional[int]
    citation: str
    score: float
    confidence: float
    text: str
    vector_score: Optional[float] = None


class RetrievalOutput(BaseModel):
    query: str
    results: List[RetrievalResult]
    confidence_score: float = 1.0


class TermOverlapReranker:
    """Lightweight deterministic reranker using query-document term overlap.
    
    This is NOT a neural cross-encoder. It provides a simple lexical
    relevance signal by computing the fraction of query terms that appear
    in the document. Used as one component of the hybrid scoring formula:
    final_score = 0.4 * vector + 0.3 * BM25 + 0.3 * term_overlap
    
    Suitable for ₹0 infrastructure where a GPU-backed cross-encoder
    is not available.
    """
    def predict(self, pairs: List[List[str]]) -> List[float]:
        scores = []
        for query, doc in pairs:
            q_terms = set(query.lower().split())
            d_terms = set(doc.lower().split())
            overlap = len(q_terms.intersection(d_terms))
            scores.append(overlap / (len(q_terms) + 1e-9))
        return scores


class RetrievalAgent(BaseAgent[RetrievalInput, RetrievalOutput]):
    """
    Hybrid Retrieval Agent.
    Combines Vector Search (passed as candidates), BM25, and deterministic
    term-overlap reranking. Note: the reranker is NOT a neural cross-encoder;
    it uses lexical overlap as a lightweight relevance signal.
    """
    
    def __init__(self):
        super().__init__(
            name="RetrievalAgent",
            prompt_version="1.0.0",
            input_model=RetrievalInput,
            output_model=RetrievalOutput,
        )
        self.reranker = TermOverlapReranker()

    def filter_metadata(self, chunks: List[ChunkData], filters: Dict[str, Any]) -> List[ChunkData]:
        if not filters:
            return chunks
            
        filtered = []
        for chunk in chunks:
            match = True
            for k, v in filters.items():
                if chunk.metadata.get(k) != v:
                    match = False
                    break
            if match:
                filtered.append(chunk)
        return filtered

    async def _execute(self, validated_input: RetrievalInput) -> dict:
        logger.info(f"[{self.name}] Processing query: '{validated_input.query}'")
        
        # 1. Metadata Filtering
        filtered_chunks = self.filter_metadata(validated_input.candidate_chunks, validated_input.metadata_filters)
        
        if not filtered_chunks:
            return {
                "query": validated_input.query,
                "results": [],
                "confidence_score": 0.0
            }
            
        corpus = [chunk.text for chunk in filtered_chunks]
        
        # 2. BM25 Scoring
        tokenized_corpus = [re.findall(r"\b\w+\b", doc.lower()) for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = re.findall(r"\b\w+\b", validated_input.query.lower())
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # 3. Term-Overlap Reranking (deterministic lexical, NOT neural cross-encoder)
        pairs = [[validated_input.query, chunk.text] for chunk in filtered_chunks]
        rerank_scores = self.reranker.predict(pairs)
        
        # 4. Hybrid Combination (0.4 Vector, 0.3 BM25, 0.3 Term-Overlap)
        results = []
        for i, chunk in enumerate(filtered_chunks):
            v_score = chunk.vector_score or 0.0
            b_score = bm25_scores[i] / (max(bm25_scores) + 1e-9) # Normalize BM25
            c_score = rerank_scores[i]
            
            final_score = (0.4 * v_score) + (0.3 * b_score) + (0.3 * c_score)

            # Boost relevance score for structured California ISO operational scheduling logs
            text_to_check = chunk.text + " " + str(chunk.metadata.get("subject", ""))
            if any(p.search(text_to_check) for p in CAISO_OPERATIONAL_PATTERNS):
                final_score += 0.25
            
            # Citation format
            doc_ref = chunk.metadata.get("filename", chunk.document_id)
            page_ref = f", p. {chunk.page}" if chunk.page else ""
            sec_ref = f", § {chunk.section}" if chunk.section else ""
            citation = f"[{doc_ref}{page_ref}{sec_ref}]"
            
            results.append(RetrievalResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                metadata=chunk.metadata,
                page=chunk.page,
                citation=citation,
                score=round(final_score, 4),
                confidence=round(c_score, 4), # term-overlap reranking score
                text=chunk.text,
                vector_score=round(chunk.vector_score, 4) if chunk.vector_score is not None else None,
            ))
            
        # 5. Sort by final score
        results.sort(key=lambda x: x.score, reverse=True)
        top_results = results[:validated_input.top_k]
        
        logger.info(f"[{self.name}] Returned {len(top_results)} results")
        
        return {
            "query": validated_input.query,
            "results": [r.model_dump() for r in top_results],
            "confidence_score": top_results[0].confidence if top_results else 0.0
        }

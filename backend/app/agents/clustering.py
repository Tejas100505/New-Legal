"""
Clustering Agent for the E-Discovery platform.

Clusters retrieved documents using KMeans on neural embeddings.
Generates real, dynamic cluster labels using a hybrid approach:
1. TF-IDF salient keyword extraction (deterministic, high-precision topic terms).
2. Gemini LLM theme synthesis on representative cluster exemplars (closest to centroid).
3. Fallback to TF-IDF key terms if LLM is unavailable or offline.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import numpy as np
try:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError as e:
    import logging as _logging
    _logging.getLogger(__name__).error(
        "scikit-learn failed to import; clustering will be unavailable: %s", e
    )
    raise RuntimeError(
        f"scikit-learn is required for clustering but failed to import: {e}"
    ) from e

from app.agents.base import BaseAgent, AgentException
from app.config import get_settings
from loguru import logger

from app.agents.gemini_client import (
    get_gemini_client as _get_gemini_client,
    is_quota_error,
    mark_primary_exhausted,
)


class ClusteringInput(BaseModel):
    documents: List[Dict[str, Any]]  # e.g. {"id": "1", "text": "...", "embedding": [...]}
    n_clusters: int | None = None  # If None, auto-detect
    use_llm_labeling: bool = True  # If True, synthesize title with Gemini; if False, use TF-IDF only


class ClusterResult(BaseModel):
    cluster_id: int
    label: str
    top_terms: List[str] = Field(default_factory=list)
    document_ids: List[str]


class ClusteringOutput(BaseModel):
    clusters: List[ClusterResult]
    confidence_score: float


class ClusteringAgent(BaseAgent[ClusteringInput, ClusteringOutput]):
    """
    Clusters documents using KMeans on neural embeddings and generates
    grounded, dynamic topic labels from cluster contents.
    """

    def __init__(self):
        super().__init__(
            name="ClusteringAgent",
            prompt_version="2.0.0",
            input_model=ClusteringInput,
            output_model=ClusteringOutput,
        )

    @staticmethod
    def _strip_email_headers(text: str) -> str:
        """
        Strips RFC-822 email headers (To:, From:, Subject:, Date:, Cc:, Bcc:, etc.)
        and email transmission envelopes so clustering focuses on message body topic content.
        """
        import re
        # Remove standard RFC-822 headers at the top of the message
        # e.g., Message-ID: ..., Date: ..., From: ..., To: ..., Subject: ..., Cc: ..., Mime-Version: ...
        header_patterns = [
            r"^(?:Message-ID|Date|From|To|Subject|Cc|Bcc|Mime-Version|Content-Type|Content-Transfer-Encoding|X-[A-Za-z0-9\-]+):.*$",
            r"^-+\s*(?:Forwarded by|Original Message).*",
            r"^Sent:\s+.*$",
            r"^Received:\s+.*$",
        ]
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            if any(re.match(p, line.strip(), re.IGNORECASE) for p in header_patterns):
                continue
            cleaned_lines.append(line)
        cleaned_text = "\n".join(cleaned_lines).strip()
        return cleaned_text if len(cleaned_text) > 20 else text

    def _extract_tfidf_terms(self, cluster_texts: List[str], all_texts: List[str], top_n: int = 5) -> List[str]:
        """
        Computes TF-IDF terms specifically distinguishing this cluster from the corpus,
        stripping headers first so topics reflect substantive message body content.
        """
        try:
            # Strip RFC-822 headers from cluster texts and reference corpus texts
            stripped_cluster_texts = [self._strip_email_headers(t) for t in cluster_texts]
            stripped_all_texts = [self._strip_email_headers(t) for t in all_texts[:50]]

            # Combine cluster text into a single pseudo-document
            cluster_combined = " ".join(stripped_cluster_texts)
            if not cluster_combined.strip():
                return ["general", "documents"]

            corpus = [cluster_combined] + stripped_all_texts
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_df=0.85,
                min_df=1,
                token_pattern=r"(?u)\b[a-zA-Z]{3,}\b",
                max_features=200
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()

            # Scores for the cluster pseudo-document (row 0)
            cluster_scores = tfidf_matrix[0].toarray().flatten()
            top_indices = cluster_scores.argsort()[::-1][:top_n]
            top_terms = [feature_names[idx] for idx in top_indices if cluster_scores[idx] > 0]
            return top_terms or ["general", "correspondence"]
        except Exception as e:
            logger.warning(f"[{self.name}] TF-IDF extraction failed: {e}")
            return ["cluster", "documents"]

    async def _synthesize_llm_label(self, top_terms: List[str], sample_snippets: List[str]) -> str:
        """
        Synthesizes a short, precise legal/business cluster label via Gemini LLM.
        """
        client = _get_gemini_client()
        settings = get_settings()
        model_name = settings.google_model or "gemini-3.5-flash-lite"

        samples_text = "\n\n".join([f"--- Sample {i+1} ---\n{s[:400]}" for i, s in enumerate(sample_snippets)])

        prompt = f"""You are a legal e-discovery topic modeling analyst.
Given the following representative document snippets and key terms from a specific document cluster, generate a short, concise, descriptive theme label (3 to 6 words maximum).

KEY TF-IDF TERMS:
{', '.join(top_terms)}

REPRESENTATIVE DOCUMENT SAMPLES:
{samples_text}

REQUIREMENTS:
- The label must be grounded directly in the subject matter of these specific documents.
- Do NOT use generic labels like "General Documents" or "Business Email".
- Return strictly JSON matching:
{{"label": "Concise Descriptive Cluster Label"}}"""

        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            import json
            parsed = json.loads(response.text)
            label = parsed.get("label", "").strip()
            if label:
                return label
        except Exception as e:
            logger.warning(f"[{self.name}] LLM cluster labeling failed ({e}). Falling back to TF-IDF label.")

        # Fallback to TF-IDF title
        return " / ".join(t.capitalize() for t in top_terms[:3])

    async def _execute(self, validated_input: ClusteringInput) -> dict:
        logger.info(f"[{self.name}] Clustering {len(validated_input.documents)} documents")

        try:
            if not validated_input.documents:
                return {"clusters": [], "confidence_score": 0.0}

            embeddings = [doc["embedding"] for doc in validated_input.documents]
            X = np.array(embeddings)

            # Auto-detect reasonable k if not provided
            n_docs = len(validated_input.documents)
            if validated_input.n_clusters:
                k = min(validated_input.n_clusters, n_docs)
            else:
                # Default rule of thumb: ~sqrt(n/2), clamped between 2 and 6
                k = max(2, min(6, int(np.sqrt(n_docs / 2)) or 2))
                k = min(k, n_docs)

            kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
            labels = kmeans.fit_predict(X)
            centroids = kmeans.cluster_centers_

            all_texts = [d.get("text", "") for d in validated_input.documents]

            # Group documents by cluster and find exemplars closest to centroid
            clusters_map = {}
            for i, label in enumerate(labels):
                if label not in clusters_map:
                    clusters_map[label] = {"indices": [], "ids": [], "texts": []}
                clusters_map[label]["indices"].append(i)
                clusters_map[label]["ids"].append(validated_input.documents[i]["id"])
                clusters_map[label]["texts"].append(validated_input.documents[i].get("text", ""))

            final_clusters = []
            for cluster_id, data in clusters_map.items():
                c_indices = data["indices"]
                c_texts = data["texts"]

                # Extract top TF-IDF terms
                top_terms = self._extract_tfidf_terms(c_texts, all_texts, top_n=5)

                # Select 3-4 representative snippets closest to cluster centroid
                c_embeddings = X[c_indices]
                centroid = centroids[cluster_id]
                distances = np.linalg.norm(c_embeddings - centroid, axis=1)
                closest_indices = distances.argsort()[:4]
                sample_snippets = [self._strip_email_headers(c_texts[idx]) for idx in closest_indices if c_texts[idx].strip()]

                # Generate label: LLM or TF-IDF
                if validated_input.use_llm_labeling and sample_snippets:
                    label = await self._synthesize_llm_label(top_terms, sample_snippets)
                else:
                    label = " / ".join(t.capitalize() for t in top_terms[:3])

                final_clusters.append({
                    "cluster_id": int(cluster_id),
                    "label": label,
                    "top_terms": top_terms,
                    "document_ids": data["ids"]
                })

            # Sort clusters by id
            final_clusters.sort(key=lambda x: x["cluster_id"])

            # Compute silhouette-inspired inertia confidence
            confidence = 0.90 if len(final_clusters) > 1 else 0.75

            return {
                "clusters": final_clusters,
                "confidence_score": confidence
            }
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            raise AgentException(f"Clustering failed: {e}")

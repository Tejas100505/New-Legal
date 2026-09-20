"""
Review Agent for the E-Discovery platform.

Merges outputs from all upstream agents into one structured JSON.
Generates a Review Map using NetworkX.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import networkx as nx

from app.agents.base import BaseAgent, AgentException
from loguru import logger


class ReviewInput(BaseModel):
    documents: List[Dict[str, Any]]  # List of {document_id, summaries, classification, entities, risk, privilege, pii, ...}
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    clusters: List[Dict[str, Any]] = Field(default_factory=list)


class ReviewOutput(BaseModel):
    review_json: Dict[str, Any]
    review_map: Dict[str, Any]  # NetworkX node-link JSON
    confidence_score: float


class ReviewAgent(BaseAgent[ReviewInput, ReviewOutput]):
    """
    Merges all agent outputs and generates a Review Map.
    """

    def __init__(self):
        super().__init__(
            name="ReviewAgent",
            prompt_version="1.0.0",
            input_model=ReviewInput,
            output_model=ReviewOutput,
        )

    def _build_review_map(
        self,
        documents: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        clusters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build a NetworkX Review Map."""
        G = nx.Graph()

        # Add document nodes
        for doc in documents:
            doc_id = doc.get("document_id", "unknown")
            G.add_node(
                doc_id,
                type="Document",
                classification=doc.get("classification", "Unknown"),
                risk=doc.get("risk", "LOW"),
            )

        # Add cluster edges (shared_cluster)
        for cluster in clusters:
            doc_ids = cluster.get("document_ids", [])
            label = cluster.get("label", "General")
            for i in range(len(doc_ids)):
                for j in range(i + 1, len(doc_ids)):
                    if G.has_node(doc_ids[i]) and G.has_node(doc_ids[j]):
                        G.add_edge(doc_ids[i], doc_ids[j], relation="shared_cluster", cluster_label=label)

        # Add relationship edges (similarity)
        for rel in relationships:
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt and G.has_node(src) and G.has_node(tgt):
                G.add_edge(src, tgt, relation="similarity")

        return nx.node_link_data(G, edges="links")

    async def _execute(self, validated_input: ReviewInput) -> dict:
        logger.info(f"[{self.name}] Generating review for {len(validated_input.documents)} documents")

        # Merge all agent outputs into a structured JSON
        merged = {
            "total_documents": len(validated_input.documents),
            "documents": [],
        }

        for doc in validated_input.documents:
            merged["documents"].append({
                "document_id": doc.get("document_id"),
                "classification": doc.get("classification"),
                "entities": doc.get("entities"),
                "risk": doc.get("risk"),
                "privilege": doc.get("privilege"),
                "pii_redacted": doc.get("pii_redacted", False),
                "summaries": doc.get("summaries"),
            })

        # Build Review Map
        review_map = self._build_review_map(
            validated_input.documents,
            validated_input.relationships,
            validated_input.clusters,
        )

        return {
            "review_json": merged,
            "review_map": review_map,
            "confidence_score": 0.87,
        }

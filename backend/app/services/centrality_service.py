import math
import re
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict

# Regex for standard email-address-pattern entities
EMAIL_PATTERN_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Derived normalization cap C:
# Derived via scratch/derive_cap_c.py on the real 424-document dataset (27,937 entity edges):
#   p99 of connected strength (excluding 322 flagged email-org nodes, N=2,677) = 8.8218
#   C = ceil(p99_connected_excluding_flagged) = ceil(8.8218) = 9.0
CENTRALITY_CAP_DEFAULT: float = 9.0

# Base importance floor for zero-strength / isolate nodes
IMPORTANCE_FLOOR: float = 0.05
IMPORTANCE_SCALE: float = 0.95


class CentralityService:
    """
    Computes weighted degree (node strength) centrality for knowledge graph entities
    using real Step-2 calibrated edge weights and normalizes into [0.05, 1.0].
    """

    def __init__(self, cap: float = CENTRALITY_CAP_DEFAULT):
        self.cap = float(cap)
        self.email_regex = EMAIL_PATTERN_REGEX

    def is_email_pattern_entity(self, label: str) -> bool:
        """Checks if the entity string matches a standard email address."""
        if not label:
            return False
        return bool(self.email_regex.match(label.strip()))

    def is_single_token_organization(self, label: str, node_type: str) -> bool:
        """
        Generically detects single-token organization fragments across the corpus,
        mirroring the structural pattern in is_single_token_person():
        (single whitespace-delimited token, no '@' character, typed as organization).
        E.g., 'Arlena', 'Deanna', 'Kaake', 'Osborn', 'Martin', 'Scott', 'FYI'.
        """
        norm_type = (node_type or "").strip().lower()
        if norm_type not in ("organization", "org"):
            return False
        if not label:
            return False
        if "@" in label:
            return False
        tokens = label.strip().split()
        return len(tokens) < 2

    def flag_likely_misclassified(self, label: str, node_type: str) -> bool:
        """
        Detects entities requiring the likely_misclassified flag:
        1. Email-address pattern entities typed as organizations.
        2. Generic single-token organization fragments (no space, no '@').
        """
        norm_type = (node_type or "").strip().lower()
        if norm_type in ("organization", "org"):
            if self.is_email_pattern_entity(label):
                return True
            if self.is_single_token_organization(label, node_type):
                return True
        return False

    def compute_node_strengths(
        self,
        entity_nodes: List[Dict[str, Any]],
        inter_entity_edges: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Computes weighted degree (node strength) per entity node:
        strength(v) = sum(weight of all incident entity-entity edges incident to v).
        Uses deterministic summation over the live, suppressed edge set.
        """
        strengths: Dict[str, float] = {n["id"]: 0.0 for n in entity_nodes}

        for edge in inter_entity_edges:
            src = edge["source"]
            tgt = edge["target"]
            # Step-2 real edge weight
            w = float(edge.get("weight", 0.0))

            if src in strengths:
                strengths[src] += w
            if tgt in strengths:
                strengths[tgt] += w

        return {nid: round(s, 6) for nid, s in strengths.items()}

    def normalize_strength(self, strength: float, cap: Optional[float] = None) -> float:
        """
        Normalizes node strength into [0.05, 1.0] using logarithmic compression:
          importance = 0.05 + 0.95 * ln(1 + min(strength, C)) / ln(1 + C)
        Nodes with strength 0.0 receive exactly 0.05.
        Deterministic and monotonic.
        """
        c = float(cap if cap is not None else self.cap)
        if c <= 0:
            c = 1.0

        clamped_strength = max(0.0, min(float(strength), c))
        # ln(1 + 0) = 0 -> importance = 0.05 + 0.0 = 0.05
        norm_val = math.log(1.0 + clamped_strength) / math.log(1.0 + c)
        importance = IMPORTANCE_FLOOR + IMPORTANCE_SCALE * norm_val
        bounded = max(0.05, min(1.0, importance))
        return round(bounded, 4)

    def apply_centrality_to_nodes(
        self,
        nodes: List[Dict[str, Any]],
        inter_entity_edges: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Applies weighted degree centrality to entity nodes in-place/returned:
        - Document nodes (type == 'document') are preserved with their existing importance.
        - Entity nodes receive real normalized importance based on incident edge weights.
        - Nodes matching email-org pattern receive metadata['likely_misclassified'] = 'true'.
        """
        entity_nodes = [n for n in nodes if n.get("type") != "document"]
        strengths = self.compute_node_strengths(entity_nodes, inter_entity_edges)

        for n in nodes:
            if n.get("type") == "document":
                # DO NOT TOUCH document node importance
                continue

            nid = n["id"]
            lbl = n.get("label", "")
            ntype = n.get("type", "")
            s = strengths.get(nid, 0.0)

            # Assign normalized importance
            n["importance"] = self.normalize_strength(s)

            # Metadata enrichment
            if "metadata" not in n or not isinstance(n["metadata"], dict):
                n["metadata"] = {}

            n["metadata"]["weighted_degree"] = f"{s:.4f}"

            # Part A.1.c: Check email-address pattern in organization
            if self.flag_likely_misclassified(lbl, ntype):
                n["metadata"]["likely_misclassified"] = "true"

        return nodes

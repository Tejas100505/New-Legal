import math
import re
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict, Counter

# Calibration ceiling for multi-document relationship breadth
D_CAP_DEFAULT: int = 10

# Scaling parameter for logarithmic breadth curve
BREADTH_K: float = 1.5

# Relationship type multipliers
RELATION_MULTIPLIERS: Dict[str, float] = {
    "communication": 1.0,
    "relationship": 1.0,
    "relates_to": 0.95,
    "mentions": 0.85,
    "association": 0.90,
}

# Tier 1: Pattern-based regex for protocol, header, timezone, and routing delimiters
HEADER_ARTIFACT_REGEX = re.compile(
    r"^content[-_](type|transfer[-_]encoding|disposition|length|description)"
    r"|^mime[-_]version"
    r"|^x[-_](origin|filename|to|from|cc|bcc|folder|tier|routing)"
    r"|.*x-filename.*"
    r"|^notesaddr"
    r"|^na$"
    r"|^ou=.*|^cn=.*"
    r"|.*[\\/].*(desk|folder|archive|inbox|sent)"
    r"|^(pst|pdt|cst|cdt|est|edt|gmt|utc)$",
    re.IGNORECASE | re.DOTALL
)

# Tier 2: Static blocklist of known artifact tokens
KNOWN_ARTIFACT_STRINGS: Set[str] = {
    "na", "pst", "pdt", "cst", "cdt", "gmt", "utc", "ou",
    "dutch\\fin desk", "content-type", "content-transfer-encoding",
    "mime-version", "notesaddr", "x-origin", "x-filename",
    "lblair", "mheard", "skean", "x-118"
}


def is_header_or_protocol_artifact(name: str) -> bool:
    """Detects whether an entity string represents an email header, protocol delimiter, or timezone."""
    norm = name.strip().lower()
    if not norm or norm in KNOWN_ARTIFACT_STRINGS:
        return True
    return bool(HEADER_ARTIFACT_REGEX.search(norm))


def is_single_token_person(name: str, category: str) -> bool:
    """
    Generically detects unresolvable single-token person fragments across the corpus.
    E.g., 'Steven', 'Lynn', 'John', 'Marie', 'Bill', 'Chris'.
    Legitimate email addresses containing '@' are preserved.
    """
    if category != "person":
        return False
    if "@" in name:
        return False
    tokens = name.strip().split()
    return len(tokens) < 2


def should_suppress_node(name: str, category: str) -> bool:
    """
    Suppresses an entity node if it is a protocol/header artifact
    or an unresolvable single-token person fragment.
    """
    if is_header_or_protocol_artifact(name):
        return True
    if is_single_token_person(name, category):
        return True
    return False


def should_suppress_edge(source_name: str, source_cat: str, target_name: str, target_cat: str) -> bool:
    """
    Policy 2: Suppresses edges where either endpoint is an email header/protocol delimiter
    or an unresolvable single-token person fragment.
    """
    if should_suppress_node(source_name, source_cat) or should_suppress_node(target_name, target_cat):
        return True
    return False


class EdgeWeightingService:
    """
    Calibrates, weights, and attaches evidence metadata to knowledge graph relationships.
    Uses multi-document breadth saturation (D_cap = 10) with additive interaction depth boost.
    """

    def __init__(self, d_cap: int = D_CAP_DEFAULT, k: float = BREADTH_K) -> None:
        self.d_cap = d_cap
        self.k = k
        self._log_d_cap = math.log(1.0 + self.k * (self.d_cap - 1.0))

    def compute_breadth_score(self, d: int) -> float:
        """
        Computes logarithmic breadth saturation score S_breadth(D).
        S_breadth(1) = 0.0, S_breadth(>= D_cap) = 1.0.
        """
        if d <= 1:
            return 0.0
        capped_d = min(d, self.d_cap)
        num = math.log(1.0 + self.k * (capped_d - 1.0))
        return min(1.0, max(0.0, num / self._log_d_cap))

    def compute_depth_boost(self, f: int, d: int) -> float:
        """
        Computes additive interaction depth boost:
        DepthBoost(u, v) = min(0.10, 0.02 * max(0, F - D))
        """
        excess = max(0, f - d)
        return min(0.10, 0.02 * excess)

    def compute_inter_entity_weight(
        self,
        d: int,
        f: int,
        relation_type: str = "communication"
    ) -> float:
        """
        Calculates calibrated edge weight for an inter-entity tie:
        Weight = round(max(0.05, min(1.0, [0.05 + 0.95 * S_breadth + DepthBoost] * M_rel)), 4)
        """
        s_breadth = self.compute_breadth_score(d)
        depth_boost = self.compute_depth_boost(f, d)
        m_rel = RELATION_MULTIPLIERS.get(relation_type.lower(), 0.90)

        raw_weight = (0.05 + 0.95 * s_breadth + depth_boost) * m_rel
        bounded = max(0.05, min(1.0, raw_weight))
        return round(bounded, 4)

    def compute_document_mention_weight(self, term_frequency: int) -> float:
        """
        Harmonized containment scale for document-to-entity MENTIONS_* edges:
        Weight(d, e) = round(0.15 + 0.60 * (tf - 1) / 3, 4) bounded to [0.15, 0.75].
        """
        capped_tf = max(1, min(4, term_frequency))
        w = 0.15 + 0.60 * (capped_tf - 1.0) / 3.0
        return round(w, 4)

    def generate_weight_rationale(
        self,
        d: int,
        f: int,
        weight: float,
        relation_type: str
    ) -> str:
        """Constructs an auditable explanation string for the derived weight."""
        s_breadth = self.compute_breadth_score(d)
        depth_boost = self.compute_depth_boost(f, d)
        return (
            f"Weight {weight:.4f} derived from {f} {relation_type} events across "
            f"{d} shared documents (breadth={s_breadth:.4f}, depth_boost={depth_boost:.4f}, D_cap={self.d_cap})"
        )

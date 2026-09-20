import pytest
import math
from app.services.centrality_service import (
    CentralityService,
    CENTRALITY_CAP_DEFAULT,
    EMAIL_PATTERN_REGEX
)

def test_centrality_cap_and_email_regex():
    service = CentralityService(cap=9.0)
    assert service.cap == 9.0
    assert service.is_email_pattern_entity("jeff.king@enron.com") is True
    assert service.is_email_pattern_entity("john.forney@enron.com") is True
    assert service.is_email_pattern_entity("Kenneth Lay") is False
    assert service.is_email_pattern_entity("ENRON") is False
    assert service.is_email_pattern_entity("ECT") is False

def test_flag_likely_misclassified():
    service = CentralityService(cap=9.0)
    # 1. An email string typed as organization must be flagged
    assert service.flag_likely_misclassified("jeff.king@enron.com", "organization") is True
    assert service.flag_likely_misclassified("jeff.king@enron.com", "org") is True
    # An email string typed as person must NOT be flagged
    assert service.flag_likely_misclassified("jeff.king@enron.com", "person") is False

    # 2. Generic single-token organizations must be flagged structurally (no hardcoded lists)
    assert service.is_single_token_organization("Arlena", "organization") is True
    assert service.is_single_token_organization("Deanna", "organization") is True
    assert service.is_single_token_organization("Kaake", "org") is True
    assert service.is_single_token_organization("Osborn", "organization") is True
    assert service.is_single_token_organization("Martin", "organization") is True
    assert service.is_single_token_organization("FYI", "organization") is True
    assert service.flag_likely_misclassified("Arlena", "organization") is True
    assert service.flag_likely_misclassified("Kaake", "organization") is True

    # 3. Multi-word organizations must NOT be flagged as single-token
    assert service.is_single_token_organization("Enron North America", "organization") is False
    assert service.is_single_token_organization("Smith L Day", "organization") is False
    assert service.is_single_token_organization("Fletcher J Sturm", "organization") is False
    assert service.flag_likely_misclassified("Enron North America", "organization") is False

    # 4. Multi-word or single-token person entities must NOT be flagged under organization rule
    assert service.is_single_token_organization("Kenneth Lay", "person") is False
    assert service.is_single_token_organization("Steven", "person") is False
    assert service.flag_likely_misclassified("Kenneth Lay", "person") is False

def test_weighted_degree_computation():
    service = CentralityService(cap=9.0)
    nodes = [
        {"id": "node_A", "type": "person", "label": "Alice"},
        {"id": "node_B", "type": "organization", "label": "Corp"},
        {"id": "node_C", "type": "person", "label": "Bob"},
        {"id": "node_D", "type": "person", "label": "Isolate"},
    ]
    edges = [
        {"source": "node_A", "target": "node_B", "weight": 0.8},
        {"source": "node_A", "target": "node_C", "weight": 0.5},
        {"source": "node_B", "target": "node_C", "weight": 0.2},
    ]

    strengths = service.compute_node_strengths(nodes, edges)
    # Alice (A): 0.8 + 0.5 = 1.3
    assert abs(strengths["node_A"] - 1.3) < 1e-5
    # Corp (B): 0.8 + 0.2 = 1.0
    assert abs(strengths["node_B"] - 1.0) < 1e-5
    # Bob (C): 0.5 + 0.2 = 0.7
    assert abs(strengths["node_C"] - 0.7) < 1e-5
    # Isolate (D): 0.0
    assert strengths["node_D"] == 0.0

def test_normalization_formula_milestones():
    service = CentralityService(cap=9.0)
    # Strength = 0.0 -> must be exactly 0.05
    assert service.normalize_strength(0.0) == 0.05

    # Strength = C (9.0) -> must be exactly 1.0
    assert service.normalize_strength(9.0) == 1.0

    # Strength > C (e.g. 50.0, 107.4) -> must be clamped to exactly 1.0
    assert service.normalize_strength(50.0) == 1.0
    assert service.normalize_strength(107.4154) == 1.0

    # Monotonicity test: strictly increasing up to cap C
    strengths = [0.0, 0.5, 1.0, 3.0, 6.0, 9.0]
    importances = [service.normalize_strength(s) for s in strengths]
    for i in range(len(importances) - 1):
        assert importances[i] < importances[i + 1]

def test_normalization_bounds_and_determinism():
    service = CentralityService(cap=9.0)
    # Test across large array of values
    for s in [-5.0, 0.0, 0.001, 0.5, 1.38, 7.0377, 9.0, 15.0, 1000.0]:
        val1 = service.normalize_strength(s)
        val2 = service.normalize_strength(s)
        assert val1 == val2  # Determinism
        assert 0.05 <= val1 <= 1.0  # Bounds

def test_apply_centrality_to_nodes():
    service = CentralityService(cap=9.0)
    nodes = [
        {"id": "doc_1", "type": "document", "label": "doc1.txt", "importance": 0.9, "metadata": {}},
        {"id": "ent_1", "type": "person", "label": "Kenneth Lay", "importance": 0.75, "metadata": {}},
        {"id": "ent_2", "type": "organization", "label": "ENRON", "importance": 0.75, "metadata": {}},
        {"id": "ent_3", "type": "organization", "label": "jeff.king@enron.com", "importance": 0.75, "metadata": {}},
        {"id": "ent_4", "type": "person", "label": "Zero Degree", "importance": 0.75, "metadata": {}},
        {"id": "ent_5", "type": "organization", "label": "Kaake", "importance": 0.75, "metadata": {}},
    ]
    edges = [
        {"source": "ent_1", "target": "ent_2", "weight": 0.9812},
        {"source": "ent_2", "target": "ent_3", "weight": 0.8500},
        {"source": "ent_2", "target": "ent_5", "weight": 0.5000},
    ]

    result = service.apply_centrality_to_nodes(nodes, edges)
    res_map = {n["id"]: n for n in result}

    # Document node importance must remain exactly 0.9
    assert res_map["doc_1"]["importance"] == 0.9
    assert "likely_misclassified" not in res_map["doc_1"]["metadata"]

    # Zero-degree entity receives exactly 0.05
    assert res_map["ent_4"]["importance"] == 0.05
    assert res_map["ent_4"]["metadata"]["weighted_degree"] == "0.0000"

    # Flagged nodes receive metadata flag (both email pattern and single-token org)
    assert res_map["ent_3"]["metadata"]["likely_misclassified"] == "true"
    assert res_map["ent_5"]["metadata"]["likely_misclassified"] == "true"

    # ENRON has strength 0.9812 + 0.8500 = 1.8312
    assert float(res_map["ent_2"]["metadata"]["weighted_degree"]) > float(res_map["ent_1"]["metadata"]["weighted_degree"])
    assert res_map["ent_2"]["importance"] > res_map["ent_1"]["importance"]

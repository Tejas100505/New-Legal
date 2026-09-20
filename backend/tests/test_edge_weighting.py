import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.services.edge_weighting import (
    EdgeWeightingService,
    is_header_or_protocol_artifact,
    is_single_token_person,
    should_suppress_edge,
    D_CAP_DEFAULT,
)


def test_d_cap_default():
    service = EdgeWeightingService()
    assert service.d_cap == 10
    assert service.k == 1.5


def test_breadth_score_milestones():
    service = EdgeWeightingService()
    # D <= 1 is exactly 0.0
    assert service.compute_breadth_score(0) == 0.0
    assert service.compute_breadth_score(1) == 0.0

    # D = 2: ln(2.5)/ln(14.5) ~ 0.3426
    assert pytest.approx(service.compute_breadth_score(2), abs=1e-4) == 0.3426

    # D = 3: ln(4.0)/ln(14.5) ~ 0.5184
    assert pytest.approx(service.compute_breadth_score(3), abs=1e-4) == 0.5184

    # D = 4: ln(5.5)/ln(14.5) ~ 0.6375
    assert pytest.approx(service.compute_breadth_score(4), abs=1e-4) == 0.6375

    # D = 9: ln(13.0)/ln(14.5) ~ 0.9592
    assert pytest.approx(service.compute_breadth_score(9), abs=1e-4) == 0.9592

    # D >= 10: 1.0 (capped saturation)
    assert service.compute_breadth_score(10) == 1.0
    assert service.compute_breadth_score(15) == 1.0
    assert service.compute_breadth_score(25) == 1.0


def test_depth_boost():
    service = EdgeWeightingService()
    # F <= D -> boost is 0
    assert service.compute_depth_boost(5, 5) == 0.0
    assert service.compute_depth_boost(4, 5) == 0.0

    # F > D -> 0.02 per excess event
    assert pytest.approx(service.compute_depth_boost(6, 5), abs=1e-4) == 0.02
    assert pytest.approx(service.compute_depth_boost(7, 5), abs=1e-4) == 0.04
    assert pytest.approx(service.compute_depth_boost(8, 5), abs=1e-4) == 0.06

    # Depth boost caps at 0.10
    assert service.compute_depth_boost(20, 5) == 0.10


def test_exact_edge_weight_milestones():
    service = EdgeWeightingService()

    # Incidental Pair (D=1, F=1) -> 0.0500 floor
    assert service.compute_inter_entity_weight(1, 1, "communication") == 0.0500

    # Emerging Tie (D=2, F=2) -> 0.3755
    assert service.compute_inter_entity_weight(2, 2, "communication") == 0.3755

    # Emerging Tie with Depth (D=2, F=3) -> 0.3955
    assert service.compute_inter_entity_weight(2, 3, "communication") == 0.3955

    # Regular Association (D=3, F=3) -> 0.5425
    assert service.compute_inter_entity_weight(3, 3, "communication") == 0.5425

    # Strong Association (D=4, F=4) -> 0.6556
    assert service.compute_inter_entity_weight(4, 4, "communication") == 0.6556

    # Major Corporate Tie (D=5, F=6) -> 0.7613
    assert service.compute_inter_entity_weight(5, 6, "communication") == 0.7613

    # Key Executive Connection (D=6, F=7) -> 0.8303
    assert service.compute_inter_entity_weight(6, 7, "communication") == 0.8303

    # Kenneth Lay Top Org Partner (ENRON: D=9, F=10) -> 0.9812
    assert service.compute_inter_entity_weight(9, 10, "communication") == 0.9812

    # Top Corporate Hub (ECT <-> Scott Neal: D=10, F=11) -> 1.0000
    assert service.compute_inter_entity_weight(10, 11, "communication") == 1.0000


def test_document_mention_weights():
    service = EdgeWeightingService()
    # tf = 1 -> 0.1500
    assert service.compute_document_mention_weight(1) == 0.1500
    # tf = 2 -> 0.3500
    assert service.compute_document_mention_weight(2) == 0.3500
    # tf = 3 -> 0.5500
    assert service.compute_document_mention_weight(3) == 0.5500
    # tf >= 4 -> 0.7500
    assert service.compute_document_mention_weight(4) == 0.7500
    assert service.compute_document_mention_weight(10) == 0.7500


def test_policy_2_artifact_suppression():
    # MIME/Header tokens
    assert is_header_or_protocol_artifact("Content-Type")
    assert is_header_or_protocol_artifact("Content-Transfer-Encoding")
    assert is_header_or_protocol_artifact("PST")
    assert is_header_or_protocol_artifact("NA")
    assert is_header_or_protocol_artifact("Dutch\\Fin Desk")
    assert is_header_or_protocol_artifact("Notesaddr")
    assert is_header_or_protocol_artifact("X-Origin")
    assert is_header_or_protocol_artifact("Guzman-M\n\nX-FileName")

    # Legitimate entities must NOT be flagged as header artifacts
    assert not is_header_or_protocol_artifact("Kenneth Lay")
    assert not is_header_or_protocol_artifact("Scott Neal")
    assert not is_header_or_protocol_artifact("ENRON")
    assert not is_header_or_protocol_artifact("ECT")


def test_policy_2_single_token_person_suppression():
    # Bare first names under category 'person'
    assert is_single_token_person("Steven", "person")
    assert is_single_token_person("Lynn", "person")
    assert is_single_token_person("John", "person")
    assert is_single_token_person("Marie", "person")
    assert is_single_token_person("Steve", "person")

    # Full multi-word names must NOT be suppressed
    assert not is_single_token_person("Steven Harris", "person")
    assert not is_single_token_person("Lynn Blair", "person")
    assert not is_single_token_person("Kenneth Lay", "person")

    # Valid email addresses must NOT be suppressed
    assert not is_single_token_person("dan.leff@enron.com", "person")
    assert not is_single_token_person("geir.solberg@enron.com", "person")

    # Single-token organizations must NOT be suppressed (e.g. 'ECT', 'FERC')
    assert not is_single_token_person("ECT", "organization")
    assert not is_single_token_person("FERC", "organization")
    assert not is_single_token_person("ENRON", "organization")


def test_should_suppress_edge():
    # Header artifact endpoint -> suppressed
    assert should_suppress_edge("Content-Type", "organization", "John", "person")
    assert should_suppress_edge("ENRON", "organization", "PST", "organization")

    # Single token person endpoint -> suppressed
    assert should_suppress_edge("ENRON", "organization", "Steven", "person")
    assert should_suppress_edge("ENRON", "organization", "Steve", "person")

    # Genuine fully named connections -> NOT suppressed
    assert not should_suppress_edge("ENRON", "organization", "Kenneth Lay", "person")
    assert not should_suppress_edge("ECT", "organization", "Scott Neal", "person")
    assert not should_suppress_edge("Fletcher J Sturm", "person", "Robert Benson", "person")


def test_weight_rationale():
    service = EdgeWeightingService()
    rationale = service.generate_weight_rationale(9, 10, 0.9812, "communication")
    assert "0.9812" in rationale
    assert "10 communication events" in rationale
    assert "9 shared documents" in rationale
    assert "D_cap=10" in rationale

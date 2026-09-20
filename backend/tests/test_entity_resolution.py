import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from collections import Counter
from app.services.entity_resolution import (
    EntityResolutionService,
    clean_person_string,
    parse_person_name,
    are_first_names_compatible,
    are_middle_names_compatible,
    is_known_mock_entity,
    NICKNAMES,
)


def test_nickname_table_validity():
    """Ensure all nicknames map to valid non-empty formal names without self-loops or bad types."""
    assert len(NICKNAMES) >= 40
    for nick, formal in NICKNAMES.items():
        assert isinstance(nick, str) and len(nick) > 0
        assert isinstance(formal, str) and len(formal) > 0
        assert nick != formal
        assert nick.islower()
        assert formal.islower()


def test_clean_person_string():
    """Verify stripping of email routing, MIME artifacts, possessives, and formatting."""
    assert clean_person_string("Kevin M Presto/HOU/ECT@ECT") == "Kevin M Presto"
    assert clean_person_string("Tim Belden@ECT") == "Tim Belden"
    assert clean_person_string("Vince Kaminski=20") == "Vince Kaminski"
    assert clean_person_string("Sara Shackleton's") == "Sara Shackleton"
    assert clean_person_string("James D Steffes/NA/Enron@Enron") == "James D Steffes"
    assert clean_person_string("<John.Arnold@enron.com>") == ""


def test_parse_person_name():
    """Verify structural name parsing including honorifics, suffixes, and 'Last, First'."""
    p1 = parse_person_name("Kenneth Lay")
    assert p1["first"] == "kenneth"
    assert p1["last"] == "lay"
    assert not p1["is_single"]

    p2 = parse_person_name("Chairman Lay")
    assert p2["last"] == "lay"
    assert p2["is_single"]

    p3 = parse_person_name("Sanders, Richard B.")
    assert p3["first"] == "richard"
    assert p3["middle"] == "b."
    assert p3["last"] == "sanders"

    p4 = parse_person_name("John Doe Jr.")
    assert p4["first"] == "john"
    assert p4["last"] == "doe"
    assert p4["suffix"] == "jr"


def test_are_first_names_compatible():
    """Verify nickname matching, initials, and incompatible first names."""
    assert are_first_names_compatible("ken", "kenneth")
    assert are_first_names_compatible("kenneth", "ken")
    assert are_first_names_compatible("jim", "james")
    assert are_first_names_compatible("k", "kenneth")
    assert are_first_names_compatible("kenneth", "k.")
    assert not are_first_names_compatible("kenneth", "clayton")
    assert not are_first_names_compatible("tom", "tim")
    # Substring prefix matches between multi-char tokens must be rejected
    assert not are_first_names_compatible("kim", "kimat")
    assert not are_first_names_compatible("al", "alma")



def test_are_middle_names_compatible():
    """Verify middle initial compatibility and conflict prevention."""
    assert are_middle_names_compatible("", "b.")
    assert are_middle_names_compatible("b.", "")
    assert are_middle_names_compatible("b.", "b.")
    # Conflicting middle initials must NOT be compatible
    assert not are_middle_names_compatible("a.", "b.")
    assert not are_middle_names_compatible("alan", "b.")


def test_kenneth_lay_canonical_merge():
    """Real example: Kenneth Lay and Ken Lay merge into Kenneth Lay."""
    resolver = EntityResolutionService()
    mentions = {
        "people": Counter({
            "Kenneth Lay": 6,
            "Ken Lay": 12,
            "Ken Lay/HOU/ECT@ECT": 1,
        })
    }
    resolver.cluster_entities(mentions)

    id1, name1, _ = resolver.resolve("Kenneth Lay", "person")
    id2, name2, _ = resolver.resolve("Ken Lay", "person")
    id3, name3, _ = resolver.resolve("Ken Lay/HOU/ECT@ECT", "person")

    # All must map to same canonical ID
    assert id1 == id2 == id3
    # Display name must prefer complete formal form "Kenneth Lay"
    assert name1 == name2 == name3 == "Kenneth Lay"


def test_middle_initial_conflict_separation():
    """Confirm two people with same first+last but different middle initials are NOT merged."""
    resolver = EntityResolutionService()
    mentions = {
        "people": Counter({
            "Richard A. Sanders": 5,
            "Richard B. Sanders": 5,
        })
    }
    resolver.cluster_entities(mentions)

    id_a, _, _ = resolver.resolve("Richard A. Sanders", "person")
    id_b, _, _ = resolver.resolve("Richard B. Sanders", "person")

    assert id_a != id_b, "Entities with conflicting middle initials must NOT be merged!"


def test_generational_suffix_separation():
    """Confirm Jr. and Sr. are NOT merged."""
    resolver = EntityResolutionService()
    mentions = {
        "people": Counter({
            "John Doe Jr.": 3,
            "John Doe Sr.": 3,
        })
    }
    resolver.cluster_entities(mentions)

    id_jr, _, _ = resolver.resolve("John Doe Jr.", "person")
    id_sr, _, _ = resolver.resolve("John Doe Sr.", "person")

    assert id_jr != id_sr, "Jr. and Sr. must never be merged into the same person!"


def test_single_token_ambiguity_flagged():
    """Confirm single-token last names are flagged as ambiguous and not falsely merged."""
    resolver = EntityResolutionService()
    mentions = {
        "people": Counter({
            "Tom Alonso": 5,
            "Alonso": 2,
        })
    }
    resolver.cluster_entities(mentions)

    id_full, _, _ = resolver.resolve("Tom Alonso", "person")
    id_single, _, _ = resolver.resolve("Alonso", "person")

    # Kept separate to prevent false merge
    assert id_full != id_single
    flagged = resolver.get_flagged_ambiguous()
    assert any("Alonso" in f["item"] for f in flagged)


def test_initial_collision_ambiguity():
    """Confirm that if multiple distinct first names share an initial under a last name, initial is flagged."""
    resolver = EntityResolutionService()
    mentions = {
        "people": Counter({
            "Kenneth Lay": 5,
            "Kevin Lay": 5,
            "K. Lay": 2,
        })
    }
    resolver.cluster_entities(mentions)

    id_k_lay, _, _ = resolver.resolve("K. Lay", "person")
    id_ken, _, _ = resolver.resolve("Kenneth Lay", "person")
    id_kev, _, _ = resolver.resolve("Kevin Lay", "person")

    # K. Lay must not be merged into either because it is ambiguous!
    assert id_k_lay != id_ken
    assert id_k_lay != id_kev
    flagged = resolver.get_flagged_ambiguous()
    assert any("K. Lay" in f["item"] for f in flagged)


def test_type_scoped_clustering_isolation():
    """Confirm that person, organization, and location entities are 100% isolated (zero cross-type merge)."""
    resolver = EntityResolutionService()
    mentions = {
        "people": Counter({"Washington": 3}),
        "organizations": Counter({"Washington": 3}),
        "locations": Counter({"Washington": 3}),
    }
    resolver.cluster_entities(mentions)

    p_id, p_name, p_type = resolver.resolve("Washington", "person")
    o_id, o_name, o_type = resolver.resolve("Washington", "organization")
    l_id, l_name, l_type = resolver.resolve("Washington", "location")

    assert p_id != o_id
    assert p_id != l_id
    assert o_id != l_id
    assert p_type == "person"
    assert o_type == "organization"
    assert l_type == "location"


def test_mock_filter():
    """Verify known mock OCR entities are flagged and filtered."""
    assert is_known_mock_entity("Meridian Corp")
    assert is_known_mock_entity("Dr. James Whitfield")
    assert not is_known_mock_entity("Kenneth Lay")

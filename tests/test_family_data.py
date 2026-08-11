"""Contrato público del conjunto familiar completamente ficticio."""

from identity.family_data import FAMILY_ANIMALS, FAMILY_PEOPLE, FAMILY_RELATIONSHIPS
from identity.relationship import RELATIONSHIP_TYPES


def test_example_entities_are_small_unique_and_fictitious():
    names = [item["name"] for item in FAMILY_PEOPLE + FAMILY_ANIMALS]
    assert 2 <= len(FAMILY_PEOPLE) <= 8
    assert 1 <= len(FAMILY_ANIMALS) <= 4
    assert len(names) == len(set(names))
    assert all("fictici" in item["summary"].casefold() for item in FAMILY_PEOPLE)


def test_example_relationships_reference_existing_entities():
    names = {item["name"] for item in FAMILY_PEOPLE + FAMILY_ANIMALS}
    for relationship in FAMILY_RELATIONSHIPS:
        assert relationship["source"] in names
        assert relationship["target"] in names
        assert relationship["relationship_type"] in RELATIONSHIP_TYPES
        assert relationship["source_type"] in {"person", "animal"}
        assert relationship["target_type"] in {"person", "animal"}


def test_example_data_contains_no_runtime_paths_or_contacts():
    serialized = repr((FAMILY_PEOPLE, FAMILY_ANIMALS, FAMILY_RELATIONSHIPS)).casefold()
    assert "@" not in serialized
    assert "c:\\users\\" not in serialized
    assert "h:\\" not in serialized

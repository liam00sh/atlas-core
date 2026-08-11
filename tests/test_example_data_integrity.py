"""Integridad de los JSON sintéticos usados por la suite pública."""

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "examples" / "private_runtime" / "identity"


def _load(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def test_example_entity_and_relationship_ids_are_unique():
    people = _load("people.json")
    animals = _load("animals.json")
    relationships = _load("relationships.json")
    entity_ids = [item["id"] for item in people + animals]
    relationship_ids = [item["id"] for item in relationships]
    assert len(entity_ids) == len(set(entity_ids))
    assert len(relationship_ids) == len(set(relationship_ids))


def test_every_example_relationship_endpoint_exists():
    people = _load("people.json")
    animals = _load("animals.json")
    relationships = _load("relationships.json")
    entity_ids = {item["id"] for item in people + animals}
    for relationship in relationships:
        assert relationship["source_entity_id"] in entity_ids
        assert relationship["target_entity_id"] in entity_ids


def test_example_records_are_explicitly_synthetic():
    people = _load("people.json")
    assert all("fictici" in item.get("summary", "").casefold() for item in people)

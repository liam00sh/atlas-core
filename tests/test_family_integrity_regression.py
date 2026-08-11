import json
from pathlib import Path


def test_required_people_exist():
    data = json.loads(
        Path("examples/private_runtime/identity/people.json").read_text(encoding="utf-8")
    )
    names = {item["name"] for item in data}
    assert "Alex Romero" in names
    assert "Carla Romero" in names
    assert "Vega Ferrer" in names


def test_Carla_is_mother_of_Alex():
    people = json.loads(
        Path("examples/private_runtime/identity/people.json").read_text(encoding="utf-8")
    )
    relationships = json.loads(
        Path("examples/private_runtime/identity/relationships.json").read_text(encoding="utf-8")
    )
    ids = {item["name"]: item["id"] for item in people}

    matching = [
        item
        for item in relationships
        if item["source_entity_id"] == ids["Carla Romero"]
        and item["target_entity_id"] == ids["Alex Romero"]
    ]
    assert "mother" in {
        item["relationship_type"]
        for item in matching
    }

import json
from pathlib import Path


def test_required_people_exist():
    data = json.loads(
        Path("identity/data/people.json").read_text(encoding="utf-8")
    )
    names = {item["name"] for item in data}
    assert "REDACTED_7e476572dd1d" in names
    assert "REDACTED_e3b252570a2f" in names
    assert "REDACTED_8762331d93e2" in names


def test_REDACTED_e899cf89ab27_carreres_is_mother_of_REDACTED_7b9528898599():
    people = json.loads(
        Path("identity/data/people.json").read_text(encoding="utf-8")
    )
    relationships = json.loads(
        Path("identity/data/relationships.json").read_text(encoding="utf-8")
    )
    ids = {item["name"]: item["id"] for item in people}

    matching = [
        item
        for item in relationships
        if item["source_entity_id"] == ids["REDACTED_e3b252570a2f"]
        and item["target_entity_id"] == ids["REDACTED_8762331d93e2"]
    ]
    assert "mother" in {
        item["relationship_type"]
        for item in matching
    }

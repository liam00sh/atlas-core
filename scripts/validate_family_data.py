from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "identity" / "data"


def load(name: str) -> list[dict]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> None:
    people = load("people.json")
    animals = load("animals.json")
    relationships = load("relationships.json")

    valid_ids = {
        item["id"]
        for item in [*people, *animals]
    }

    invalid = [
        item
        for item in relationships
        if item["source_entity_id"] not in valid_ids
        or item["target_entity_id"] not in valid_ids
    ]

    if invalid:
        raise SystemExit(
            f"Hay {len(invalid)} relaciones con extremos inexistentes."
        )

    names = {item["name"]: item["id"] for item in people}
    REDACTED_e899cf89ab27_to_REDACTED_7b9528898599 = [
        item
        for item in relationships
        if item["source_entity_id"] == names["REDACTED_e3b252570a2f"]
        and item["target_entity_id"] == names["REDACTED_8762331d93e2"]
    ]

    if "mother" not in {
        item["relationship_type"]
        for item in REDACTED_e899cf89ab27_to_REDACTED_7b9528898599
    }:
        raise SystemExit(
            "Falta REDACTED_e3b252570a2f -> mother -> REDACTED_8762331d93e2."
        )

    print(
        f"Integridad correcta: {len(relationships)} relaciones válidas."
    )


if __name__ == "__main__":
    main()

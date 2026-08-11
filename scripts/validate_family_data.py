"""Valida referencias del almacenamiento de identidad configurado."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def data_directory() -> Path:
    configured = os.environ.get("ATLAS_IDENTITY_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return ROOT / "examples" / "private_runtime" / "identity"


def load(directory: Path, name: str) -> list[dict]:
    payload = json.loads((directory / name).read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise SystemExit(f"{name} no contiene una lista válida.")
    return payload


def main() -> None:
    directory = data_directory()
    people = load(directory, "people.json")
    animals = load(directory, "animals.json")
    relationships = load(directory, "relationships.json")

    person_ids = {item.get("id") for item in people}
    animal_ids = {item.get("id") for item in animals}
    valid_ids = person_ids | animal_ids
    if None in valid_ids or len(valid_ids) != len(people) + len(animals):
        raise SystemExit("Hay identificadores ausentes o duplicados.")

    invalid = [
        item
        for item in relationships
        if item.get("source_entity_id") not in valid_ids
        or item.get("target_entity_id") not in valid_ids
        or item.get("source_entity_id") == item.get("target_entity_id")
    ]
    if invalid:
        raise SystemExit(
            f"Hay {len(invalid)} relaciones con extremos inexistentes o reflexivos."
        )

    print(
        f"Integridad correcta: {len(people)} personas, {len(animals)} animales "
        f"y {len(relationships)} relaciones válidas."
    )


if __name__ == "__main__":
    main()

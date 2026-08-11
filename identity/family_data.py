"""Carga declarativa de personas, animales y relaciones privadas.

El repositorio no incluye datos familiares reales. La instalación privada debe
indicar un JSON mediante ``ATLAS_FAMILY_DATA_FILE`` o guardarlo como
``family.json`` dentro de ``ATLAS_PRIVATE_DATA_DIR``. Si no existe, Atlas carga
colecciones vacías y continúa funcionando sin inventar identidades.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _configured_path() -> Path | None:
    explicit = os.environ.get("ATLAS_FAMILY_DATA_FILE", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    private_root = os.environ.get("ATLAS_PRIVATE_DATA_DIR", "").strip()
    if private_root:
        return (Path(private_root).expanduser().resolve() / "family.json")

    return None


def _load_family_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    path = _configured_path()
    if path is None or not path.is_file():
        return [], [], []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return [], [], []

    if not isinstance(payload, dict):
        return [], [], []

    collections: list[list[dict[str, Any]]] = []
    for key in ("people", "animals", "relationships"):
        value = payload.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            return [], [], []
        collections.append(value)

    return collections[0], collections[1], collections[2]


FAMILY_PEOPLE, FAMILY_ANIMALS, FAMILY_RELATIONSHIPS = _load_family_data()
FAMILY_DATA_PATH = _configured_path()
FAMILY_DATA_LOADED = FAMILY_DATA_PATH is not None and FAMILY_DATA_PATH.is_file()

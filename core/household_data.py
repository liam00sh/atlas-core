"""Carga privada de hogares, residencias y nombres cotidianos."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value).casefold())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class Household:
    key: str
    label: str
    people: tuple[str, ...]
    animals: tuple[str, ...] = ()
    owners: tuple[str, ...] = ()
    tenure: str = ""
    notes: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    anonymous_companions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PersonLocation:
    person: str
    origin: str
    habitual_residence: str
    birth_place: str = ""
    previous_residences: tuple[str, ...] = ()
    summer_residence: str = ""
    aliases: tuple[str, ...] = ()


def _configured_path() -> Path | None:
    explicit = os.environ.get("ATLAS_HOUSEHOLD_DATA_FILE", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    private_root = os.environ.get("ATLAS_PRIVATE_DATA_DIR", "").strip()
    if private_root:
        return Path(private_root).expanduser().resolve() / "households.json"
    return None


def _read_payload() -> dict:
    path = _configured_path()
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


_PAYLOAD = _read_payload()
HOUSEHOLDS = tuple(
    Household(
        key=str(item.get("key", "")),
        label=str(item.get("label", "")),
        people=tuple(item.get("people", [])),
        animals=tuple(item.get("animals", [])),
        owners=tuple(item.get("owners", [])),
        tenure=str(item.get("tenure", "")),
        notes=tuple(item.get("notes", [])),
        aliases=tuple(item.get("aliases", [])),
        anonymous_companions=tuple(item.get("anonymous_companions", [])),
    )
    for item in _PAYLOAD.get("households", [])
    if isinstance(item, dict)
)
OTHER_PROPERTIES = {
    str(key): tuple(value)
    for key, value in _PAYLOAD.get("other_properties", {}).items()
    if isinstance(value, list)
}
FAMILY_GROUP_ORDER = tuple(
    tuple(group)
    for group in _PAYLOAD.get("family_group_order", [])
    if isinstance(group, list)
)
PERSON_LOCATIONS = tuple(
    PersonLocation(
        person=str(item.get("person", "")),
        origin=str(item.get("origin", "")),
        habitual_residence=str(item.get("habitual_residence", "")),
        birth_place=str(item.get("birth_place", "")),
        previous_residences=tuple(item.get("previous_residences", [])),
        summer_residence=str(item.get("summer_residence", "")),
        aliases=tuple(item.get("aliases", [])),
    )
    for item in _PAYLOAD.get("person_locations", [])
    if isinstance(item, dict)
)
PREFERRED_PERSON_NAMES = {
    str(key): str(value)
    for key, value in _PAYLOAD.get("preferred_person_names", {}).items()
}


def find_household(reference: str) -> Household | None:
    wanted = normalize_name(reference)
    if not wanted:
        return None
    for household in HOUSEHOLDS:
        candidates = (household.key, household.label, *household.people, *household.animals, *household.aliases)
        normalized = [normalize_name(item) for item in candidates]
        if wanted in normalized or any(wanted in candidate.split() for candidate in normalized):
            return household
    return None


def order_family_names(names: list[str]) -> list[str]:
    by_normalized = {normalize_name(name): name for name in names}
    ordered: list[str] = []
    used: set[str] = set()
    for group in FAMILY_GROUP_ORDER:
        for member in group:
            key = normalize_name(member)
            if key in by_normalized and key not in used:
                ordered.append(by_normalized[key])
                used.add(key)
    ordered.extend(sorted((name for name in names if normalize_name(name) not in used), key=normalize_name))
    return ordered


def preferred_person_name(full_name: str) -> str:
    clean = str(full_name or "").strip()
    if not clean:
        return ""
    return PREFERRED_PERSON_NAMES.get(clean, clean.split()[0])


def find_person_location(reference: str) -> PersonLocation | None:
    wanted = normalize_name(reference)
    if not wanted:
        return None
    for profile in PERSON_LOCATIONS:
        candidates = tuple(normalize_name(item) for item in (profile.person, *profile.aliases))
        if wanted in candidates or any(wanted in candidate.split() for candidate in candidates):
            return profile
    return None

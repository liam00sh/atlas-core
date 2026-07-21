"""
Datos declarativos de hogares y unidades familiares de Proyecto Atlas.

Este módulo no concede permisos ni autentica personas. Solo describe convivencia
y propiedades confirmadas para responder preguntas cotidianas.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


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


HOUSEHOLDS: tuple[Household, ...] = (
    Household(
        key="casa_liam",
        label="la casa familiar de Liam",
        people=(
            "María José Martínez Sanz",
            "José Vicente Navarro",
            "Lidia Vicente Martínez",
            "Roberto Amarillo Navarro",
            "Liam Vicente Martínez",
        ),
        animals=("Gato", "Funcio", "Lucas"),
        owners=("María José Martínez Sanz",),
        tenure="vivienda familiar",
        notes=(
            "José Vicente Navarro ayuda a pagar la vivienda, pero no figura como propietario.",
        ),
        aliases=("Liam", "María José", "José Vicente Navarro", "Lidia", "Roberto"),
    ),
    Household(
        key="piso_raul",
        label="el piso de Raúl",
        people=("Raúl Isidro Vicente Martínez",),
        tenure="alquiler compartido",
        notes=("Vive con compañeros de piso no identificados.",),
        aliases=("Raúl",),
        anonymous_companions=("unos compañeros de piso",),
    ),
    Household(
        key="casa_sara",
        label="la casa de Sara",
        people=("Sara", "Saray Izquierdo Carreres", "José Manuel Martínez Pérez", "Adra"),
        owners=("Sara",),
        tenure="vivienda en propiedad de Sara",
        aliases=("Sara", "Saray", "José Manuel Martínez Pérez", "Adra"),
    ),
    Household(
        key="piso_saray_alicante",
        label="el piso compartido de Saray en Alicante",
        people=("Saray Izquierdo Carreres",),
        tenure="alquiler compartido",
        notes=("En verano Saray suele estar en Caudete con su familia.",),
        aliases=("piso de Saray", "Saray Alicante"),
    ),
    Household(
        key="casa_pablo",
        label="la casa de Pablo en Monforte del Cid",
        people=("Pablo", "Alba Martínez Pérez"),
        owners=("Pablo",),
        notes=("Alba algunos fines de semana vuelve a la casa del pueblo.",),
        aliases=("Pablo", "Alba"),
    ),
    Household(
        key="casa_pepi_jose_miguel",
        label="la casa de Pepi Carreres y José Miguel",
        people=("Pepi Carreres López", "José Miguel Izquierdo Catalán", "Rubén Izquierdo Carreres"),
        aliases=("Pepi Carreres", "José Miguel", "Rubén"),
    ),
    Household(
        key="casa_georgel_manoli",
        label="la casa de Georgel y Manoli",
        people=("Georgel Melinte", "Manoli Carreres López", "Noa Melinte Carreres"),
        aliases=("Georgel", "Manoli", "Noa"),
    ),
    Household(
        key="casa_manuela_antonio",
        label="la casa de Manuela y Antonio",
        people=("Manuela López Serrano", "Antonio Carreres Hernández", "Estrella"),
        notes=("Suele haber uno de sus hijos o hijas ayudando a cuidarlos.",),
        aliases=("Manuela", "Antonio Carreres Hernández", "Estrella"),
    ),
    Household(
        key="casa_jorge",
        label="la casa de Jorge en Caudete",
        people=("Jorge Carreres López",),
        owners=("Jorge Carreres López",),
        aliases=("Jorge",),
    ),
    Household(
        key="casa_andres",
        label="la casa de Andrés en Caudete",
        people=("Andrés Carreres López",),
        owners=("Andrés Carreres López",),
        aliases=("Andrés",),
    ),
    Household(
        key="casa_antonio",
        label="la casa de Antonio en Caudete",
        people=("Antonio Carreres López",),
        owners=("Antonio Carreres López",),
        notes=(
            "A veces están sus hijos Yael Carreres y Yeray Carreres.",
            "Yael y Yeray viven normalmente con su madre, también en Caudete.",
        ),
        aliases=("Antonio Carreres López", "Yael", "Yeray"),
    ),
)

OTHER_PROPERTIES: dict[str, tuple[str, ...]] = {
    "José Manuel Martínez Pérez": (
        "una casa heredada con Alba Martínez Pérez en Beneixama",
        "un campo junto al río",
    ),
    "Alba Martínez Pérez": (
        "una casa heredada con José Manuel Martínez Pérez en Beneixama",
    ),
}

# Orden por ramas y unidades familiares. Los nombres de una misma tupla se
# muestran juntos antes de pasar a la siguiente rama.
FAMILY_GROUP_ORDER: tuple[tuple[str, ...], ...] = (
    ("Alba Martínez Pérez", "José Manuel Martínez Pérez"),
    ("José Evaristo Maestre Martínez", "María Teresa Maestre Martínez"),
    ("Claudia Vicente", "Martín Vicente"),
    ("Mario Amorós Vicente", "Salvador Amorós Vicente"),
)


def find_household(reference: str) -> Household | None:
    wanted = normalize_name(reference)
    if not wanted:
        return None
    for household in HOUSEHOLDS:
        candidates = (
            household.key,
            household.label,
            *household.people,
            *household.animals,
            *household.aliases,
        )
        normalized_candidates = [normalize_name(item) for item in candidates]
        if wanted in normalized_candidates:
            return household
        if any(wanted and wanted in candidate.split() for candidate in normalized_candidates):
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
    remaining = sorted(
        (name for name in names if normalize_name(name) not in used),
        key=normalize_name,
    )
    ordered.extend(remaining)
    return ordered


@dataclass(frozen=True)
class PersonLocation:
    """Origen y residencia cotidiana confirmados de una persona."""

    person: str
    origin: str
    habitual_residence: str
    birth_place: str = ""
    previous_residences: tuple[str, ...] = ()
    summer_residence: str = ""
    aliases: tuple[str, ...] = ()


PERSON_LOCATIONS: tuple[PersonLocation, ...] = (
    PersonLocation(
        person="Liam Vicente Martínez",
        origin="Beneixama",
        birth_place="Beneixama",
        habitual_residence="Beneixama",
        aliases=("Liam",),
    ),
    PersonLocation(
        person="Saray Izquierdo Carreres",
        origin="Caudete",
        birth_place="Caudete",
        habitual_residence="Alicante",
        summer_residence="Caudete",
        aliases=("Saray",),
    ),
    PersonLocation(
        person="Raúl Isidro Vicente Martínez",
        origin="Beneixama",
        birth_place="Beneixama",
        habitual_residence="Barcelona",
        previous_residences=("Beneixama",),
        aliases=("Raúl", "Raul"),
    ),
    PersonLocation(
        person="Noa Melinte Carreres",
        origin="Caudete",
        birth_place="Caudete",
        habitual_residence="Caudete",
        aliases=("Noa",),
    ),
)


PREFERRED_PERSON_NAMES: dict[str, str] = {
    "Liam Vicente Martínez": "Liam",
    "Saray Izquierdo Carreres": "Saray",
    "Raúl Isidro Vicente Martínez": "Raúl",
    "Noa Melinte Carreres": "Noa",
    "María José Martínez Sanz": "María José",
    "José Vicente Navarro": "José Vicente",
    "Lidia Vicente Martínez": "Lidia",
    "Roberto Amarillo Navarro": "Roberto",
    "José Manuel Martínez Pérez": "José Manuel",
    "Alba Martínez Pérez": "Alba",
    "José Evaristo Maestre Martínez": "José Evaristo",
    "María Teresa Maestre Martínez": "María Teresa",
    "Claudia Vicente": "Claudia",
    "Martín Vicente": "Martín",
    "Mario Amorós Vicente": "Mario",
    "Salvador Amorós Vicente": "Salvador",
    "Pepi Carreres López": "Pepi",
    "Josefa Carreres López": "Pepi",
    "José Miguel Izquierdo Catalán": "José Miguel",
    "Rubén Izquierdo Carreres": "Rubén",
    "Georgel Melinte": "Georgel",
    "Manoli Carreres López": "Manoli",
    "Manuela López Serrano": "Manuela",
    "Antonio Carreres Hernández": "Antonio",
    "Jorge Carreres López": "Jorge",
    "Andrés Carreres López": "Andrés",
    "Antonio Carreres López": "Antonio",
    "Yael Carreres": "Yael",
    "Yeray Carreres": "Yeray",
    "José Vicente": "Pepe Vicente",
    "José Martínez": "Pepe Martínez",
}


def preferred_person_name(full_name: str) -> str:
    """Devuelve el nombre cotidiano, conservando el completo si es necesario."""

    clean = str(full_name or "").strip()
    if not clean:
        return ""
    if clean in PREFERRED_PERSON_NAMES:
        return PREFERRED_PERSON_NAMES[clean]
    # Para nombres desconocidos se usa el primer nombre. Las capas de resolución
    # siguen trabajando con el identificador completo, así que esto solo afecta
    # a cómo se presenta la respuesta.
    return clean.split()[0]


def find_person_location(reference: str) -> PersonLocation | None:
    wanted = normalize_name(reference)
    if not wanted:
        return None
    for profile in PERSON_LOCATIONS:
        candidates = (profile.person, *profile.aliases)
        normalized_candidates = tuple(normalize_name(item) for item in candidates)
        if wanted in normalized_candidates:
            return profile
        if any(wanted and wanted in candidate.split() for candidate in normalized_candidates):
            return profile
    return None

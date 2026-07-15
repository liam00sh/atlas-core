"""
===============================================================================
Proyecto Atlas
Archivo: identity/animal.py

Descripción:
    Define la entidad Animal utilizada por Atlas Identity System.

    Un animal representa cualquier mascota o animal conocido por Daxter.

    Puede utilizarse para representar:

    - Perros.
    - Gatos.
    - Aves.
    - Peces.
    - Reptiles.
    - Pequeños mamíferos.
    - Cualquier otra especie.

    Ejemplos:

        Nala:
            Gata de Liam.

        Thor:
            Perro de una persona conocida.

        Espinete:
            Caracol del acuario.

    Esta clase almacena:

    - Identificador único.
    - Nombre.
    - Alias.
    - Especie.
    - Raza.
    - Sexo.
    - Género gramatical.
    - Fecha de nacimiento aproximada.
    - Estado vital.
    - Número de encuentros.
    - Primera y última interacción.
    - Resumen descriptivo.
    - Fechas de creación y actualización.

    Animal no:

    - Guarda información en archivos.
    - Decide quién es su propietario.
    - Gestiona relaciones.
    - Decide permisos.
    - Crea recuerdos.

    La propiedad, convivencia y cuidado se representarán mediante
    identity/relationship.py.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import uuid

from dataclasses import dataclass
from dataclasses import field

from datetime import datetime


# =============================================================================
# SEXO
# =============================================================================

MALE = "male"
FEMALE = "female"
UNKNOWN_SEX = "unknown"


VALID_ANIMAL_SEXES = {
    MALE,
    FEMALE,
    UNKNOWN_SEX,
}


# =============================================================================
# GÉNERO GRAMATICAL
# =============================================================================

VALID_GRAMMATICAL_GENDERS = {
    "masculine",
    "feminine",
    "neutral",
    "unknown",
}


# =============================================================================
# ESTADO DEL ANIMAL
# =============================================================================

ACTIVE = "active"
MISSING = "missing"
DECEASED = "deceased"
UNKNOWN_STATUS = "unknown"


VALID_ANIMAL_STATUSES = {
    ACTIVE,
    MISSING,
    DECEASED,
    UNKNOWN_STATUS,
}


ANIMAL_STATUS_LABELS = {
    ACTIVE: "Activo",
    MISSING: "Desaparecido",
    DECEASED: "Fallecido",
    UNKNOWN_STATUS: "Desconocido",
}


# =============================================================================
# ESPECIES COMUNES
# =============================================================================

DOG = "dog"
CAT = "cat"
BIRD = "bird"
FISH = "fish"
REPTILE = "reptile"
AMPHIBIAN = "amphibian"
RABBIT = "rabbit"
RODENT = "rodent"
HORSE = "horse"
INVERTEBRATE = "invertebrate"
OTHER_SPECIES = "other"
UNKNOWN_SPECIES = "unknown"


COMMON_SPECIES = {
    DOG,
    CAT,
    BIRD,
    FISH,
    REPTILE,
    AMPHIBIAN,
    RABBIT,
    RODENT,
    HORSE,
    INVERTEBRATE,
    OTHER_SPECIES,
    UNKNOWN_SPECIES,
}


SPECIES_LABELS = {
    DOG: "Perro",
    CAT: "Gato",
    BIRD: "Ave",
    FISH: "Pez",
    REPTILE: "Reptil",
    AMPHIBIAN: "Anfibio",
    RABBIT: "Conejo",
    RODENT: "Roedor",
    HORSE: "Caballo",
    INVERTEBRATE: "Invertebrado",
    OTHER_SPECIES: "Otra especie",
    UNKNOWN_SPECIES: "Especie desconocida",
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def is_valid_animal_status(
    status: str,
) -> bool:
    """
    Indica si un estado animal es válido.
    """

    return status in VALID_ANIMAL_STATUSES


def get_animal_status_label(
    status: str,
) -> str:
    """
    Devuelve el nombre legible de un estado.
    """

    return ANIMAL_STATUS_LABELS.get(
        status,
        "Desconocido",
    )


def get_species_label(
    species: str,
) -> str:
    """
    Devuelve el nombre legible de una especie conocida.

    Si se utiliza una especie personalizada, devuelve
    el propio valor recibido.
    """

    return SPECIES_LABELS.get(
        species,
        species.strip().capitalize()
        if species.strip()
        else "Especie desconocida",
    )


# =============================================================================
# ENTIDAD ANIMAL
# =============================================================================

@dataclass
class Animal:
    """
    Representa un animal conocido por Atlas.
    """

    name: str

    species: str

    id: str = field(
        default_factory=lambda: str(
            uuid.uuid4()
        )
    )

    aliases: list[str] = field(
        default_factory=list
    )

    breed: str | None = None

    sex: str = UNKNOWN_SEX

    grammatical_gender: str = "unknown"

    birth_date: str | None = None

    status: str = ACTIVE

    encounter_count: int = 0

    first_seen_at: str | None = None

    last_seen_at: str | None = None

    summary: str = ""

    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat(
            timespec="seconds"
        )
    )

    updated_at: str = field(
        default_factory=lambda: datetime.now().isoformat(
            timespec="seconds"
        )
    )

    def __post_init__(
        self,
    ) -> None:
        """
        Valida y normaliza los datos del animal.
        """

        self.id = self.id.strip()

        self.name = self.name.strip()

        self.species = self.species.strip().casefold()

        self.summary = self.summary.strip()

        if not self.id:

            raise ValueError(
                "Un animal debe tener un identificador."
            )

        if not self.name:

            raise ValueError(
                "Un animal debe tener un nombre."
            )

        if not self.species:

            raise ValueError(
                "Un animal debe tener una especie."
            )

        if self.sex not in VALID_ANIMAL_SEXES:

            raise ValueError(
                f"Sexo animal no válido: {self.sex}"
            )

        if (
            self.grammatical_gender
            not in VALID_GRAMMATICAL_GENDERS
        ):

            raise ValueError(
                "Género gramatical no válido: "
                f"{self.grammatical_gender}"
            )

        if self.status not in VALID_ANIMAL_STATUSES:

            raise ValueError(
                f"Estado animal no válido: {self.status}"
            )

        if self.encounter_count < 0:

            raise ValueError(
                "El número de encuentros no puede ser negativo."
            )

        if self.breed is not None:

            self.breed = (
                self.breed.strip()
                or None
            )

        if self.birth_date is not None:

            self.birth_date = (
                self.birth_date.strip()
                or None
            )

        self.aliases = self._normalize_aliases(
            self.aliases
        )

    @staticmethod
    def _normalize_aliases(
        aliases: list[str],
    ) -> list[str]:
        """
        Limpia alias vacíos y elimina duplicados.
        """

        normalized_aliases = []

        known_aliases = set()

        for alias in aliases:

            clean_alias = str(
                alias
            ).strip()

            if not clean_alias:
                continue

            alias_key = clean_alias.casefold()

            if alias_key in known_aliases:
                continue

            known_aliases.add(
                alias_key
            )

            normalized_aliases.append(
                clean_alias
            )

        return normalized_aliases

    def add_alias(
        self,
        alias: str,
    ) -> bool:
        """
        Añade un alias nuevo.
        """

        alias = alias.strip()

        if not alias:

            return False

        if alias.casefold() == self.name.casefold():

            return False

        existing_aliases = {
            current_alias.casefold()
            for current_alias in self.aliases
        }

        if alias.casefold() in existing_aliases:

            return False

        self.aliases.append(
            alias
        )

        self.touch()

        return True

    def remove_alias(
        self,
        alias: str,
    ) -> bool:
        """
        Elimina un alias existente.
        """

        alias_key = alias.strip().casefold()

        if not alias_key:

            return False

        for index, current_alias in enumerate(
            self.aliases
        ):

            if current_alias.casefold() == alias_key:

                del self.aliases[
                    index
                ]

                self.touch()

                return True

        return False

    def matches_name(
        self,
        value: str,
    ) -> bool:
        """
        Comprueba el nombre principal y los alias.
        """

        value_key = value.strip().casefold()

        if not value_key:

            return False

        if self.name.casefold() == value_key:

            return True

        return any(
            alias.casefold() == value_key
            for alias in self.aliases
        )

    def register_encounter(
        self,
        occurred_at: str | None = None,
    ) -> None:
        """
        Registra un encuentro nuevo con el animal.
        """

        encounter_time = (
            occurred_at
            or datetime.now().isoformat(
                timespec="seconds"
            )
        )

        if self.first_seen_at is None:

            self.first_seen_at = encounter_time

        self.last_seen_at = encounter_time

        self.encounter_count += 1

        self.touch()

    def update_summary(
        self,
        summary: str,
    ) -> None:
        """
        Actualiza el resumen descriptivo.
        """

        self.summary = summary.strip()

        self.touch()

    def update_status(
        self,
        status: str,
    ) -> None:
        """
        Actualiza el estado del animal.
        """

        if status not in VALID_ANIMAL_STATUSES:

            raise ValueError(
                f"Estado animal no válido: {status}"
            )

        self.status = status

        self.touch()

    def update_species(
        self,
        species: str,
        breed: str | None = None,
    ) -> None:
        """
        Actualiza la especie y opcionalmente la raza.
        """

        species = species.strip().casefold()

        if not species:

            raise ValueError(
                "La especie no puede estar vacía."
            )

        self.species = species

        if breed is not None:

            self.breed = (
                breed.strip()
                or None
            )

        self.touch()

    def set_sex(
        self,
        sex: str,
    ) -> None:
        """
        Actualiza el sexo registrado.
        """

        if sex not in VALID_ANIMAL_SEXES:

            raise ValueError(
                f"Sexo animal no válido: {sex}"
            )

        self.sex = sex

        self.touch()

    def set_grammatical_gender(
        self,
        grammatical_gender: str,
    ) -> None:
        """
        Actualiza el género gramatical.
        """

        if (
            grammatical_gender
            not in VALID_GRAMMATICAL_GENDERS
        ):

            raise ValueError(
                "Género gramatical no válido: "
                f"{grammatical_gender}"
            )

        self.grammatical_gender = (
            grammatical_gender
        )

        self.touch()

    def touch(
        self,
    ) -> None:
        """
        Actualiza la fecha de modificación.
        """

        self.updated_at = datetime.now().isoformat(
            timespec="seconds"
        )

    def to_dict(
        self,
    ) -> dict:
        """
        Convierte el animal en un diccionario serializable.
        """

        return {
            "id": self.id,
            "name": self.name,
            "aliases": list(
                self.aliases
            ),
            "species": self.species,
            "breed": self.breed,
            "sex": self.sex,
            "grammatical_gender": (
                self.grammatical_gender
            ),
            "birth_date": self.birth_date,
            "status": self.status,
            "encounter_count": (
                self.encounter_count
            ),
            "first_seen_at": (
                self.first_seen_at
            ),
            "last_seen_at": (
                self.last_seen_at
            ),
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "Animal":
        """
        Crea un animal desde un diccionario.
        """

        if not isinstance(
            data,
            dict,
        ):

            raise TypeError(
                "Los datos de un animal deben ser "
                "un diccionario."
            )

        return cls(
            id=str(
                data.get(
                    "id",
                    str(uuid.uuid4()),
                )
            ),
            name=str(
                data.get(
                    "name",
                    "",
                )
            ),
            aliases=list(
                data.get(
                    "aliases",
                    [],
                )
            ),
            species=str(
                data.get(
                    "species",
                    UNKNOWN_SPECIES,
                )
            ),
            breed=data.get(
                "breed"
            ),
            sex=str(
                data.get(
                    "sex",
                    UNKNOWN_SEX,
                )
            ),
            grammatical_gender=str(
                data.get(
                    "grammatical_gender",
                    "unknown",
                )
            ),
            birth_date=data.get(
                "birth_date"
            ),
            status=str(
                data.get(
                    "status",
                    ACTIVE,
                )
            ),
            encounter_count=int(
                data.get(
                    "encounter_count",
                    0,
                )
            ),
            first_seen_at=data.get(
                "first_seen_at"
            ),
            last_seen_at=data.get(
                "last_seen_at"
            ),
            summary=str(
                data.get(
                    "summary",
                    "",
                )
            ),
            created_at=str(
                data.get(
                    "created_at",
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                )
            ),
            updated_at=str(
                data.get(
                    "updated_at",
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                )
            ),
        )
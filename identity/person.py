"""
===============================================================================
Proyecto Atlas
Archivo: identity/person.py

Descripción:
    Define la entidad Person utilizada por Atlas Identity System.

    Una persona representa a cualquier individuo conocido por Daxter,
    independientemente de que utilice Atlas o no.

    Ejemplos:

    - Liam:
        Usuario principal y propietario del sistema.

    - Saray:
        Usuaria con perfil propio.

    - Rubén:
        Persona conocida y hermano de Saray.

    - Un invitado ocasional:
        Puede existir como persona sin disponer de usuario,
        memoria propia ni permisos especiales.

    Esta clase almacena información básica de identidad:

    - Identificador único.
    - Nombre.
    - Alias.
    - Género gramatical.
    - Estado social dentro de Atlas.
    - Número de encuentros.
    - Primera y última interacción.
    - Persona que la presentó.
    - Resumen descriptivo.
    - Perfil de usuario asociado, cuando exista.
    - Fecha de creación y actualización.

    Person no:

    - Lee ni escribe archivos.
    - Decide permisos.
    - Gestiona relaciones.
    - Crea usuarios.
    - Ejecuta acciones sobre Atlas.

    Es únicamente una representación estructurada de una persona.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import uuid

from dataclasses import dataclass
from dataclasses import field

from datetime import datetime

from identity.person_status import GUEST
from identity.person_status import PERSON_STATUSES
from identity.person_status import USER


# =============================================================================
# CONSTANTES
# =============================================================================

VALID_GRAMMATICAL_GENDERS = {
    "masculine",
    "feminine",
    "neutral",
    "unknown",
}


# =============================================================================
# ENTIDAD PERSONA
# =============================================================================

@dataclass
class Person:
    """
    Representa una persona conocida por Atlas.

    Atributos:
        id:
            Identificador único de la persona.

        name:
            Nombre principal utilizado por Atlas.

        aliases:
            Otros nombres, apodos o formas de identificarla.

        grammatical_gender:
            Género gramatical utilizado para adaptar pronombres
            y determinadas respuestas.

        status:
            Estado social dentro de Atlas.

            Valores admitidos:

            - guest
            - known
            - regular
            - user

        encounter_count:
            Número de encuentros registrados.

        first_seen_at:
            Fecha y hora de la primera interacción conocida.

        last_seen_at:
            Fecha y hora de la interacción más reciente.

        introduced_by:
            Identificador o nombre de la persona que la presentó.

        summary:
            Descripción breve y actualizable.

        user_profile:
            Nombre del perfil completo de UserManager asociado.

            Será None cuando la persona no sea usuaria de Atlas.

        created_at:
            Fecha de creación del registro.

        updated_at:
            Fecha de última modificación.
    """

    name: str

    id: str = field(
        default_factory=lambda: str(
            uuid.uuid4()
        )
    )

    aliases: list[str] = field(
        default_factory=list
    )

    grammatical_gender: str = "unknown"

    status: str = GUEST

    encounter_count: int = 0

    first_seen_at: str | None = None

    last_seen_at: str | None = None

    introduced_by: str | None = None

    summary: str = ""

    user_profile: str | None = None

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
        Valida y normaliza los datos después de crear la persona.
        """

        self.name = self.name.strip()

        if not self.name:

            raise ValueError(
                "Una persona debe tener un nombre."
            )

        self.id = self.id.strip()

        if not self.id:

            raise ValueError(
                "Una persona debe tener un identificador."
            )

        if self.status not in PERSON_STATUSES:

            raise ValueError(
                f"Estado de persona no válido: {self.status}"
            )

        if (
            self.grammatical_gender
            not in VALID_GRAMMATICAL_GENDERS
        ):

            raise ValueError(
                "Género gramatical no válido: "
                f"{self.grammatical_gender}"
            )

        if self.encounter_count < 0:

            raise ValueError(
                "El número de encuentros no puede ser negativo."
            )

        self.aliases = self._normalize_aliases(
            self.aliases
        )

        self.summary = self.summary.strip()

        if self.introduced_by is not None:

            self.introduced_by = (
                self.introduced_by.strip()
                or None
            )

        if self.user_profile is not None:

            self.user_profile = (
                self.user_profile.strip()
                or None
            )

        if self.status == USER and self.user_profile is None:

            raise ValueError(
                "Una persona con estado user debe tener "
                "un perfil de usuario asociado."
            )

    @staticmethod
    def _normalize_aliases(
        aliases: list[str],
    ) -> list[str]:
        """
        Limpia alias vacíos y elimina duplicados.

        La comparación ignora mayúsculas y minúsculas,
        pero conserva la primera forma escrita.
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
        Añade un alias si todavía no existe.

        Devuelve:
            True:
                El alias se añadió.

            False:
                El alias estaba vacío o ya existía.
        """

        alias = alias.strip()

        if not alias:
            return False

        existing_aliases = {
            existing_alias.casefold()
            for existing_alias in self.aliases
        }

        if alias.casefold() in existing_aliases:
            return False

        if alias.casefold() == self.name.casefold():
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

        La comparación ignora mayúsculas y minúsculas.
        """

        alias_key = alias.strip().casefold()

        if not alias_key:
            return False

        for index, existing_alias in enumerate(
            self.aliases
        ):

            if existing_alias.casefold() == alias_key:

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
        Comprueba si un texto coincide con el nombre
        principal o con alguno de los alias.
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
        Registra un nuevo encuentro con la persona.

        Si no se proporciona fecha, utiliza el momento actual.
        """

        encounter_time = (
            occurred_at
            or datetime.now().isoformat(
                timespec="seconds"
            )
        )

        if self.first_seen_at is None:

            self.first_seen_at = (
                encounter_time
            )

        self.last_seen_at = (
            encounter_time
        )

        self.encounter_count += 1

        self.touch()

    def change_status(
        self,
        new_status: str,
    ) -> None:
        """
        Cambia el estado social de la persona.

        Una persona no puede convertirse en user
        sin tener un perfil asociado.
        """

        if new_status not in PERSON_STATUSES:

            raise ValueError(
                f"Estado de persona no válido: {new_status}"
            )

        if (
            new_status == USER
            and self.user_profile is None
        ):

            raise ValueError(
                "No se puede establecer el estado user "
                "sin un perfil de usuario asociado."
            )

        self.status = new_status

        self.touch()

    def link_user_profile(
        self,
        user_profile: str,
    ) -> None:
        """
        Vincula la persona con un perfil de UserManager.

        Al vincularlo, la persona pasa a estado user.
        """

        user_profile = user_profile.strip()

        if not user_profile:

            raise ValueError(
                "El perfil de usuario no puede estar vacío."
            )

        self.user_profile = (
            user_profile
        )

        self.status = USER

        self.touch()

    def unlink_user_profile(
        self,
        fallback_status: str,
    ) -> None:
        """
        Elimina la vinculación con UserManager.

        Parámetros:
            fallback_status:
                Estado que debe adoptar después de dejar
                de ser usuaria.

        No se permite utilizar user como estado de respaldo.
        """

        if fallback_status not in PERSON_STATUSES:

            raise ValueError(
                f"Estado de respaldo no válido: "
                f"{fallback_status}"
            )

        if fallback_status == USER:

            raise ValueError(
                "El estado de respaldo no puede ser user."
            )

        self.user_profile = None

        self.status = fallback_status

        self.touch()

    def update_summary(
        self,
        summary: str,
    ) -> None:
        """
        Actualiza el resumen descriptivo de la persona.
        """

        self.summary = summary.strip()

        self.touch()

    def set_grammatical_gender(
        self,
        grammatical_gender: str,
    ) -> None:
        """
        Actualiza el género gramatical utilizado
        para adaptar respuestas y pronombres.
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

    def is_user(
        self,
    ) -> bool:
        """
        Indica si la persona dispone de perfil completo.
        """

        return (
            self.status == USER
            and self.user_profile is not None
        )

    def to_dict(
        self,
    ) -> dict:
        """
        Convierte la persona en un diccionario serializable.
        """

        return {
            "id": self.id,

            "name": self.name,

            "aliases": list(
                self.aliases
            ),

            "grammatical_gender": (
                self.grammatical_gender
            ),

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

            "introduced_by": (
                self.introduced_by
            ),

            "summary": self.summary,

            "user_profile": (
                self.user_profile
            ),

            "created_at": self.created_at,

            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "Person":
        """
        Crea una persona desde un diccionario.

        Los campos ausentes utilizan valores seguros
        por defecto.
        """

        if not isinstance(
            data,
            dict,
        ):

            raise TypeError(
                "Los datos de una persona deben ser un diccionario."
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

            grammatical_gender=str(
                data.get(
                    "grammatical_gender",
                    "unknown",
                )
            ),

            status=str(
                data.get(
                    "status",
                    GUEST,
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

            introduced_by=data.get(
                "introduced_by"
            ),

            summary=str(
                data.get(
                    "summary",
                    "",
                )
            ),

            user_profile=data.get(
                "user_profile"
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
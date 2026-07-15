"""
===============================================================================
Proyecto Atlas
Archivo: identity/relationship.py

Descripción:
    Define la entidad Relationship utilizada por Atlas Identity System.

    Una relación conecta dos entidades conocidas por Atlas.

    Actualmente las entidades admitidas son:

    - person:
        Una persona.

    - animal:
        Un animal o mascota.

    Ejemplos:

        Rubén
            └── brother ──> Saray

        Liam
            └── pet_owner ──> Nala

        Nala
            └── pet_of ──> Liam

    Cada relación contiene:

    - Identificador único.
    - Entidad de origen.
    - Tipo de la entidad de origen.
    - Tipo de relación.
    - Entidad de destino.
    - Tipo de la entidad de destino.
    - Confirmación.
    - Origen de la información.
    - Nivel de confianza.
    - Notas.
    - Fechas de creación y actualización.

    Relationship no:

    - Guarda archivos.
    - Comprueba que las entidades existan.
    - Decide permisos.
    - Deduce parentescos indirectos.
    - Crea perfiles.

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
# TIPOS DE ENTIDAD
# =============================================================================

PERSON_ENTITY = "person"
ANIMAL_ENTITY = "animal"


ENTITY_TYPES = {
    PERSON_ENTITY,
    ANIMAL_ENTITY,
}


ENTITY_TYPE_LABELS = {
    PERSON_ENTITY: "Persona",
    ANIMAL_ENTITY: "Animal",
}


# =============================================================================
# RELACIONES PERSONALES Y FAMILIARES
# =============================================================================

PARTNER = "partner"
SPOUSE = "spouse"
EX_PARTNER = "ex_partner"

MOTHER = "mother"
FATHER = "father"
PARENT = "parent"

DAUGHTER = "daughter"
SON = "son"
CHILD = "child"

SISTER = "sister"
BROTHER = "brother"
SIBLING = "sibling"

GRANDMOTHER = "grandmother"
GRANDFATHER = "grandfather"
GRANDPARENT = "grandparent"

GRANDDAUGHTER = "granddaughter"
GRANDSON = "grandson"
GRANDCHILD = "grandchild"

AUNT = "aunt"
UNCLE = "uncle"

NIECE = "niece"
NEPHEW = "nephew"

COUSIN = "cousin"


# =============================================================================
# RELACIONES SOCIALES
# =============================================================================

FRIEND = "friend"
CLOSE_FRIEND = "close_friend"
ACQUAINTANCE = "acquaintance"
NEIGHBOR = "neighbor"


# =============================================================================
# RELACIONES PROFESIONALES
# =============================================================================

COWORKER = "coworker"
COLLEAGUE = "colleague"
MANAGER = "manager"
EMPLOYEE = "employee"
CLIENT = "client"


# =============================================================================
# RELACIONES CON ANIMALES
# =============================================================================

PET_OWNER = "pet_owner"
PET_OF = "pet_of"

CARES_FOR = "cares_for"
CARED_FOR_BY = "cared_for_by"

LIVES_WITH = "lives_with"

ANIMAL_COMPANION = "animal_companion"


# =============================================================================
# RELACIONES CONTEXTUALES
# =============================================================================

INTRODUCED_BY = "introduced_by"
KNOWN_THROUGH = "known_through"

OTHER = "other"


# =============================================================================
# COLECCIÓN DE RELACIONES VÁLIDAS
# =============================================================================

RELATIONSHIP_TYPES = {
    PARTNER,
    SPOUSE,
    EX_PARTNER,

    MOTHER,
    FATHER,
    PARENT,

    DAUGHTER,
    SON,
    CHILD,

    SISTER,
    BROTHER,
    SIBLING,

    GRANDMOTHER,
    GRANDFATHER,
    GRANDPARENT,

    GRANDDAUGHTER,
    GRANDSON,
    GRANDCHILD,

    AUNT,
    UNCLE,

    NIECE,
    NEPHEW,

    COUSIN,

    FRIEND,
    CLOSE_FRIEND,
    ACQUAINTANCE,
    NEIGHBOR,

    COWORKER,
    COLLEAGUE,
    MANAGER,
    EMPLOYEE,
    CLIENT,

    PET_OWNER,
    PET_OF,
    CARES_FOR,
    CARED_FOR_BY,
    LIVES_WITH,
    ANIMAL_COMPANION,

    INTRODUCED_BY,
    KNOWN_THROUGH,

    OTHER,
}


# =============================================================================
# NOMBRES LEGIBLES
# =============================================================================

RELATIONSHIP_LABELS = {
    PARTNER: "pareja",
    SPOUSE: "cónyuge",
    EX_PARTNER: "expareja",

    MOTHER: "madre",
    FATHER: "padre",
    PARENT: "progenitor",

    DAUGHTER: "hija",
    SON: "hijo",
    CHILD: "descendiente",

    SISTER: "hermana",
    BROTHER: "hermano",
    SIBLING: "hermano o hermana",

    GRANDMOTHER: "abuela",
    GRANDFATHER: "abuelo",
    GRANDPARENT: "abuelo o abuela",

    GRANDDAUGHTER: "nieta",
    GRANDSON: "nieto",
    GRANDCHILD: "nieto o nieta",

    AUNT: "tía",
    UNCLE: "tío",

    NIECE: "sobrina",
    NEPHEW: "sobrino",

    COUSIN: "primo o prima",

    FRIEND: "amigo o amiga",
    CLOSE_FRIEND: "amigo o amiga cercana",
    ACQUAINTANCE: "persona conocida",
    NEIGHBOR: "vecino o vecina",

    COWORKER: "compañero o compañera de trabajo",
    COLLEAGUE: "colega",
    MANAGER: "responsable",
    EMPLOYEE: "empleado o empleada",
    CLIENT: "cliente",

    PET_OWNER: "propietario o responsable",
    PET_OF: "mascota de",
    CARES_FOR: "cuida de",
    CARED_FOR_BY: "recibe cuidados de",
    LIVES_WITH: "convive con",
    ANIMAL_COMPANION: "compañero animal",

    INTRODUCED_BY: "presentado por",
    KNOWN_THROUGH: "conocido a través de",

    OTHER: "otra relación",
}


# =============================================================================
# RELACIONES INVERSAS
# =============================================================================

INVERSE_RELATIONSHIPS = {
    PARTNER: PARTNER,
    SPOUSE: SPOUSE,
    EX_PARTNER: EX_PARTNER,

    MOTHER: CHILD,
    FATHER: CHILD,
    PARENT: CHILD,

    DAUGHTER: PARENT,
    SON: PARENT,
    CHILD: PARENT,

    SISTER: SIBLING,
    BROTHER: SIBLING,
    SIBLING: SIBLING,

    GRANDMOTHER: GRANDCHILD,
    GRANDFATHER: GRANDCHILD,
    GRANDPARENT: GRANDCHILD,

    GRANDDAUGHTER: GRANDPARENT,
    GRANDSON: GRANDPARENT,
    GRANDCHILD: GRANDPARENT,

    AUNT: NIECE,
    UNCLE: NEPHEW,

    NIECE: AUNT,
    NEPHEW: UNCLE,

    COUSIN: COUSIN,

    FRIEND: FRIEND,
    CLOSE_FRIEND: CLOSE_FRIEND,
    ACQUAINTANCE: ACQUAINTANCE,
    NEIGHBOR: NEIGHBOR,

    COWORKER: COWORKER,
    COLLEAGUE: COLLEAGUE,

    MANAGER: EMPLOYEE,
    EMPLOYEE: MANAGER,

    CLIENT: CLIENT,

    PET_OWNER: PET_OF,
    PET_OF: PET_OWNER,

    CARES_FOR: CARED_FOR_BY,
    CARED_FOR_BY: CARES_FOR,

    LIVES_WITH: LIVES_WITH,
    ANIMAL_COMPANION: ANIMAL_COMPANION,

    INTRODUCED_BY: KNOWN_THROUGH,
    KNOWN_THROUGH: INTRODUCED_BY,

    OTHER: OTHER,
}


# =============================================================================
# ORIGEN DE LA INFORMACIÓN
# =============================================================================

MANUAL_SOURCE = "manual"
USER_SOURCE = "user"
ASSISTANT_SOURCE = "assistant"
INFERRED_SOURCE = "inferred"
IMPORTED_SOURCE = "imported"


RELATIONSHIP_SOURCES = {
    MANUAL_SOURCE,
    USER_SOURCE,
    ASSISTANT_SOURCE,
    INFERRED_SOURCE,
    IMPORTED_SOURCE,
}


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def is_valid_entity_type(
    entity_type: str,
) -> bool:
    """
    Indica si un tipo de entidad está admitido.
    """

    return entity_type in ENTITY_TYPES


def get_entity_type_label(
    entity_type: str,
) -> str:
    """
    Devuelve el nombre legible del tipo de entidad.
    """

    return ENTITY_TYPE_LABELS.get(
        entity_type,
        "Entidad desconocida",
    )


def is_valid_relationship_type(
    relationship_type: str,
) -> bool:
    """
    Indica si un tipo de relación está admitido.
    """

    return relationship_type in RELATIONSHIP_TYPES


def get_relationship_label(
    relationship_type: str,
) -> str:
    """
    Devuelve el nombre legible de una relación.
    """

    return RELATIONSHIP_LABELS.get(
        relationship_type,
        "relación desconocida",
    )


def get_inverse_relationship_type(
    relationship_type: str,
) -> str | None:
    """
    Devuelve el tipo inverso genérico.
    """

    return INVERSE_RELATIONSHIPS.get(
        relationship_type
    )


# =============================================================================
# ENTIDAD RELACIÓN
# =============================================================================

@dataclass
class Relationship:
    """
    Representa una relación entre dos entidades.
    """

    source_entity_id: str

    relationship_type: str

    target_entity_id: str

    source_entity_type: str = PERSON_ENTITY

    target_entity_type: str = PERSON_ENTITY

    id: str = field(
        default_factory=lambda: str(
            uuid.uuid4()
        )
    )

    confirmed: bool = False

    information_source: str = USER_SOURCE

    registered_by: str | None = None

    confidence: float = 1.0

    notes: str = ""

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
        Valida y normaliza la relación.
        """

        self.id = self.id.strip()

        self.source_entity_id = (
            self.source_entity_id.strip()
        )

        self.target_entity_id = (
            self.target_entity_id.strip()
        )

        self.source_entity_type = (
            self.source_entity_type.strip()
        )

        self.target_entity_type = (
            self.target_entity_type.strip()
        )

        self.relationship_type = (
            self.relationship_type.strip()
        )

        self.information_source = (
            self.information_source.strip()
        )

        self.notes = self.notes.strip()

        if self.registered_by is not None:

            self.registered_by = (
                self.registered_by.strip()
                or None
            )

        if not self.id:

            raise ValueError(
                "Una relación debe tener un identificador."
            )

        if not self.source_entity_id:

            raise ValueError(
                "La relación debe tener una entidad de origen."
            )

        if not self.target_entity_id:

            raise ValueError(
                "La relación debe tener una entidad de destino."
            )

        if not is_valid_entity_type(
            self.source_entity_type
        ):

            raise ValueError(
                "Tipo de entidad de origen no válido: "
                f"{self.source_entity_type}"
            )

        if not is_valid_entity_type(
            self.target_entity_type
        ):

            raise ValueError(
                "Tipo de entidad de destino no válido: "
                f"{self.target_entity_type}"
            )

        same_entity = (
            self.source_entity_type
            == self.target_entity_type

            and self.source_entity_id.casefold()
            == self.target_entity_id.casefold()
        )

        if same_entity:

            raise ValueError(
                "Una entidad no puede mantener esta relación "
                "consigo misma."
            )

        if not is_valid_relationship_type(
            self.relationship_type
        ):

            raise ValueError(
                "Tipo de relación no válido: "
                f"{self.relationship_type}"
            )

        if (
            self.information_source
            not in RELATIONSHIP_SOURCES
        ):

            raise ValueError(
                "Origen de relación no válido: "
                f"{self.information_source}"
            )

        self.confidence = float(
            self.confidence
        )

        if not 0.0 <= self.confidence <= 1.0:

            raise ValueError(
                "La confianza debe estar entre 0.0 y 1.0."
            )

    def matches(
        self,
        source_entity_id: str,
        relationship_type: str,
        target_entity_id: str,
        source_entity_type: str | None = None,
        target_entity_type: str | None = None,
    ) -> bool:
        """
        Comprueba si la relación coincide con unos datos.
        """

        if (
            source_entity_type is not None
            and self.source_entity_type
            != source_entity_type
        ):

            return False

        if (
            target_entity_type is not None
            and self.target_entity_type
            != target_entity_type
        ):

            return False

        return (
            self.source_entity_id.casefold()
            == source_entity_id.strip().casefold()

            and self.relationship_type
            == relationship_type.strip()

            and self.target_entity_id.casefold()
            == target_entity_id.strip().casefold()
        )

    def involves_entity(
        self,
        entity_id: str,
        entity_type: str | None = None,
    ) -> bool:
        """
        Indica si una entidad participa en la relación.
        """

        entity_key = entity_id.strip().casefold()

        if not entity_key:

            return False

        source_matches = (
            self.source_entity_id.casefold()
            == entity_key

            and (
                entity_type is None
                or self.source_entity_type
                == entity_type
            )
        )

        target_matches = (
            self.target_entity_id.casefold()
            == entity_key

            and (
                entity_type is None
                or self.target_entity_type
                == entity_type
            )
        )

        return (
            source_matches
            or target_matches
        )

    def confirm(
        self,
        registered_by: str | None = None,
    ) -> None:
        """
        Marca la relación como confirmada.
        """

        self.confirmed = True

        self.confidence = 1.0

        if registered_by is not None:

            self.registered_by = (
                registered_by.strip()
                or None
            )

        self.touch()

    def unconfirm(
        self,
    ) -> None:
        """
        Marca la relación como no confirmada.
        """

        self.confirmed = False

        self.touch()

    def update_confidence(
        self,
        confidence: float,
    ) -> None:
        """
        Modifica el nivel de confianza.
        """

        confidence = float(
            confidence
        )

        if not 0.0 <= confidence <= 1.0:

            raise ValueError(
                "La confianza debe estar entre 0.0 y 1.0."
            )

        self.confidence = confidence

        self.touch()

    def update_notes(
        self,
        notes: str,
    ) -> None:
        """
        Actualiza las notas.
        """

        self.notes = notes.strip()

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

    def create_inverse(
        self,
        inverse_relationship_type: str | None = None,
    ) -> "Relationship":
        """
        Crea una relación inversa sin guardarla.
        """

        resolved_inverse_type = (
            inverse_relationship_type
            or get_inverse_relationship_type(
                self.relationship_type
            )
        )

        if resolved_inverse_type is None:

            raise ValueError(
                "No existe una relación inversa definida "
                f"para {self.relationship_type}."
            )

        if not is_valid_relationship_type(
            resolved_inverse_type
        ):

            raise ValueError(
                "Tipo de relación inversa no válido: "
                f"{resolved_inverse_type}"
            )

        return Relationship(
            source_entity_id=(
                self.target_entity_id
            ),
            source_entity_type=(
                self.target_entity_type
            ),
            relationship_type=(
                resolved_inverse_type
            ),
            target_entity_id=(
                self.source_entity_id
            ),
            target_entity_type=(
                self.source_entity_type
            ),
            confirmed=self.confirmed,
            information_source=(
                self.information_source
            ),
            registered_by=(
                self.registered_by
            ),
            confidence=self.confidence,
            notes=(
                "Relación inversa generada a partir de "
                f"{self.id}."
            ),
        )

    def to_dict(
        self,
    ) -> dict:
        """
        Convierte la relación en un diccionario.
        """

        return {
            "id": self.id,
            "source_entity_id": (
                self.source_entity_id
            ),
            "source_entity_type": (
                self.source_entity_type
            ),
            "relationship_type": (
                self.relationship_type
            ),
            "target_entity_id": (
                self.target_entity_id
            ),
            "target_entity_type": (
                self.target_entity_type
            ),
            "confirmed": self.confirmed,
            "information_source": (
                self.information_source
            ),
            "registered_by": (
                self.registered_by
            ),
            "confidence": self.confidence,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
    ) -> "Relationship":
        """
        Crea una relación desde un diccionario.
        """

        if not isinstance(
            data,
            dict,
        ):

            raise TypeError(
                "Los datos de una relación deben ser "
                "un diccionario."
            )

        return cls(
            id=str(
                data.get(
                    "id",
                    str(uuid.uuid4()),
                )
            ),
            source_entity_id=str(
                data.get(
                    "source_entity_id",
                    "",
                )
            ),
            source_entity_type=str(
                data.get(
                    "source_entity_type",
                    PERSON_ENTITY,
                )
            ),
            relationship_type=str(
                data.get(
                    "relationship_type",
                    "",
                )
            ),
            target_entity_id=str(
                data.get(
                    "target_entity_id",
                    "",
                )
            ),
            target_entity_type=str(
                data.get(
                    "target_entity_type",
                    PERSON_ENTITY,
                )
            ),
            confirmed=bool(
                data.get(
                    "confirmed",
                    False,
                )
            ),
            information_source=str(
                data.get(
                    "information_source",
                    USER_SOURCE,
                )
            ),
            registered_by=data.get(
                "registered_by"
            ),
            confidence=float(
                data.get(
                    "confidence",
                    1.0,
                )
            ),
            notes=str(
                data.get(
                    "notes",
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
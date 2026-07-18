"""
===============================================================================
Proyecto Atlas
Archivo: identity/relationship_engine.py

Descripción:
    Gestiona las relaciones entre las entidades conocidas por Atlas.

    RelationshipEngine actúa como capa de servicio entre:

        identity/people_manager.py
        identity/identity_storage.py
        identity/relationship.py

    Sus responsabilidades principales son:

    - Comprobar que las entidades de una relación existen.
    - Crear relaciones entre personas y animales.
    - Evitar relaciones duplicadas.
    - Generar relaciones inversas.
    - Elegir relaciones inversas específicas según el género.
    - Consultar relaciones entrantes y salientes.
    - Buscar conexiones entre entidades.
    - Eliminar relaciones.
    - Confirmar relaciones.
    - Preparar descripciones legibles.
    - Realizar deducciones indirectas sencillas.

    Ejemplos:

        Liam --partner--> Saray

    puede generar automáticamente:

        Saray --partner--> Liam


        Rubén --brother--> Saray

    puede generar:

        Saray --sister--> Rubén


        Liam --pet_owner--> Nala

    puede generar:

        Nala --pet_of--> Liam

    RelationshipEngine no:

    - Lee ni escribe archivos JSON directamente.
    - Reconoce personas mediante voz o cámara.
    - Decide permisos de memoria.
    - Crea perfiles de usuario.
    - Interpreta conversaciones completas.
    - Genera todavía árboles gráficos.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from core.log_manager import info

from identity.animal import Animal

from identity.identity_storage import IdentityStorage

from identity.people_manager import PeopleManager

from identity.person import Person

from identity.relationship import ANIMAL_ENTITY
from identity.relationship import PERSON_ENTITY

from identity.relationship import AUNT
from identity.relationship import BROTHER
from identity.relationship import CARED_FOR_BY
from identity.relationship import CARES_FOR
from identity.relationship import CHILD
from identity.relationship import COUSIN
from identity.relationship import DAUGHTER
from identity.relationship import FATHER
from identity.relationship import FRIEND
from identity.relationship import GRANDFATHER
from identity.relationship import GRANDMOTHER
from identity.relationship import GRANDPARENT
from identity.relationship import GRANDSON
from identity.relationship import GRANDDAUGHTER
from identity.relationship import GRANDCHILD
from identity.relationship import LIVES_WITH
from identity.relationship import ANIMAL_COMPANION
from identity.relationship import MOTHER
from identity.relationship import NEPHEW
from identity.relationship import NIECE
from identity.relationship import PARENT
from identity.relationship import PARTNER
from identity.relationship import PET_OF
from identity.relationship import PET_OWNER
from identity.relationship import SIBLING
from identity.relationship import SISTER
from identity.relationship import SON
from identity.relationship import SPOUSE
from identity.relationship import UNCLE

from identity.relationship import Relationship

from identity.relationship import get_inverse_relationship_type
from identity.relationship import get_relationship_label
from identity.relationship import is_valid_entity_type
from identity.relationship import is_valid_relationship_type


# =============================================================================
# CLASE PRINCIPAL
# =============================================================================

class RelationshipEngine:
    """
    Gestiona las relaciones del sistema de identidades.

    Todas las operaciones persistentes se delegan
    en IdentityStorage.
    """

    # Política de presentación pública: estos vínculos se conservan
    # internamente, pero se describen únicamente como primos.
    _PUBLIC_COUSIN_ONLY_NAMES = {
        frozenset({"Liam Vicente Martínez", "José Manuel Martínez Pérez"}),
        frozenset({"Liam Vicente Martínez", "Alba Martínez Pérez"}),
    }

    def __init__(
        self,
        people_manager: PeopleManager,
        storage: IdentityStorage | None = None,
    ) -> None:
        """
        Inicializa el motor de relaciones.

        Parámetros:
            people_manager:
                Gestor utilizado para resolver personas
                y animales.

            storage:
                Almacenamiento utilizado para guardar relaciones.

                Si no se proporciona, se reutiliza el almacenamiento
                de PeopleManager.
        """

        if not isinstance(
            people_manager,
            PeopleManager,
        ):

            raise TypeError(
                "people_manager debe ser una instancia "
                "de PeopleManager."
            )

        self.people_manager = (
            people_manager
        )

        self.storage = (
            storage
            if storage is not None
            else people_manager.storage
        )

        info(
            "RelationshipEngine inicializado."
        )

    # =========================================================================
    # RESOLUCIÓN DE ENTIDADES
    # =========================================================================

    def _resolve_entity_by_id(
        self,
        entity_id: str,
        entity_type: str,
    ) -> Person | Animal | None:
        """
        Busca una entidad utilizando su ID y tipo.
        """

        if not is_valid_entity_type(
            entity_type
        ):

            raise ValueError(
                "Tipo de entidad no válido: "
                f"{entity_type}"
            )

        if entity_type == PERSON_ENTITY:

            return self.people_manager.get_person_by_id(
                entity_id
            )

        return self.people_manager.get_animal_by_id(
            entity_id
        )

    def entity_exists(
        self,
        entity_id: str,
        entity_type: str,
    ) -> bool:
        """
        Indica si una entidad existe.
        """

        return (
            self._resolve_entity_by_id(
                entity_id=entity_id,
                entity_type=entity_type,
            )
            is not None
        )

    def resolve_entity_reference(
        self,
        value: str,
        preferred_type: str | None = None,
    ) -> tuple[str, Person | Animal] | None:
        """
        Resuelve una referencia por nombre, alias o ID.

        Este método delega en PeopleManager.
        """

        return self.people_manager.resolve_entity(
            value=value,
            preferred_type=preferred_type,
        )

    # =========================================================================
    # CONSULTA DE RELACIONES
    # =========================================================================

    def get_relationships(
        self,
    ) -> list[Relationship]:
        """
        Devuelve todas las relaciones almacenadas.
        """

        return self.storage.load_relationships()

    def get_relationship_count(
        self,
    ) -> int:
        """
        Devuelve el número total de relaciones.
        """

        return len(
            self.get_relationships()
        )

    def get_relationship_by_id(
        self,
        relationship_id: str,
    ) -> Relationship | None:
        """
        Busca una relación por su identificador.
        """

        return self.storage.get_relationship_by_id(
            relationship_id
        )

    def find_exact_relationship(
        self,
        *,
        source_entity_id: str,
        source_entity_type: str,
        relationship_type: str,
        target_entity_id: str,
        target_entity_type: str,
    ) -> Relationship | None:
        """
        Busca una relación estructuralmente idéntica.
        """

        for relationship in self.get_relationships():

            if relationship.matches(
                source_entity_id=source_entity_id,
                source_entity_type=source_entity_type,
                relationship_type=relationship_type,
                target_entity_id=target_entity_id,
                target_entity_type=target_entity_type,
            ):

                return relationship

        return None

    def relationship_exists(
        self,
        *,
        source_entity_id: str,
        source_entity_type: str,
        relationship_type: str,
        target_entity_id: str,
        target_entity_type: str,
    ) -> bool:
        """
        Indica si una relación ya existe.
        """

        return (
            self.find_exact_relationship(
                source_entity_id=source_entity_id,
                source_entity_type=source_entity_type,
                relationship_type=relationship_type,
                target_entity_id=target_entity_id,
                target_entity_type=target_entity_type,
            )
            is not None
        )

    def get_relationships_for_entity(
        self,
        entity_id: str,
        entity_type: str,
    ) -> list[Relationship]:
        """
        Devuelve todas las relaciones en las que participa
        una entidad.
        """

        if not is_valid_entity_type(
            entity_type
        ):

            raise ValueError(
                "Tipo de entidad no válido: "
                f"{entity_type}"
            )

        return [
            relationship
            for relationship in self.get_relationships()
            if relationship.involves_entity(
                entity_id=entity_id,
                entity_type=entity_type,
            )
        ]

    def get_outgoing_relationships(
        self,
        entity_id: str,
        entity_type: str,
        relationship_type: str | None = None,
    ) -> list[Relationship]:
        """
        Devuelve las relaciones donde la entidad
        aparece como origen.
        """

        relationships = [
            relationship
            for relationship in self.get_relationships()
            if (
                relationship.source_entity_id.casefold()
                == entity_id.strip().casefold()

                and relationship.source_entity_type
                == entity_type
            )
        ]

        if relationship_type is None:

            return relationships

        return [
            relationship
            for relationship in relationships
            if relationship.relationship_type
            == relationship_type
        ]

    def get_incoming_relationships(
        self,
        entity_id: str,
        entity_type: str,
        relationship_type: str | None = None,
    ) -> list[Relationship]:
        """
        Devuelve las relaciones donde la entidad
        aparece como destino.
        """

        relationships = [
            relationship
            for relationship in self.get_relationships()
            if (
                relationship.target_entity_id.casefold()
                == entity_id.strip().casefold()

                and relationship.target_entity_type
                == entity_type
            )
        ]

        if relationship_type is None:

            return relationships

        return [
            relationship
            for relationship in relationships
            if relationship.relationship_type
            == relationship_type
        ]

    def get_related_entities(
        self,
        entity_id: str,
        entity_type: str,
        relationship_type: str | None = None,
    ) -> list[
        tuple[
            Relationship,
            str,
            Person | Animal,
        ]
    ]:
        """
        Devuelve las entidades relacionadas con una entidad.

        Cada resultado contiene:

            (
                relación,
                tipo de la entidad relacionada,
                entidad relacionada
            )
        """

        results = []

        for relationship in self.get_relationships_for_entity(
            entity_id=entity_id,
            entity_type=entity_type,
        ):

            source_matches = (
                relationship.source_entity_id.casefold()
                == entity_id.strip().casefold()

                and relationship.source_entity_type
                == entity_type
            )

            if source_matches:

                related_entity_id = (
                    relationship.target_entity_id
                )

                related_entity_type = (
                    relationship.target_entity_type
                )

            else:

                related_entity_id = (
                    relationship.source_entity_id
                )

                related_entity_type = (
                    relationship.source_entity_type
                )

            if (
                relationship_type is not None
                and relationship.relationship_type
                != relationship_type
            ):

                continue

            related_entity = self._resolve_entity_by_id(
                entity_id=related_entity_id,
                entity_type=related_entity_type,
            )

            if related_entity is None:
                continue

            results.append(
                (
                    relationship,
                    related_entity_type,
                    related_entity,
                )
            )

        return results

    # =========================================================================
    # CREACIÓN DE RELACIONES
    # =========================================================================

    def create_relationship(
        self,
        *,
        source_entity_id: str,
        source_entity_type: str,
        relationship_type: str,
        target_entity_id: str,
        target_entity_type: str,
        confirmed: bool = False,
        information_source: str = "user",
        registered_by: str | None = None,
        confidence: float = 1.0,
        notes: str = "",
        create_inverse: bool = True,
    ) -> tuple[
        Relationship | None,
        Relationship | None,
    ]:
        """
        Crea una relación validada.

        Parámetros:
            source_entity_id:
                ID de la entidad de origen.

            source_entity_type:
                Tipo de la entidad de origen.

            relationship_type:
                Tipo de relación.

            target_entity_id:
                ID de la entidad de destino.

            target_entity_type:
                Tipo de la entidad de destino.

            confirmed:
                Indica si la relación está confirmada.

            information_source:
                Origen de la información.

            registered_by:
                Persona o usuario que la registró.

            confidence:
                Nivel de confianza entre 0.0 y 1.0.

            notes:
                Notas adicionales.

            create_inverse:
                Si es True, intenta crear también
                la relación inversa.

        Devuelve:
            tuple:
                (
                    relación principal,
                    relación inversa
                )

                Alguno de los elementos puede ser None.
        """

        if not is_valid_entity_type(
            source_entity_type
        ):

            raise ValueError(
                "Tipo de entidad de origen no válido: "
                f"{source_entity_type}"
            )

        if not is_valid_entity_type(
            target_entity_type
        ):

            raise ValueError(
                "Tipo de entidad de destino no válido: "
                f"{target_entity_type}"
            )

        if not is_valid_relationship_type(
            relationship_type
        ):

            raise ValueError(
                "Tipo de relación no válido: "
                f"{relationship_type}"
            )

        source_entity = self._resolve_entity_by_id(
            entity_id=source_entity_id,
            entity_type=source_entity_type,
        )

        if source_entity is None:

            raise ValueError(
                "La entidad de origen no existe: "
                f"{source_entity_type}:{source_entity_id}"
            )

        target_entity = self._resolve_entity_by_id(
            entity_id=target_entity_id,
            entity_type=target_entity_type,
        )

        if target_entity is None:

            raise ValueError(
                "La entidad de destino no existe: "
                f"{target_entity_type}:{target_entity_id}"
            )

        existing_relationship = (
            self.find_exact_relationship(
                source_entity_id=source_entity_id,
                source_entity_type=source_entity_type,
                relationship_type=relationship_type,
                target_entity_id=target_entity_id,
                target_entity_type=target_entity_type,
            )
        )

        if existing_relationship is not None:

            info(
                "Relación existente reutilizada: "
                f"{source_entity.name} "
                f"--{relationship_type}--> "
                f"{target_entity.name}."
            )

            inverse_relationship = (
                self.find_inverse_for_relationship(
                    existing_relationship
                )
            )

            return (
                existing_relationship,
                inverse_relationship,
            )

        relationship = Relationship(
            source_entity_id=source_entity_id,
            source_entity_type=source_entity_type,
            relationship_type=relationship_type,
            target_entity_id=target_entity_id,
            target_entity_type=target_entity_type,
            confirmed=confirmed,
            information_source=information_source,
            registered_by=registered_by,
            confidence=confidence,
            notes=notes,
        )

        saved = self.storage.add_relationship(
            relationship
        )

        if not saved:

            return (
                None,
                None,
            )

        info(
            f"Relación creada: "
            f"{source_entity.name} "
            f"--{relationship_type}--> "
            f"{target_entity.name}."
        )

        inverse_relationship = None

        if create_inverse:

            inverse_relationship = (
                self.create_inverse_relationship(
                    relationship
                )
            )

        return (
            relationship,
            inverse_relationship,
        )

    def create_relationship_by_name(
        self,
        *,
        source: str,
        relationship_type: str,
        target: str,
        source_type: str | None = None,
        target_type: str | None = None,
        confirmed: bool = False,
        information_source: str = "user",
        registered_by: str | None = None,
        confidence: float = 1.0,
        notes: str = "",
        create_inverse: bool = True,
    ) -> tuple[
        Relationship | None,
        Relationship | None,
    ]:
        """
        Crea una relación utilizando nombres, alias o IDs.
        """

        resolved_source = (
            self.resolve_entity_reference(
                value=source,
                preferred_type=source_type,
            )
        )

        if resolved_source is None:

            raise ValueError(
                f"No se ha encontrado la entidad «{source}»."
            )

        resolved_target = (
            self.resolve_entity_reference(
                value=target,
                preferred_type=target_type,
            )
        )

        if resolved_target is None:

            raise ValueError(
                f"No se ha encontrado la entidad «{target}»."
            )

        resolved_source_type, source_entity = (
            resolved_source
        )

        resolved_target_type, target_entity = (
            resolved_target
        )

        return self.create_relationship(
            source_entity_id=source_entity.id,
            source_entity_type=resolved_source_type,
            relationship_type=relationship_type,
            target_entity_id=target_entity.id,
            target_entity_type=resolved_target_type,
            confirmed=confirmed,
            information_source=information_source,
            registered_by=registered_by,
            confidence=confidence,
            notes=notes,
            create_inverse=create_inverse,
        )

    # =========================================================================
    # RELACIONES INVERSAS
    # =========================================================================

    def _resolve_inverse_relationship_type(
        self,
        relationship: Relationship,
    ) -> str | None:
        """
        Determina el tipo inverso más concreto posible.

        Para relaciones dependientes del género, consulta
        la entidad que pasará a ser el origen de la inversa.
        """

        generic_inverse = (
            get_inverse_relationship_type(
                relationship.relationship_type
            )
        )

        if generic_inverse is None:
            return None

        inverse_source = (
            self._resolve_entity_by_id(
                entity_id=(
                    relationship.target_entity_id
                ),
                entity_type=(
                    relationship.target_entity_type
                ),
            )
        )

        if not isinstance(
            inverse_source,
            Person,
        ):

            return generic_inverse

        gender = (
            inverse_source.grammatical_gender
        )

        # ---------------------------------------------------------------------
        # PADRES E HIJOS
        # ---------------------------------------------------------------------

        if generic_inverse == CHILD:

            if gender == "feminine":
                return DAUGHTER

            if gender == "masculine":
                return SON

            return CHILD

        if generic_inverse == PARENT:

            if gender == "feminine":
                return MOTHER

            if gender == "masculine":
                return FATHER

            return PARENT

        # ---------------------------------------------------------------------
        # HERMANOS
        # ---------------------------------------------------------------------

        if generic_inverse == SIBLING:

            if gender == "feminine":
                return SISTER

            if gender == "masculine":
                return BROTHER

            return SIBLING

        # ---------------------------------------------------------------------
        # ABUELOS Y NIETOS
        # ---------------------------------------------------------------------

        if generic_inverse == GRANDCHILD:

            if gender == "feminine":
                return GRANDDAUGHTER

            if gender == "masculine":
                return GRANDSON

            return GRANDCHILD

        if generic_inverse == GRANDPARENT:

            if gender == "feminine":
                return GRANDMOTHER

            if gender == "masculine":
                return GRANDFATHER

            return GRANDPARENT

        # ---------------------------------------------------------------------
        # TÍOS Y SOBRINOS
        # ---------------------------------------------------------------------

        if generic_inverse in {
            NIECE,
            NEPHEW,
        }:

            if gender == "feminine":
                return NIECE

            if gender == "masculine":
                return NEPHEW

        if generic_inverse in {
            AUNT,
            UNCLE,
        }:

            if gender == "feminine":
                return AUNT

            if gender == "masculine":
                return UNCLE

        return generic_inverse

    def create_inverse_relationship(
        self,
        relationship: Relationship,
    ) -> Relationship | None:
        """
        Crea y guarda la relación inversa.

        Si ya existe, devuelve la existente.
        """

        inverse_type = (
            self._resolve_inverse_relationship_type(
                relationship
            )
        )

        if inverse_type is None:

            info(
                "No se ha creado relación inversa porque "
                f"no existe una definición para "
                f"{relationship.relationship_type}."
            )

            return None

        existing_inverse = (
            self.find_exact_relationship(
                source_entity_id=(
                    relationship.target_entity_id
                ),
                source_entity_type=(
                    relationship.target_entity_type
                ),
                relationship_type=(
                    inverse_type
                ),
                target_entity_id=(
                    relationship.source_entity_id
                ),
                target_entity_type=(
                    relationship.source_entity_type
                ),
            )
        )

        if existing_inverse is not None:

            return existing_inverse

        inverse_relationship = (
            relationship.create_inverse(
                inverse_relationship_type=(
                    inverse_type
                )
            )
        )

        saved = self.storage.add_relationship(
            inverse_relationship
        )

        if not saved:
            return None

        info(
            "Relación inversa creada: "
            f"{inverse_relationship.source_entity_id} "
            f"--{inverse_relationship.relationship_type}--> "
            f"{inverse_relationship.target_entity_id}."
        )

        return inverse_relationship

    def find_inverse_for_relationship(
        self,
        relationship: Relationship,
    ) -> Relationship | None:
        """
        Busca la relación inversa de una relación existente.
        """

        inverse_type = (
            self._resolve_inverse_relationship_type(
                relationship
            )
        )

        if inverse_type is None:
            return None

        return self.find_exact_relationship(
            source_entity_id=(
                relationship.target_entity_id
            ),
            source_entity_type=(
                relationship.target_entity_type
            ),
            relationship_type=(
                inverse_type
            ),
            target_entity_id=(
                relationship.source_entity_id
            ),
            target_entity_type=(
                relationship.source_entity_type
            ),
        )

    # =========================================================================
    # ACTUALIZACIÓN
    # =========================================================================

    def confirm_relationship(
        self,
        relationship_id: str,
        registered_by: str | None = None,
        confirm_inverse: bool = True,
    ) -> bool:
        """
        Confirma una relación y opcionalmente su inversa.
        """

        relationship = self.get_relationship_by_id(
            relationship_id
        )

        if relationship is None:
            return False

        relationship.confirm(
            registered_by=registered_by
        )

        if not self.storage.update_relationship(
            relationship
        ):

            return False

        if confirm_inverse:

            inverse = (
                self.find_inverse_for_relationship(
                    relationship
                )
            )

            if inverse is not None:

                inverse.confirm(
                    registered_by=registered_by
                )

                self.storage.update_relationship(
                    inverse
                )

        return True

    def update_relationship_notes(
        self,
        relationship_id: str,
        notes: str,
    ) -> bool:
        """
        Actualiza las notas de una relación.
        """

        relationship = self.get_relationship_by_id(
            relationship_id
        )

        if relationship is None:
            return False

        relationship.update_notes(
            notes
        )

        return self.storage.update_relationship(
            relationship
        )

    def update_relationship_confidence(
        self,
        relationship_id: str,
        confidence: float,
        update_inverse: bool = True,
    ) -> bool:
        """
        Actualiza la confianza de una relación.
        """

        relationship = self.get_relationship_by_id(
            relationship_id
        )

        if relationship is None:
            return False

        relationship.update_confidence(
            confidence
        )

        if not self.storage.update_relationship(
            relationship
        ):

            return False

        if update_inverse:

            inverse = (
                self.find_inverse_for_relationship(
                    relationship
                )
            )

            if inverse is not None:

                inverse.update_confidence(
                    confidence
                )

                self.storage.update_relationship(
                    inverse
                )

        return True

    # =========================================================================
    # ELIMINACIÓN
    # =========================================================================

    def delete_relationship(
        self,
        relationship_id: str,
        delete_inverse: bool = True,
    ) -> bool:
        """
        Elimina una relación.

        Si delete_inverse es True, también elimina
        su relación inversa.
        """

        relationship = self.get_relationship_by_id(
            relationship_id
        )

        if relationship is None:
            return False

        inverse = None

        if delete_inverse:

            inverse = (
                self.find_inverse_for_relationship(
                    relationship
                )
            )

        deleted = (
            self.storage.delete_relationship(
                relationship.id
            )
        )

        if not deleted:
            return False

        if inverse is not None:

            self.storage.delete_relationship(
                inverse.id
            )

        info(
            f"Relación eliminada desde RelationshipEngine: "
            f"{relationship.id}."
        )

        return True

    # =========================================================================
    # DESCRIPCIÓN
    # =========================================================================

    def describe_relationship(
        self,
        relationship: Relationship,
    ) -> str:
        """
        Devuelve una descripción legible de una relación.
        """

        source_entity = (
            self._resolve_entity_by_id(
                entity_id=(
                    relationship.source_entity_id
                ),
                entity_type=(
                    relationship.source_entity_type
                ),
            )
        )

        target_entity = (
            self._resolve_entity_by_id(
                entity_id=(
                    relationship.target_entity_id
                ),
                entity_type=(
                    relationship.target_entity_type
                ),
            )
        )

        source_name = (
            source_entity.name
            if source_entity is not None
            else relationship.source_entity_id
        )

        target_name = (
            target_entity.name
            if target_entity is not None
            else relationship.target_entity_id
        )

        public_pair = frozenset({source_name, target_name})
        if public_pair in self._PUBLIC_COUSIN_ONLY_NAMES:
            return f"{source_name} y {target_name} son primos."

        label = get_relationship_label(
            relationship.relationship_type
        )

        description = (
            f"{source_name} es {label} de "
            f"{target_name}."
        )

        notes = str(
            getattr(relationship, "notes", "") or ""
        ).strip()

        # Las notas que solo documentan la creación automática de
        # la relación inversa no aportan información familiar.
        # Las demás sí son esenciales para distinguir vínculos
        # biológicos, legales, adoptivos y afectivos que pueden
        # coexistir sin ser contradictorios.
        if (
            notes
            and not notes.casefold().startswith(
                "relación inversa generada"
            )
        ):
            description += f" Detalle verificado: {notes}"

        return description

    def describe_relationships_for_entity(
        self,
        entity_id: str,
        entity_type: str,
    ) -> list[str]:
        """
        Devuelve descripciones de todas las relaciones
        de una entidad.
        """

        descriptions: list[str] = []

        for relationship in self.get_relationships_for_entity(
            entity_id=entity_id,
            entity_type=entity_type,
        ):
            description = self.describe_relationship(relationship)
            if description not in descriptions:
                descriptions.append(description)

        return descriptions



    # =========================================================================
    # RESOLUCIÓN GENERAL DE PARENTESCOS
    # =========================================================================

    @staticmethod
    def _entity_gender(entity: Person | Animal | None) -> str:
        """Devuelve el género gramatical conocido de una entidad."""

        return str(
            getattr(entity, "grammatical_gender", "") or ""
        ).strip().casefold()

    @classmethod
    def _gendered_label(
        cls,
        masculine: str,
        feminine: str,
        entity: Person | Animal | None,
        neutral: str | None = None,
    ) -> str:
        """Elige una etiqueta familiar según el género de la entidad origen."""

        gender = cls._entity_gender(entity)
        if gender == "feminine":
            return feminine
        if gender == "masculine":
            return masculine
        return neutral or f"{masculine} o {feminine}"

    @staticmethod
    def _other_endpoint(
        relationship: Relationship,
        entity_id: str,
        entity_type: str,
    ) -> tuple[str, str] | None:
        """Devuelve el extremo opuesto de una relación."""

        key = entity_id.strip().casefold()
        if (
            relationship.source_entity_id.casefold() == key
            and relationship.source_entity_type == entity_type
        ):
            return (
                relationship.target_entity_id,
                relationship.target_entity_type,
            )
        if (
            relationship.target_entity_id.casefold() == key
            and relationship.target_entity_type == entity_type
        ):
            return (
                relationship.source_entity_id,
                relationship.source_entity_type,
            )
        return None

    def find_shortest_relationship_path(
        self,
        source_entity_id: str,
        source_entity_type: str,
        target_entity_id: str,
        target_entity_type: str,
        max_depth: int = 4,
    ) -> list[Relationship]:
        """
        Busca el camino relacional más corto entre dos entidades.

        El recorrido incluye personas y animales, evita ciclos y no crea
        relaciones nuevas. Se limita por defecto a cuatro pasos para impedir
        deducciones remotas o poco fiables.
        """

        source_key = (
            source_entity_type,
            source_entity_id.strip().casefold(),
        )
        target_key = (
            target_entity_type,
            target_entity_id.strip().casefold(),
        )

        if source_key == target_key:
            return []

        queue: list[tuple[str, str, list[Relationship]]] = [
            (source_entity_id, source_entity_type, [])
        ]
        visited = {source_key}

        while queue:
            current_id, current_type, path = queue.pop(0)
            if len(path) >= max_depth:
                continue

            for relationship in self.get_relationships_for_entity(
                entity_id=current_id,
                entity_type=current_type,
            ):
                endpoint = self._other_endpoint(
                    relationship,
                    current_id,
                    current_type,
                )
                if endpoint is None:
                    continue

                next_id, next_type = endpoint
                next_key = (next_type, next_id.casefold())
                next_path = [*path, relationship]

                if next_key == target_key:
                    return next_path

                if next_key in visited:
                    continue

                visited.add(next_key)
                queue.append((next_id, next_type, next_path))

        return []

    def _oriented_relationship_type(
        self,
        relationship: Relationship,
        source_entity_id: str,
        source_entity_type: str,
    ) -> str | None:
        """
        Devuelve el tipo de relación visto desde la entidad indicada.

        Normalmente el almacenamiento ya contiene la relación inversa, pero
        este método también funciona si únicamente existe uno de los sentidos.
        """

        source_matches = (
            relationship.source_entity_id.casefold()
            == source_entity_id.strip().casefold()
            and relationship.source_entity_type == source_entity_type
        )
        if source_matches:
            return relationship.relationship_type

        target_matches = (
            relationship.target_entity_id.casefold()
            == source_entity_id.strip().casefold()
            and relationship.target_entity_type == source_entity_type
        )
        if not target_matches:
            return None

        return get_inverse_relationship_type(
            relationship.relationship_type
        )

    def _compose_two_step_kinship(
        self,
        first_type: str,
        second_type: str,
        source_entity: Person | Animal | None,
    ) -> str | None:
        """Compone parentescos familiares seguros de exactamente dos pasos."""

        parent_types = {MOTHER, FATHER, PARENT}
        child_types = {DAUGHTER, SON, CHILD}
        sibling_types = {SISTER, BROTHER, SIBLING}
        partner_types = {PARTNER, SPOUSE}

        if first_type in parent_types and second_type in parent_types:
            return self._gendered_label(
                "abuelo", "abuela", source_entity, "abuelo o abuela"
            )

        if first_type in child_types and second_type in child_types:
            return self._gendered_label(
                "nieto", "nieta", source_entity, "nieto o nieta"
            )

        if first_type in sibling_types and second_type in parent_types:
            return self._gendered_label(
                "tío", "tía", source_entity, "tío o tía"
            )

        if first_type in child_types and second_type in sibling_types:
            return self._gendered_label(
                "sobrino", "sobrina", source_entity, "sobrino o sobrina"
            )

        if (
            first_type in child_types
            and second_type in {AUNT, UNCLE}
        ):
            return self._gendered_label(
                "primo", "prima", source_entity, "primo o prima"
            )

        # Pareja + hermano/a y hermano/a + pareja producen cuñados.
        if (
            first_type in partner_types
            and second_type in sibling_types
        ) or (
            first_type in sibling_types
            and second_type in partner_types
        ):
            return self._gendered_label(
                "cuñado", "cuñada", source_entity, "cuñado o cuñada"
            )

        # Pareja de un hijo/a respecto de sus padres.
        if (
            first_type in partner_types
            and second_type in child_types
        ):
            return self._gendered_label(
                "yerno", "nuera", source_entity, "yerno o nuera"
            )

        # Padre/madre de la pareja respecto de la otra persona.
        if (
            first_type in parent_types
            and second_type in partner_types
        ):
            return self._gendered_label(
                "suegro", "suegra", source_entity, "suegro o suegra"
            )

        return None

    def infer_relationship_label(
        self,
        source_entity_id: str,
        source_entity_type: str,
        target_entity_id: str,
        target_entity_type: str,
    ) -> str | None:
        """
        Devuelve el parentesco o vínculo más específico que puede demostrarse.

        Prioriza relaciones directas. Si no existen, compone reglas familiares
        seguras de dos pasos. Para conexiones más largas devuelve ``None`` y
        la capa superior puede describir el camino sin inventar una etiqueta.
        """

        source_entity = self._resolve_entity_by_id(
            source_entity_id,
            source_entity_type,
        )
        target_entity = self._resolve_entity_by_id(
            target_entity_id,
            target_entity_type,
        )
        if source_entity is None or target_entity is None:
            return None

        public_pair = frozenset({
            source_entity.name,
            target_entity.name,
        })
        if public_pair in self._PUBLIC_COUSIN_ONLY_NAMES:
            return self._gendered_label(
                "primo", "prima", source_entity, "primo o prima"
            )

        direct = []
        for relationship in self.get_relationships_for_entity(
            entity_id=source_entity_id,
            entity_type=source_entity_type,
        ):
            endpoint = self._other_endpoint(
                relationship,
                source_entity_id,
                source_entity_type,
            )
            if endpoint is None:
                continue
            other_id, other_type = endpoint
            if (
                other_id.casefold() == target_entity_id.strip().casefold()
                and other_type == target_entity_type
            ):
                direct_type = self._oriented_relationship_type(
                    relationship,
                    source_entity_id,
                    source_entity_type,
                )
                if direct_type:
                    direct.append(direct_type)

        if direct:
            # La política pública de primos ya se ha aplicado arriba.
            preferred_order = (
                PARTNER, SPOUSE, MOTHER, FATHER, PARENT,
                DAUGHTER, SON, CHILD, SISTER, BROTHER, SIBLING,
                GRANDMOTHER, GRANDFATHER, GRANDPARENT,
                GRANDDAUGHTER, GRANDSON, GRANDCHILD,
                AUNT, UNCLE, NIECE, NEPHEW, COUSIN,
                PET_OWNER, PET_OF, CARES_FOR, CARED_FOR_BY,
                LIVES_WITH, ANIMAL_COMPANION,
            )
            for relationship_type in preferred_order:
                if relationship_type not in direct:
                    continue
                if relationship_type == COUSIN:
                    return self._gendered_label(
                        "primo", "prima", source_entity, "primo o prima"
                    )
                return get_relationship_label(relationship_type)
            return get_relationship_label(direct[0])

        path = self.find_shortest_relationship_path(
            source_entity_id,
            source_entity_type,
            target_entity_id,
            target_entity_type,
            max_depth=2,
        )
        if len(path) != 2:
            return None

        first_type = self._oriented_relationship_type(
            path[0],
            source_entity_id,
            source_entity_type,
        )
        first_endpoint = self._other_endpoint(
            path[0],
            source_entity_id,
            source_entity_type,
        )
        if first_type is None or first_endpoint is None:
            return None

        middle_id, middle_type = first_endpoint
        second_type = self._oriented_relationship_type(
            path[1],
            middle_id,
            middle_type,
        )
        if second_type is None:
            return None

        return self._compose_two_step_kinship(
            first_type,
            second_type,
            source_entity,
        )

    def describe_relationship_between_entities(
        self,
        source_entity_id: str,
        source_entity_type: str,
        target_entity_id: str,
        target_entity_type: str,
    ) -> str:
        """
        Describe de forma segura la relación entre dos entidades cualesquiera.

        Si existe un parentesco directo o compuesto conocido lo nombra. En los
        demás casos describe el camino verificable y evita asignar parentescos
        no demostrados. También admite conexiones entre personas y animales.
        """

        source = self._resolve_entity_by_id(
            source_entity_id,
            source_entity_type,
        )
        target = self._resolve_entity_by_id(
            target_entity_id,
            target_entity_type,
        )
        if source is None or target is None:
            return ""

        label = self.infer_relationship_label(
            source_entity_id,
            source_entity_type,
            target_entity_id,
            target_entity_type,
        )
        if label:
            return f"{source.name} es {label} de {target.name}."

        path = self.find_shortest_relationship_path(
            source_entity_id,
            source_entity_type,
            target_entity_id,
            target_entity_type,
        )
        if not path:
            return (
                f"No hay un parentesco o vínculo verificado entre "
                f"{source.name} y {target.name}."
            )

        steps = []
        current_id = source_entity_id
        current_type = source_entity_type
        for relationship in path:
            endpoint = self._other_endpoint(
                relationship,
                current_id,
                current_type,
            )
            if endpoint is None:
                break
            next_id, next_type = endpoint
            current_entity = self._resolve_entity_by_id(
                current_id,
                current_type,
            )
            next_entity = self._resolve_entity_by_id(
                next_id,
                next_type,
            )
            oriented_type = self._oriented_relationship_type(
                relationship,
                current_id,
                current_type,
            )
            if (
                current_entity is not None
                and next_entity is not None
                and oriented_type is not None
            ):
                steps.append(
                    f"{current_entity.name} es "
                    f"{get_relationship_label(oriented_type)} de "
                    f"{next_entity.name}"
                )
            current_id, current_type = next_id, next_type

        if not steps:
            return ""

        return (
            f"{source.name} está relacionado con {target.name} "
            f"mediante esta cadena verificada: "
            + "; ".join(steps)
            + "."
        )

    # =========================================================================
    # DEDUCCIONES SENCILLAS
    # =========================================================================

    def find_two_step_connections(
        self,
        source_entity_id: str,
        source_entity_type: str,
        target_entity_id: str,
        target_entity_type: str,
    ) -> list[
        tuple[
            Relationship,
            Relationship,
        ]
    ]:
        """
        Busca conexiones formadas por exactamente dos relaciones.

        Ejemplo:

            Liam --partner--> Saray
            Saray --sister--> Rubén

        permite localizar el camino:

            Liam -> Saray -> Rubén

        Este método no crea relaciones nuevas.
        Solo devuelve caminos existentes.
        """

        first_step_relationships = (
            self.get_outgoing_relationships(
                entity_id=source_entity_id,
                entity_type=source_entity_type,
            )
        )

        connections = []

        for first_relationship in (
            first_step_relationships
        ):

            second_step_relationships = (
                self.get_outgoing_relationships(
                    entity_id=(
                        first_relationship.target_entity_id
                    ),
                    entity_type=(
                        first_relationship.target_entity_type
                    ),
                )
            )

            for second_relationship in (
                second_step_relationships
            ):

                target_matches = (
                    second_relationship.target_entity_id.casefold()
                    == target_entity_id.strip().casefold()

                    and second_relationship.target_entity_type
                    == target_entity_type
                )

                if target_matches:

                    connections.append(
                        (
                            first_relationship,
                            second_relationship,
                        )
                    )

        return connections

    def describe_two_step_connection(
        self,
        first_relationship: Relationship,
        second_relationship: Relationship,
    ) -> str:
        """
        Describe una conexión indirecta de dos pasos.

        Ejemplo:

            Liam es pareja de Saray.
            Saray es hermana de Rubén.

        Resultado:

            Rubén está relacionado con Liam a través de Saray:
            Saray es pareja de Liam y hermana de Rubén.

        En esta primera versión se prioriza claridad
        sobre naturalidad lingüística perfecta.
        """

        first_source = self._resolve_entity_by_id(
            entity_id=(
                first_relationship.source_entity_id
            ),
            entity_type=(
                first_relationship.source_entity_type
            ),
        )

        middle_entity = self._resolve_entity_by_id(
            entity_id=(
                first_relationship.target_entity_id
            ),
            entity_type=(
                first_relationship.target_entity_type
            ),
        )

        final_entity = self._resolve_entity_by_id(
            entity_id=(
                second_relationship.target_entity_id
            ),
            entity_type=(
                second_relationship.target_entity_type
            ),
        )

        first_source_name = (
            first_source.name
            if first_source is not None
            else first_relationship.source_entity_id
        )

        middle_name = (
            middle_entity.name
            if middle_entity is not None
            else first_relationship.target_entity_id
        )

        final_name = (
            final_entity.name
            if final_entity is not None
            else second_relationship.target_entity_id
        )

        first_label = get_relationship_label(
            first_relationship.relationship_type
        )

        second_label = get_relationship_label(
            second_relationship.relationship_type
        )

        return (
            f"{final_name} está relacionado con "
            f"{first_source_name} a través de "
            f"{middle_name}: "
            f"{first_source_name} es {first_label} de "
            f"{middle_name}, y {middle_name} es "
            f"{second_label} de {final_name}."
        )
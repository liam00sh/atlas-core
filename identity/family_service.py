"""
===============================================================================
Proyecto Atlas
Archivo: identity/family_service.py

Descripción:
    Ofrece operaciones de consulta sobre personas, parentescos, convivencia y
    animales.

    Este servicio utiliza ``PeopleManager`` y ``RelationshipEngine`` como
    fuentes de verdad. No lee ni escribe directamente los archivos JSON.
===============================================================================
"""


from identity.people_manager import PeopleManager
from identity.relationship import Relationship
from identity.relationship_engine import RelationshipEngine


class FamilyService:
    """Servicio de consultas familiares de alto nivel."""

    def __init__(
        self,
        people_manager: PeopleManager,
        relationship_engine: RelationshipEngine,
    ) -> None:
        """Inicializa el servicio familiar."""

        if not isinstance(
            people_manager,
            PeopleManager,
        ):

            raise TypeError(
                "people_manager debe ser una instancia "
                "de PeopleManager."
            )

        if not isinstance(
            relationship_engine,
            RelationshipEngine,
        ):

            raise TypeError(
                "relationship_engine debe ser una instancia "
                "de RelationshipEngine."
            )

        self.people_manager = people_manager
        self.relationship_engine = relationship_engine

    def describe_person_family(
        self,
        person_name: str,
    ) -> str:
        """
        Devuelve una descripción de las relaciones directas de una persona.

        Cuando el nombre o alias coincide con varias personas, devuelve una
        petición de aclaración en lugar de seleccionar arbitrariamente la
        primera coincidencia.
        """

        clean_name = str(
            person_name
        ).strip()

        if not clean_name:
            return "No se ha indicado ninguna persona."

        matches = self.people_manager.find_people_by_name(
            clean_name
        )

        if len(matches) > 1:

            options = ", ".join(
                person.name
                for person in matches
            )

            return (
                f"La referencia «{clean_name}» es ambigua. "
                f"Puede referirse a: {options}."
            )

        if len(matches) == 1:
            person = matches[0]

        else:

            person = self.people_manager.get_person_by_id(
                clean_name
            )

        if person is None:

            return (
                f"No conozco a ninguna persona llamada "
                f"«{clean_name}»."
            )

        descriptions = (
            self.relationship_engine
            .describe_relationships_for_entity(
                entity_id=person.id,
                entity_type="person",
            )
        )

        if not descriptions:
            return (
                f"No tengo relaciones registradas para "
                f"{person.name}."
            )

        return "\n".join(descriptions)

    def find_connection(
        self,
        source_name: str,
        target_name: str,
    ) -> list[
        tuple[
            Relationship,
            Relationship,
        ]
    ]:
        """
        Busca conexiones de exactamente dos pasos entre dos personas.

        Si alguno de los nombres no existe o es ambiguo, devuelve una lista
        vacía. La presentación de preguntas de aclaración corresponde a la
        capa de conversación.
        """

        source_matches = (
            self.people_manager
            .find_people_by_name(
                source_name
            )
        )

        target_matches = (
            self.people_manager
            .find_people_by_name(
                target_name
            )
        )

        if (
            len(source_matches) != 1
            or len(target_matches) != 1
        ):
            return []

        source_entity = source_matches[0]
        target_entity = target_matches[0]

        return (
            self.relationship_engine
            .find_two_step_connections(
                source_entity_id=source_entity.id,
                source_entity_type="person",
                target_entity_id=target_entity.id,
                target_entity_type="person",
            )
        )

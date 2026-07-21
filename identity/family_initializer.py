"""
===============================================================================
Proyecto Atlas
Archivo: identity/family_initializer.py

Descripción:
    Inicializa las personas, animales y relaciones familiares declaradas en
    ``identity/family_data.py``.

    El inicializador es idempotente: puede ejecutarse varias veces sin crear
    duplicados. Cuando encuentra una entidad ya existente, intenta completar
    de forma segura sus alias, resumen, género gramatical y vínculo de usuario.
===============================================================================
"""


from core.log_manager import info

from identity.animal import Animal
from identity.family_data import FAMILY_ANIMALS
from identity.family_data import FAMILY_PEOPLE
from identity.family_data import FAMILY_RELATIONSHIPS
from identity.people_manager import PeopleManager
from identity.person import Person
from identity.relationship_engine import RelationshipEngine


class FamilyInitializer:
    """
    Registra y sincroniza la información familiar inicial de Atlas.
    """

    def __init__(
        self,
        people_manager: PeopleManager,
        relationship_engine: RelationshipEngine,
    ) -> None:
        """Inicializa el cargador familiar."""

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

    def initialize(
        self,
    ) -> dict[str, int]:
        """
        Crea o sincroniza todos los elementos familiares declarados.

        Las cantidades devueltas representan registros nuevos persistidos en
        esta ejecución. Las entidades reutilizadas o únicamente actualizadas
        no se contabilizan como nuevas.
        """

        self._remove_obsolete_people()
        created_people = self._initialize_people()
        created_animals = self._initialize_animals()
        self._remove_obsolete_relationships()
        created_relationships = self._initialize_relationships()

        result = {
            "created_people": created_people,
            "created_animals": created_animals,
            "created_relationships": created_relationships,
        }

        info(
            "Inicialización familiar completada. "
            f"Personas creadas: {created_people}. "
            f"Animales creados: {created_animals}. "
            f"Relaciones creadas: {created_relationships}."
        )

        return result

    def _find_existing_person(
        self,
        data: dict,
    ) -> Person | None:
        """Localiza una persona existente mediante perfil, nombre o alias."""

        user_profile = data.get(
            "user_profile"
        )

        if user_profile:

            person = (
                self.people_manager
                .find_person_by_user_profile(
                    user_profile
                )
            )

            if person is not None:
                return person

        person = self.people_manager.find_person_by_name(
            data["name"]
        )

        if person is not None:
            return person

        # Los alias solo se utilizan como ruta de migración para perfiles
        # de usuario. En personas sin cuenta pueden existir alias legítimos
        # repetidos —por ejemplo, dos familiares llamados «Pepi»— y no deben
        # provocar que dos registros distintos se fusionen.
        if not user_profile:
            return None

        matches: dict[str, Person] = {}

        for alias in data.get(
            "aliases",
            [],
        ):

            for candidate in (
                self.people_manager
                .find_people_by_name(
                    alias
                )
            ):

                matches[candidate.id] = candidate

        if len(matches) == 1:
            return next(iter(matches.values()))

        return None

    def _synchronize_person(
        self,
        person: Person,
        data: dict,
    ) -> None:
        """Completa de forma conservadora los datos de una persona."""

        desired_aliases = [
            data["name"],
            *data.get(
                "aliases",
                [],
            ),
        ]

        for alias in desired_aliases:

            if person.matches_name(
                alias
            ):
                continue

            self.people_manager.add_person_alias(
                person.id,
                alias,
            )

        # FAMILY_PEOPLE es la fuente declarativa oficial de estos perfiles.
        # Los alias corregidos o eliminados deben retirarse también del JSON
        # persistente; de lo contrario pueden resolver a la persona equivocada
        # y crear relaciones de una entidad consigo misma.
        desired_alias_keys = {
            alias.strip().casefold()
            for alias in data.get(
                "aliases",
                [],
            )
            if str(alias).strip()
        }

        aliases_changed = False

        for current_alias in list(
            person.aliases
        ):

            if (
                current_alias.strip().casefold()
                in desired_alias_keys
            ):
                continue

            if person.remove_alias(
                current_alias
            ):
                aliases_changed = True

        if aliases_changed:
            self.people_manager.save_person(
                person
            )

        grammatical_gender = data.get(
            "grammatical_gender",
            "unknown",
        )

        if (
            grammatical_gender != "unknown"
            and person.grammatical_gender
            != grammatical_gender
        ):

            self.people_manager.update_person_gender(
                person.id,
                grammatical_gender,
            )

        summary = data.get(
            "summary",
            "",
        ).strip()

        if summary and person.summary != summary:

            self.people_manager.update_person_summary(
                person.id,
                summary,
            )

        user_profile = data.get(
            "user_profile"
        )

        if (
            user_profile
            and person.user_profile != user_profile
        ):

            self.people_manager.link_person_to_user(
                person.id,
                user_profile,
            )

    def _remove_obsolete_people(
        self,
    ) -> int:
        """Elimina perfiles históricos sustituidos por nombres corregidos."""

        obsolete_names = {
            "Evaristo Maestre Esteve",
            "Fermina Pérez",
        }
        removed = 0

        for person in self.people_manager.get_people():
            if person.name not in obsolete_names:
                continue

            if self.people_manager.delete_person(
                person.id,
                delete_relationships=True,
            ):
                removed += 1

        return removed

    def _initialize_people(
        self,
    ) -> int:
        """Crea las personas ausentes y sincroniza las existentes."""

        created_count = 0

        for data in FAMILY_PEOPLE:

            existing_person = self._find_existing_person(
                data
            )

            if existing_person is not None:

                self._synchronize_person(
                    existing_person,
                    data,
                )

                continue

            user_profile = data.get(
                "user_profile"
            )

            if user_profile:

                person = (
                    self.people_manager
                    .create_user_person(
                        name=data["name"],
                        user_profile=user_profile,
                        aliases=data.get(
                            "aliases",
                            [],
                        ),
                        grammatical_gender=data.get(
                            "grammatical_gender",
                            "unknown",
                        ),
                        summary=data.get(
                            "summary",
                            "",
                        ),
                    )
                )

            else:

                person = (
                    self.people_manager
                    .create_person(
                        name=data["name"],
                        aliases=data.get(
                            "aliases",
                            [],
                        ),
                        grammatical_gender=data.get(
                            "grammatical_gender",
                            "unknown",
                        ),
                        summary=data.get(
                            "summary",
                            "",
                        ),
                    )
                )

            if person is not None:
                created_count += 1

        return created_count

    def _find_existing_animal(
        self,
        data: dict,
    ) -> Animal | None:
        """Localiza un animal existente mediante nombre o alias."""

        animal = self.people_manager.find_animal_by_name(
            data["name"]
        )

        if animal is not None:
            return animal

        matches: dict[str, Animal] = {}

        for alias in data.get(
            "aliases",
            [],
        ):

            for candidate in (
                self.people_manager
                .find_animals_by_name(
                    alias
                )
            ):

                matches[candidate.id] = candidate

        if len(matches) == 1:
            return next(iter(matches.values()))

        return None

    def _synchronize_animal(
        self,
        animal: Animal,
        data: dict,
    ) -> None:
        """Completa de forma conservadora los datos de un animal."""

        desired_aliases = [
            data["name"],
            *data.get(
                "aliases",
                [],
            ),
        ]

        for alias in desired_aliases:

            if animal.matches_name(
                alias
            ):
                continue

            self.people_manager.add_animal_alias(
                animal.id,
                alias,
            )

        # FAMILY_ANIMALS es la fuente declarativa oficial de estos animales.
        # Si un alias fue corregido o eliminado de family_data.py, también debe
        # desaparecer del registro persistente para evitar datos obsoletos.
        desired_alias_keys = {
            alias.strip().casefold()
            for alias in data.get(
                "aliases",
                [],
            )
            if str(alias).strip()
        }

        aliases_changed = False

        for current_alias in list(
            animal.aliases
        ):

            if (
                current_alias.strip().casefold()
                in desired_alias_keys
            ):
                continue

            if animal.remove_alias(
                current_alias
            ):
                aliases_changed = True

        if aliases_changed:
            self.people_manager.save_animal(
                animal
            )

        summary = data.get(
            "summary",
            "",
        ).strip()

        if summary and animal.summary != summary:

            self.people_manager.update_animal_summary(
                animal.id,
                summary,
            )

    def _initialize_animals(
        self,
    ) -> int:
        """Crea los animales ausentes y sincroniza los existentes."""

        created_count = 0

        for data in FAMILY_ANIMALS:

            existing_animal = self._find_existing_animal(
                data
            )

            if existing_animal is not None:

                self._synchronize_animal(
                    existing_animal,
                    data,
                )

                continue

            animal = (
                self.people_manager
                .create_animal(
                    name=data["name"],
                    species=data.get(
                        "species",
                        "unknown",
                    ),
                    aliases=data.get(
                        "aliases",
                        [],
                    ),
                    breed=data.get(
                        "breed"
                    ),
                    sex=data.get(
                        "sex",
                        "unknown",
                    ),
                    grammatical_gender=data.get(
                        "grammatical_gender",
                        "unknown",
                    ),
                    birth_date=data.get(
                        "birth_date"
                    ),
                    summary=data.get(
                        "summary",
                        "",
                    ),
                )
            )

            if animal is not None:
                created_count += 1

        return created_count

    def _remove_obsolete_relationships(
        self,
    ) -> int:
        """Elimina relaciones declarativas antiguas que ya fueron corregidas."""

        antonio = self.people_manager.find_person_by_name(
            "Antonio Carreres Hernández"
        )
        estrella = self.people_manager.find_animal_by_name(
            "Estrella"
        )

        if antonio is None or estrella is None:
            return 0

        removed = 0

        for relationship in list(
            self.relationship_engine.get_relationships()
        ):
            is_obsolete_direct = (
                relationship.source_entity_id == antonio.id
                and relationship.target_entity_id == estrella.id
                and relationship.relationship_type == "cares_for"
            )
            is_obsolete_inverse = (
                relationship.source_entity_id == estrella.id
                and relationship.target_entity_id == antonio.id
                and relationship.relationship_type == "cared_for_by"
            )

            if not (
                is_obsolete_direct
                or is_obsolete_inverse
            ):
                continue

            if self.relationship_engine.delete_relationship(
                relationship.id,
                delete_inverse=True,
            ):
                removed += 1

        return removed

    def _initialize_relationships(
        self,
    ) -> int:
        """
        Crea las relaciones ausentes y sus inversas.

        El conteo se calcula mediante la diferencia real de registros del
        almacenamiento. De esta forma, una segunda ejecución devuelve cero
        relaciones nuevas aunque el motor reutilice objetos existentes.
        """

        existing_relationships = (
            self.relationship_engine
            .get_relationships()
        )
        before_count = len(existing_relationships)
        existing_keys = {
            (
                item.source_entity_id,
                item.source_entity_type,
                item.relationship_type,
                item.target_entity_id,
                item.target_entity_type,
            )
            for item in existing_relationships
        }
        resolved: dict[tuple[str, str | None], tuple | None] = {}

        for data in FAMILY_RELATIONSHIPS:
            source_reference = (
                data["source"],
                data.get("source_type"),
            )
            target_reference = (
                data["target"],
                data.get("target_type"),
            )
            if source_reference not in resolved:
                resolved[source_reference] = (
                    self.relationship_engine.resolve_entity_reference(
                        value=source_reference[0],
                        preferred_type=source_reference[1],
                    )
                )
            if target_reference not in resolved:
                resolved[target_reference] = (
                    self.relationship_engine.resolve_entity_reference(
                        value=target_reference[0],
                        preferred_type=target_reference[1],
                    )
                )
            source = resolved[source_reference]
            target = resolved[target_reference]
            if source is None or target is None:
                # Conserva el mismo error descriptivo de la ruta anterior.
                self.relationship_engine.create_relationship_by_name(
                    source=data["source"],
                    source_type=data.get("source_type"),
                    relationship_type=data["relationship_type"],
                    target=data["target"],
                    target_type=data.get("target_type"),
                    confirmed=True,
                    information_source="user",
                    registered_by="Liam",
                    confidence=1.0,
                    notes=data.get("notes", ""),
                    create_inverse=True,
                )
                continue

            source_type, source_entity = source
            target_type, target_entity = target
            key = (
                source_entity.id,
                source_type,
                data["relationship_type"],
                target_entity.id,
                target_type,
            )
            if key in existing_keys:
                continue

            relationship, inverse = self.relationship_engine.create_relationship(
                source_entity_id=source_entity.id,
                source_entity_type=source_type,
                relationship_type=(
                    data["relationship_type"]
                ),
                target_entity_id=target_entity.id,
                target_entity_type=target_type,
                confirmed=True,
                information_source="user",
                registered_by="Liam",
                confidence=1.0,
                notes=data.get(
                    "notes",
                    "",
                ),
                create_inverse=True,
            )
            if relationship is not None:
                existing_keys.add(key)
            if inverse is not None:
                existing_keys.add(
                    (
                        inverse.source_entity_id,
                        inverse.source_entity_type,
                        inverse.relationship_type,
                        inverse.target_entity_id,
                        inverse.target_entity_type,
                    )
                )

        after_count = self.relationship_engine.get_relationship_count()
        return max(0, after_count - before_count)

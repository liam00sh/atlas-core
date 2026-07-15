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

        created_people = self._initialize_people()
        created_animals = self._initialize_animals()
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

    def _initialize_relationships(
        self,
    ) -> int:
        """
        Crea las relaciones ausentes y sus inversas.

        El conteo se calcula mediante la diferencia real de registros del
        almacenamiento. De esta forma, una segunda ejecución devuelve cero
        relaciones nuevas aunque el motor reutilice objetos existentes.
        """

        created_count = 0

        for data in FAMILY_RELATIONSHIPS:

            before_count = (
                self.relationship_engine
                .get_relationship_count()
            )

            self.relationship_engine.create_relationship_by_name(
                source=data["source"],
                source_type=data.get(
                    "source_type"
                ),
                relationship_type=(
                    data["relationship_type"]
                ),
                target=data["target"],
                target_type=data.get(
                    "target_type"
                ),
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

            after_count = (
                self.relationship_engine
                .get_relationship_count()
            )

            created_count += max(
                0,
                after_count - before_count,
            )

        return created_count

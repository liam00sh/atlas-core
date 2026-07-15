"""
===============================================================================
Proyecto Atlas
Archivo: identity/people_manager.py

Descripción:
    Gestiona las personas y los animales conocidos por Atlas.

    PeopleManager actúa como capa de servicio entre el resto
    del sistema y IdentityStorage.

    Sus responsabilidades principales son:

    - Crear personas.
    - Crear animales.
    - Buscar entidades por ID, nombre o alias.
    - Evitar duplicados evidentes.
    - Registrar nuevos encuentros.
    - Actualizar información básica.
    - Vincular personas con perfiles de UserManager.
    - Consultar personas por estado.
    - Eliminar entidades y sus relaciones asociadas.
    - Mantener separada la lógica social del almacenamiento JSON.

    PeopleManager no:

    - Lee ni escribe archivos directamente.
    - Deduce relaciones familiares.
    - Decide automáticamente que dos nombres pertenecen
      a la misma persona.
    - Reconoce voces o rostros.
    - Crea perfiles en UserManager.
    - Interpreta conversaciones completas.
    - Decide permisos de memoria.

    Estas responsabilidades pertenecerán posteriormente a:

        identity/identity_storage.py
        identity/relationship_engine.py
        identity/visitor_manager.py
        identity/session_identity.py

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from core.log_manager import info

from identity.animal import Animal
from identity.animal import UNKNOWN_SPECIES

from identity.identity_storage import IdentityStorage

from identity.person import Person

from identity.person_status import GUEST
from identity.person_status import PERSON_STATUSES
from identity.person_status import USER

from identity.relationship import ANIMAL_ENTITY
from identity.relationship import PERSON_ENTITY


# =============================================================================
# CLASE PRINCIPAL
# =============================================================================

class PeopleManager:
    """
    Gestiona las personas y animales conocidos por Atlas.

    Todas las operaciones persistentes se delegan
    en IdentityStorage.
    """

    def __init__(
        self,
        storage: IdentityStorage | None = None,
    ) -> None:
        """
        Inicializa el gestor.

        Parámetros:
            storage:
                Almacenamiento de identidades que debe utilizarse.

                Si no se proporciona, se crea una instancia
                de IdentityStorage con la carpeta de datos real.
        """

        self.storage = (
            storage
            if storage is not None
            else IdentityStorage()
        )

        info(
            "PeopleManager inicializado."
        )

    # =========================================================================
    # NORMALIZACIÓN
    # =========================================================================

    @staticmethod
    def _normalize_name(
        value: str,
    ) -> str:
        """
        Normaliza un nombre para realizar comparaciones.

        La normalización actual:

        - Elimina espacios exteriores.
        - Ignora mayúsculas y minúsculas.

        No elimina acentos, porque Person.matches_name()
        conserva actualmente la escritura real.

        En futuras versiones podrá utilizarse una clave adicional
        sin acentos para reconocer variantes como:

            Rubén
            Ruben
        """

        return str(
            value
        ).strip().casefold()

    # =========================================================================
    # CONSULTA GENERAL
    # =========================================================================

    def get_people(
        self,
    ) -> list[Person]:
        """
        Devuelve todas las personas almacenadas.
        """

        return self.storage.load_people()

    def get_animals(
        self,
    ) -> list[Animal]:
        """
        Devuelve todos los animales almacenados.
        """

        return self.storage.load_animals()

    def get_person_count(
        self,
    ) -> int:
        """
        Devuelve el número de personas registradas.
        """

        return len(
            self.get_people()
        )

    def get_animal_count(
        self,
    ) -> int:
        """
        Devuelve el número de animales registrados.
        """

        return len(
            self.get_animals()
        )

    def get_entity_count(
        self,
    ) -> int:
        """
        Devuelve el número total de entidades sociales.

        Incluye:

        - Personas.
        - Animales.
        """

        return (
            self.get_person_count()
            + self.get_animal_count()
        )

    # =========================================================================
    # BÚSQUEDA DE PERSONAS
    # =========================================================================

    def get_person_by_id(
        self,
        person_id: str,
    ) -> Person | None:
        """
        Busca una persona por su identificador.
        """

        return self.storage.get_person_by_id(
            person_id
        )

    def find_person_by_name(
        self,
        name: str,
    ) -> Person | None:
        """
        Busca una persona por su nombre principal o alias.

        Devuelve la persona únicamente cuando existe una sola
        coincidencia exacta. Si el nombre es ambiguo, devuelve
        ``None`` para impedir selecciones arbitrarias.
        """

        matches = self.find_people_by_name(
            name
        )

        if len(matches) != 1:
            return None

        return matches[0]

    def find_people_by_name(
        self,
        name: str,
    ) -> list[Person]:
        """
        Devuelve todas las personas cuyo nombre o alias
        coincida exactamente con el valor recibido.

        Este método resulta útil cuando existen personas
        diferentes con el mismo nombre.
        """

        name = str(
            name
        ).strip()

        if not name:
            return []

        return [
            person
            for person in self.get_people()
            if person.matches_name(
                name
            )
        ]

    def person_exists(
        self,
        name: str,
    ) -> bool:
        """
        Indica si existe alguna persona con ese nombre o alias.
        """

        return bool(
            self.find_people_by_name(
                name
            )
        )

    def get_people_by_status(
        self,
        status: str,
    ) -> list[Person]:
        """
        Devuelve las personas que tienen un estado determinado.
        """

        if status not in PERSON_STATUSES:

            raise ValueError(
                f"Estado de persona no válido: {status}"
            )

        return [
            person
            for person in self.get_people()
            if person.status == status
        ]

    def get_users(
        self,
    ) -> list[Person]:
        """
        Devuelve las personas vinculadas con perfiles de usuario.
        """

        return [
            person
            for person in self.get_people()
            if person.is_user()
        ]

    def find_person_by_user_profile(
        self,
        user_profile: str,
    ) -> Person | None:
        """
        Busca la persona vinculada a un perfil de UserManager.
        """

        profile_key = self._normalize_name(
            user_profile
        )

        if not profile_key:
            return None

        for person in self.get_people():

            if person.user_profile is None:
                continue

            if (
                self._normalize_name(
                    person.user_profile
                )
                == profile_key
            ):

                return person

        return None

    # =========================================================================
    # CREACIÓN DE PERSONAS
    # =========================================================================

    def create_person(
        self,
        name: str,
        *,
        aliases: list[str] | None = None,
        grammatical_gender: str = "unknown",
        status: str = GUEST,
        introduced_by: str | None = None,
        summary: str = "",
        user_profile: str | None = None,
        register_first_encounter: bool = False,
    ) -> Person | None:
        """
        Crea y guarda una persona nueva.

        Parámetros:
            name:
                Nombre principal.

            aliases:
                Alias o apodos conocidos.

            grammatical_gender:
                Género gramatical utilizado en las respuestas.

            status:
                Estado social inicial.

            introduced_by:
                Persona que la presentó.

            summary:
                Descripción breve.

            user_profile:
                Perfil de UserManager vinculado.

            register_first_encounter:
                Si es True, registra automáticamente
                el primer encuentro.

        Devuelve:
            Person:
                Persona creada correctamente.

            None:
                Ya existe una coincidencia evidente
                o no pudo guardarse.
        """

        clean_name = str(
            name
        ).strip()

        if not clean_name:

            raise ValueError(
                "El nombre de la persona no puede estar vacío."
            )

        # Una coincidencia exacta de nombre o alias impide
        # crear automáticamente otro registro.
        #
        # Más adelante podremos permitir homónimos mediante
        # una confirmación explícita.
        existing_person = self.find_person_by_name(
            clean_name
        )

        if existing_person is not None:

            info(
                "No se ha creado la persona porque ya existe "
                f"una coincidencia: {clean_name}."
            )

            return None

        if user_profile is not None:

            linked_person = (
                self.find_person_by_user_profile(
                    user_profile
                )
            )

            if linked_person is not None:

                info(
                    "No se ha creado la persona porque el perfil "
                    f"«{user_profile}» ya está vinculado a "
                    f"{linked_person.name}."
                )

                return None

        person = Person(
            name=clean_name,
            aliases=list(
                aliases or []
            ),
            grammatical_gender=(
                grammatical_gender
            ),
            status=status,
            introduced_by=introduced_by,
            summary=summary,
            user_profile=user_profile,
        )

        if register_first_encounter:

            person.register_encounter()

        saved = self.storage.add_person(
            person
        )

        if not saved:
            return None

        info(
            f"Persona creada por PeopleManager: "
            f"{person.name} ({person.id})."
        )

        return person

    def create_user_person(
        self,
        name: str,
        user_profile: str,
        *,
        aliases: list[str] | None = None,
        grammatical_gender: str = "unknown",
        introduced_by: str | None = None,
        summary: str = "",
        register_first_encounter: bool = False,
    ) -> Person | None:
        """
        Crea una persona vinculada a un perfil completo.

        Es una variante segura de create_person() que establece
        automáticamente el estado user.
        """

        return self.create_person(
            name=name,
            aliases=aliases,
            grammatical_gender=(
                grammatical_gender
            ),
            status=USER,
            introduced_by=introduced_by,
            summary=summary,
            user_profile=user_profile,
            register_first_encounter=(
                register_first_encounter
            ),
        )

    # =========================================================================
    # ACTUALIZACIÓN DE PERSONAS
    # =========================================================================

    def save_person(
        self,
        person: Person,
    ) -> bool:
        """
        Guarda los cambios de una persona existente.
        """

        if not isinstance(
            person,
            Person,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Person."
            )

        return self.storage.update_person(
            person
        )

    def register_person_encounter(
        self,
        person_id: str,
        occurred_at: str | None = None,
    ) -> Person | None:
        """
        Registra un encuentro y guarda el resultado.

        Devuelve la persona actualizada o None si no existe
        o no se pudo guardar.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return None

        person.register_encounter(
            occurred_at=occurred_at
        )

        if not self.save_person(
            person
        ):

            return None

        info(
            f"Encuentro registrado con {person.name}. "
            f"Total: {person.encounter_count}."
        )

        return person

    def add_person_alias(
        self,
        person_id: str,
        alias: str,
    ) -> bool:
        """
        Añade un alias y guarda la persona.

        No permite que el alias coincida con el nombre
        o alias de otra persona registrada.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return False

        alias = str(
            alias
        ).strip()

        if not alias:
            return False

        existing_person = self.find_person_by_name(
            alias
        )

        if (
            existing_person is not None
            and existing_person.id.casefold()
            != person.id.casefold()
        ):

            info(
                f"No se ha añadido el alias «{alias}» porque "
                f"ya identifica a {existing_person.name}."
            )

            return False

        added = person.add_alias(
            alias
        )

        if not added:
            return False

        return self.save_person(
            person
        )

    def update_person_summary(
        self,
        person_id: str,
        summary: str,
    ) -> bool:
        """
        Actualiza y guarda el resumen de una persona.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return False

        person.update_summary(
            summary
        )

        return self.save_person(
            person
        )

    def update_person_gender(
        self,
        person_id: str,
        grammatical_gender: str,
    ) -> bool:
        """
        Actualiza el género gramatical de una persona.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return False

        person.set_grammatical_gender(
            grammatical_gender
        )

        return self.save_person(
            person
        )

    def change_person_status(
        self,
        person_id: str,
        new_status: str,
    ) -> bool:
        """
        Cambia y guarda el estado social de una persona.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return False

        person.change_status(
            new_status
        )

        return self.save_person(
            person
        )

    def link_person_to_user(
        self,
        person_id: str,
        user_profile: str,
    ) -> bool:
        """
        Vincula una persona existente con UserManager.

        No crea el perfil de usuario. Solo guarda el vínculo.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return False

        existing_link = (
            self.find_person_by_user_profile(
                user_profile
            )
        )

        if (
            existing_link is not None
            and existing_link.id.casefold()
            != person.id.casefold()
        ):

            info(
                f"El perfil «{user_profile}» ya está vinculado "
                f"a {existing_link.name}."
            )

            return False

        person.link_user_profile(
            user_profile
        )

        return self.save_person(
            person
        )

    def unlink_person_from_user(
        self,
        person_id: str,
        fallback_status: str,
    ) -> bool:
        """
        Elimina el vínculo con UserManager.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return False

        person.unlink_user_profile(
            fallback_status=fallback_status
        )

        return self.save_person(
            person
        )

    # =========================================================================
    # ELIMINACIÓN DE PERSONAS
    # =========================================================================

    def delete_person(
        self,
        person_id: str,
        *,
        delete_relationships: bool = True,
    ) -> bool:
        """
        Elimina una persona.

        Parámetros:
            person_id:
                Identificador de la persona.

            delete_relationships:
                Indica si también deben eliminarse
                todas sus relaciones.

        Importante:
            Este método no elimina perfiles de UserManager,
            recuerdos ni contextos conversacionales.

            Esa coordinación deberá realizarla Atlas
            en una capa superior.
        """

        person = self.get_person_by_id(
            person_id
        )

        if person is None:
            return False

        if delete_relationships:

            self.storage.delete_relationships_for_entity(
                entity_id=person.id,
                entity_type=PERSON_ENTITY,
            )

        deleted = self.storage.delete_person(
            person.id
        )

        if deleted:

            info(
                f"Persona eliminada desde PeopleManager: "
                f"{person.name} ({person.id})."
            )

        return deleted

    # =========================================================================
    # BÚSQUEDA DE ANIMALES
    # =========================================================================

    def get_animal_by_id(
        self,
        animal_id: str,
    ) -> Animal | None:
        """
        Busca un animal por su identificador.
        """

        return self.storage.get_animal_by_id(
            animal_id
        )

    def find_animal_by_name(
        self,
        name: str,
    ) -> Animal | None:
        """
        Busca un animal por su nombre principal o alias.

        Devuelve el animal únicamente cuando existe una sola
        coincidencia exacta. Si el nombre es ambiguo, devuelve
        ``None`` para evitar seleccionar un registro al azar.
        """

        matches = self.find_animals_by_name(
            name
        )

        if len(matches) != 1:
            return None

        return matches[0]

    def find_animals_by_name(
        self,
        name: str,
    ) -> list[Animal]:
        """
        Devuelve todos los animales con el mismo nombre o alias.
        """

        name = str(
            name
        ).strip()

        if not name:
            return []

        return [
            animal
            for animal in self.get_animals()
            if animal.matches_name(
                name
            )
        ]

    def animal_exists(
        self,
        name: str,
    ) -> bool:
        """
        Indica si existe un animal con ese nombre o alias.
        """

        return bool(
            self.find_animals_by_name(
                name
            )
        )

    # =========================================================================
    # CREACIÓN DE ANIMALES
    # =========================================================================

    def create_animal(
        self,
        name: str,
        species: str = UNKNOWN_SPECIES,
        *,
        aliases: list[str] | None = None,
        breed: str | None = None,
        sex: str = "unknown",
        grammatical_gender: str = "unknown",
        birth_date: str | None = None,
        status: str = "active",
        summary: str = "",
        register_first_encounter: bool = False,
    ) -> Animal | None:
        """
        Crea y guarda un animal nuevo.

        La coincidencia exacta de nombre o alias impide
        su creación automática.

        Más adelante podremos permitir animales con el mismo nombre
        mediante una confirmación explícita.
        """

        clean_name = str(
            name
        ).strip()

        if not clean_name:

            raise ValueError(
                "El nombre del animal no puede estar vacío."
            )

        existing_animal = self.find_animal_by_name(
            clean_name
        )

        if existing_animal is not None:

            info(
                "No se ha creado el animal porque ya existe "
                f"una coincidencia: {clean_name}."
            )

            return None

        animal = Animal(
            name=clean_name,
            species=species,
            aliases=list(
                aliases or []
            ),
            breed=breed,
            sex=sex,
            grammatical_gender=(
                grammatical_gender
            ),
            birth_date=birth_date,
            status=status,
            summary=summary,
        )

        if register_first_encounter:

            animal.register_encounter()

        saved = self.storage.add_animal(
            animal
        )

        if not saved:
            return None

        info(
            f"Animal creado por PeopleManager: "
            f"{animal.name} ({animal.id})."
        )

        return animal

    # =========================================================================
    # ACTUALIZACIÓN DE ANIMALES
    # =========================================================================

    def save_animal(
        self,
        animal: Animal,
    ) -> bool:
        """
        Guarda los cambios de un animal existente.
        """

        if not isinstance(
            animal,
            Animal,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Animal."
            )

        return self.storage.update_animal(
            animal
        )

    def register_animal_encounter(
        self,
        animal_id: str,
        occurred_at: str | None = None,
    ) -> Animal | None:
        """
        Registra un encuentro con un animal.
        """

        animal = self.get_animal_by_id(
            animal_id
        )

        if animal is None:
            return None

        animal.register_encounter(
            occurred_at=occurred_at
        )

        if not self.save_animal(
            animal
        ):

            return None

        info(
            f"Encuentro registrado con el animal "
            f"{animal.name}. "
            f"Total: {animal.encounter_count}."
        )

        return animal

    def add_animal_alias(
        self,
        animal_id: str,
        alias: str,
    ) -> bool:
        """
        Añade un alias a un animal.
        """

        animal = self.get_animal_by_id(
            animal_id
        )

        if animal is None:
            return False

        alias = str(
            alias
        ).strip()

        if not alias:
            return False

        existing_animal = self.find_animal_by_name(
            alias
        )

        if (
            existing_animal is not None
            and existing_animal.id.casefold()
            != animal.id.casefold()
        ):

            info(
                f"No se ha añadido el alias «{alias}» porque "
                f"ya identifica al animal {existing_animal.name}."
            )

            return False

        added = animal.add_alias(
            alias
        )

        if not added:
            return False

        return self.save_animal(
            animal
        )

    def update_animal_summary(
        self,
        animal_id: str,
        summary: str,
    ) -> bool:
        """
        Actualiza el resumen de un animal.
        """

        animal = self.get_animal_by_id(
            animal_id
        )

        if animal is None:
            return False

        animal.update_summary(
            summary
        )

        return self.save_animal(
            animal
        )

    # =========================================================================
    # ELIMINACIÓN DE ANIMALES
    # =========================================================================

    def delete_animal(
        self,
        animal_id: str,
        *,
        delete_relationships: bool = True,
    ) -> bool:
        """
        Elimina un animal y, opcionalmente, sus relaciones.
        """

        animal = self.get_animal_by_id(
            animal_id
        )

        if animal is None:
            return False

        if delete_relationships:

            self.storage.delete_relationships_for_entity(
                entity_id=animal.id,
                entity_type=ANIMAL_ENTITY,
            )

        deleted = self.storage.delete_animal(
            animal.id
        )

        if deleted:

            info(
                f"Animal eliminado desde PeopleManager: "
                f"{animal.name} ({animal.id})."
            )

        return deleted

    # =========================================================================
    # RESOLUCIÓN GENERAL DE ENTIDADES
    # =========================================================================

    def resolve_entity(
        self,
        value: str,
        preferred_type: str | None = None,
    ) -> tuple[str, Person | Animal] | None:
        """
        Busca una entidad por nombre, alias o identificador.

        Parámetros:
            value:
                Nombre, alias o ID.

            preferred_type:
                Puede ser:

                - person
                - animal
                - None

        Devuelve:
            tuple:
                Tipo de entidad y objeto encontrado.

                Ejemplo:

                    (
                        "person",
                        Person(...)
                    )

            None:
                No se encontró ninguna coincidencia.

        Importante:
            Si existen una persona y un animal con el mismo nombre
            y no se indica preferred_type, se prioriza la persona.

            Más adelante SessionIdentity podrá gestionar
            estas ambigüedades mediante preguntas.
        """

        value = str(
            value
        ).strip()

        if not value:
            return None

        if preferred_type not in {
            None,
            PERSON_ENTITY,
            ANIMAL_ENTITY,
        }:

            raise ValueError(
                "Tipo de entidad preferido no válido: "
                f"{preferred_type}"
            )

        if preferred_type in {
            None,
            PERSON_ENTITY,
        }:

            person = self.get_person_by_id(
                value
            )

            if person is None:

                person = self.find_person_by_name(
                    value
                )

            if person is not None:

                return (
                    PERSON_ENTITY,
                    person,
                )

        if preferred_type in {
            None,
            ANIMAL_ENTITY,
        }:

            animal = self.get_animal_by_id(
                value
            )

            if animal is None:

                animal = self.find_animal_by_name(
                    value
                )

            if animal is not None:

                return (
                    ANIMAL_ENTITY,
                    animal,
                )

        return None
"""
===============================================================================
Proyecto Atlas
Archivo: identity/identity_storage.py

Descripción:
    Gestiona el almacenamiento persistente de Atlas Identity System.

    Este módulo es el único responsable de leer y escribir directamente
    los archivos JSON relacionados con identidades:

        identity/data/people.json
        identity/data/animals.json
        identity/data/relationships.json

    Sus responsabilidades son:

    - Crear la carpeta de datos cuando todavía no existe.
    - Crear los archivos JSON iniciales.
    - Leer personas, animales y relaciones.
    - Convertir los datos JSON en entidades del dominio.
    - Guardar entidades como diccionarios serializables.
    - Añadir y actualizar registros.
    - Eliminar registros por identificador.
    - Evitar duplicados por ID.
    - Gestionar errores de lectura y escritura.
    - Mantener separado el almacenamiento de la lógica social.

    IdentityStorage no:

    - Decide si una persona es invitada, conocida o habitual.
    - Interpreta conversaciones.
    - Decide permisos.
    - Deduce relaciones familiares.
    - Crea perfiles de usuario.
    - Reconoce automáticamente a una persona.

    Es únicamente la capa de persistencia del sistema de identidades.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import json
from copy import deepcopy

from pathlib import Path

from core.log_manager import error
from core.log_manager import info

from identity.animal import Animal
from identity.person import Person
from identity.relationship import Relationship


# =============================================================================
# CLASE DE ALMACENAMIENTO
# =============================================================================

class IdentityStorage:
    """
    Gestiona el almacenamiento persistente de identidades.

    Mantiene separados tres tipos de datos:

    - Personas.
    - Animales.
    - Relaciones.
    """

    def __init__(
        self,
        data_folder: Path | str | None = None,
    ) -> None:
        """
        Inicializa el almacenamiento.

        Parámetros:
            data_folder:
                Carpeta opcional donde se guardarán los archivos.

                Si no se proporciona, se utilizará:

                    identity/data/

                Este parámetro también permitirá utilizar carpetas
                temporales durante las pruebas automáticas.
        """

        if data_folder is None:

            self.data_folder = (
                Path(__file__).resolve().parent
                / "data"
            )

        else:

            self.data_folder = Path(
                data_folder
            ).resolve()

        self.people_file = (
            self.data_folder
            / "people.json"
        )

        self.animals_file = (
            self.data_folder
            / "animals.json"
        )

        self.relationships_file = (
            self.data_folder
            / "relationships.json"
        )
        # Tres entradas como máximo, una por archivo. La firma del archivo
        # invalida cambios externos y cada lectura devuelve copias profundas.
        self._entity_cache: dict[Path, tuple[tuple[int, int], list]] = {}

        self._ensure_storage()

        info(
            "IdentityStorage inicializado."
        )

    @staticmethod
    def _file_signature(file_path: Path) -> tuple[int, int]:
        stat = file_path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _cached_entities(self, file_path: Path):
        cached = self._entity_cache.get(file_path)
        if cached is None:
            return None
        try:
            signature = self._file_signature(file_path)
        except OSError:
            self._entity_cache.pop(file_path, None)
            return None
        if cached[0] != signature:
            self._entity_cache.pop(file_path, None)
            return None
        return deepcopy(cached[1])

    def _store_cached_entities(self, file_path: Path, entities: list) -> None:
        try:
            signature = self._file_signature(file_path)
        except OSError:
            return
        self._entity_cache[file_path] = (signature, deepcopy(entities))

    def _invalidate_cache(self, file_path: Path) -> None:
        self._entity_cache.pop(file_path, None)

    # =========================================================================
    # INICIALIZACIÓN
    # =========================================================================

    def _ensure_storage(
        self,
    ) -> None:
        """
        Crea la carpeta y los archivos necesarios.

        Los archivos nuevos comienzan con una lista JSON vacía:

            []
        """

        try:

            self.data_folder.mkdir(
                parents=True,
                exist_ok=True,
            )

        except OSError as exception:

            error(
                "No se pudo crear la carpeta de identidades: "
                f"{exception}"
            )

            raise

        self._ensure_json_file(
            self.people_file
        )

        self._ensure_json_file(
            self.animals_file
        )

        self._ensure_json_file(
            self.relationships_file
        )

    def _ensure_json_file(
        self,
        file_path: Path,
    ) -> None:
        """
        Crea un archivo JSON vacío cuando no existe.
        """

        if file_path.exists():
            return

        saved = self._save_json_list(
            file_path=file_path,
            data=[],
        )

        if not saved:

            raise OSError(
                "No se pudo crear el archivo "
                f"{file_path.name}."
            )

    # =========================================================================
    # OPERACIONES JSON INTERNAS
    # =========================================================================

    @staticmethod
    def _load_json_list(
        file_path: Path,
    ) -> list[dict]:
        """
        Lee una lista de diccionarios desde un archivo JSON.

        Si el archivo está vacío, dañado o no contiene una lista,
        devuelve una lista vacía.
        """

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(
                    file
                )

        except (
            json.JSONDecodeError,
            OSError,
        ) as exception:

            error(
                f"No se pudo leer {file_path.name}: "
                f"{exception}"
            )

            return []

        if not isinstance(
            data,
            list,
        ):

            error(
                f"El archivo {file_path.name} "
                "no contiene una lista JSON válida."
            )

            return []

        return [
            item
            for item in data
            if isinstance(
                item,
                dict,
            )
        ]

    @staticmethod
    def _save_json_list(
        file_path: Path,
        data: list[dict],
    ) -> bool:
        """
        Guarda una lista de diccionarios en un archivo JSON.
        """

        try:

            with open(
                file_path,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=4,
                )

            return True

        except (
            OSError,
            TypeError,
        ) as exception:

            error(
                f"No se pudo guardar {file_path.name}: "
                f"{exception}"
            )

            return False

    @staticmethod
    def _find_index_by_id(
        items: list,
        entity_id: str,
    ) -> int | None:
        """
        Busca la posición de una entidad por su identificador.

        La comparación ignora mayúsculas y minúsculas.
        """

        entity_key = (
            entity_id.strip().casefold()
        )

        if not entity_key:
            return None

        for index, item in enumerate(
            items
        ):

            item_id = str(
                getattr(
                    item,
                    "id",
                    "",
                )
            ).strip().casefold()

            if item_id == entity_key:
                return index

        return None

    # =========================================================================
    # PERSONAS
    # =========================================================================

    def load_people(
        self,
    ) -> list[Person]:
        """
        Carga todas las personas almacenadas.

        Los registros inválidos se omiten para evitar que un único
        elemento dañado impida utilizar el resto del sistema.
        """

        cached = self._cached_entities(self.people_file)
        if cached is not None:
            return cached

        raw_people = self._load_json_list(
            self.people_file
        )

        people = []

        for raw_person in raw_people:

            try:

                person = Person.from_dict(
                    raw_person
                )

            except (
                TypeError,
                ValueError,
            ) as exception:

                error(
                    "Se ha ignorado una persona inválida: "
                    f"{exception}"
                )

                continue

            people.append(
                person
            )

        self._store_cached_entities(self.people_file, people)
        return people

    def save_people(
        self,
        people: list[Person],
    ) -> bool:
        """
        Guarda la colección completa de personas.
        """

        if not all(
            isinstance(
                person,
                Person,
            )
            for person in people
        ):

            raise TypeError(
                "Todos los elementos deben ser objetos Person."
            )

        data = [
            person.to_dict()
            for person in people
        ]

        saved = self._save_json_list(
            file_path=self.people_file,
            data=data,
        )

        if saved:

            self._invalidate_cache(self.people_file)

            info(
                f"Personas guardadas: {len(people)}."
            )

        return saved

    def add_person(
        self,
        person: Person,
    ) -> bool:
        """
        Añade una persona nueva.

        No permite identificadores duplicados.
        """

        if not isinstance(
            person,
            Person,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Person."
            )

        people = self.load_people()

        if self._find_index_by_id(
            people,
            person.id,
        ) is not None:

            info(
                "No se ha añadido la persona porque "
                f"el ID ya existe: {person.id}."
            )

            return False

        people.append(
            person
        )

        saved = self.save_people(
            people
        )

        if saved:

            info(
                f"Persona añadida: {person.name} "
                f"({person.id})."
            )

        return saved

    def update_person(
        self,
        person: Person,
    ) -> bool:
        """
        Actualiza una persona existente por su ID.
        """

        if not isinstance(
            person,
            Person,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Person."
            )

        people = self.load_people()

        person_index = self._find_index_by_id(
            people,
            person.id,
        )

        if person_index is None:
            return False

        people[
            person_index
        ] = person

        saved = self.save_people(
            people
        )

        if saved:

            info(
                f"Persona actualizada: {person.name} "
                f"({person.id})."
            )

        return saved

    def delete_person(
        self,
        person_id: str,
    ) -> bool:
        """
        Elimina una persona por su identificador.

        Este método no elimina automáticamente sus relaciones.
        Esa coordinación corresponderá a PeopleManager.
        """

        people = self.load_people()

        person_index = self._find_index_by_id(
            people,
            person_id,
        )

        if person_index is None:
            return False

        removed_person = people.pop(
            person_index
        )

        saved = self.save_people(
            people
        )

        if saved:

            info(
                f"Persona eliminada: "
                f"{removed_person.name} "
                f"({removed_person.id})."
            )

        return saved

    def get_person_by_id(
        self,
        person_id: str,
    ) -> Person | None:
        """
        Devuelve una persona por su identificador.
        """

        people = self.load_people()

        person_index = self._find_index_by_id(
            people,
            person_id,
        )

        if person_index is None:
            return None

        return people[
            person_index
        ]

    # =========================================================================
    # ANIMALES
    # =========================================================================

    def load_animals(
        self,
    ) -> list[Animal]:
        """
        Carga todos los animales almacenados.
        """

        cached = self._cached_entities(self.animals_file)
        if cached is not None:
            return cached

        raw_animals = self._load_json_list(
            self.animals_file
        )

        animals = []

        for raw_animal in raw_animals:

            try:

                animal = Animal.from_dict(
                    raw_animal
                )

            except (
                TypeError,
                ValueError,
            ) as exception:

                error(
                    "Se ha ignorado un animal inválido: "
                    f"{exception}"
                )

                continue

            animals.append(
                animal
            )

        self._store_cached_entities(self.animals_file, animals)
        return animals

    def save_animals(
        self,
        animals: list[Animal],
    ) -> bool:
        """
        Guarda la colección completa de animales.
        """

        if not all(
            isinstance(
                animal,
                Animal,
            )
            for animal in animals
        ):

            raise TypeError(
                "Todos los elementos deben ser objetos Animal."
            )

        data = [
            animal.to_dict()
            for animal in animals
        ]

        saved = self._save_json_list(
            file_path=self.animals_file,
            data=data,
        )

        if saved:

            self._invalidate_cache(self.animals_file)

            info(
                f"Animales guardados: {len(animals)}."
            )

        return saved

    def add_animal(
        self,
        animal: Animal,
    ) -> bool:
        """
        Añade un animal nuevo.
        """

        if not isinstance(
            animal,
            Animal,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Animal."
            )

        animals = self.load_animals()

        if self._find_index_by_id(
            animals,
            animal.id,
        ) is not None:

            info(
                "No se ha añadido el animal porque "
                f"el ID ya existe: {animal.id}."
            )

            return False

        animals.append(
            animal
        )

        saved = self.save_animals(
            animals
        )

        if saved:

            info(
                f"Animal añadido: {animal.name} "
                f"({animal.id})."
            )

        return saved

    def update_animal(
        self,
        animal: Animal,
    ) -> bool:
        """
        Actualiza un animal existente por su ID.
        """

        if not isinstance(
            animal,
            Animal,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Animal."
            )

        animals = self.load_animals()

        animal_index = self._find_index_by_id(
            animals,
            animal.id,
        )

        if animal_index is None:
            return False

        animals[
            animal_index
        ] = animal

        saved = self.save_animals(
            animals
        )

        if saved:

            info(
                f"Animal actualizado: {animal.name} "
                f"({animal.id})."
            )

        return saved

    def delete_animal(
        self,
        animal_id: str,
    ) -> bool:
        """
        Elimina un animal por su identificador.
        """

        animals = self.load_animals()

        animal_index = self._find_index_by_id(
            animals,
            animal_id,
        )

        if animal_index is None:
            return False

        removed_animal = animals.pop(
            animal_index
        )

        saved = self.save_animals(
            animals
        )

        if saved:

            info(
                f"Animal eliminado: "
                f"{removed_animal.name} "
                f"({removed_animal.id})."
            )

        return saved

    def get_animal_by_id(
        self,
        animal_id: str,
    ) -> Animal | None:
        """
        Devuelve un animal por su identificador.
        """

        animals = self.load_animals()

        animal_index = self._find_index_by_id(
            animals,
            animal_id,
        )

        if animal_index is None:
            return None

        return animals[
            animal_index
        ]

    # =========================================================================
    # RELACIONES
    # =========================================================================

    def load_relationships(
        self,
    ) -> list[Relationship]:
        """
        Carga todas las relaciones almacenadas.
        """

        cached = self._cached_entities(self.relationships_file)
        if cached is not None:
            return cached

        raw_relationships = self._load_json_list(
            self.relationships_file
        )

        relationships = []

        for raw_relationship in raw_relationships:

            try:

                relationship = Relationship.from_dict(
                    raw_relationship
                )

            except (
                TypeError,
                ValueError,
            ) as exception:

                error(
                    "Se ha ignorado una relación inválida: "
                    f"{exception}"
                )

                continue

            relationships.append(
                relationship
            )

        self._store_cached_entities(self.relationships_file, relationships)
        return relationships

    def save_relationships(
        self,
        relationships: list[Relationship],
    ) -> bool:
        """
        Guarda la colección completa de relaciones.
        """

        if not all(
            isinstance(
                relationship,
                Relationship,
            )
            for relationship in relationships
        ):

            raise TypeError(
                "Todos los elementos deben ser "
                "objetos Relationship."
            )

        data = [
            relationship.to_dict()
            for relationship in relationships
        ]

        saved = self._save_json_list(
            file_path=self.relationships_file,
            data=data,
        )

        if saved:

            self._invalidate_cache(self.relationships_file)

            info(
                "Relaciones guardadas: "
                f"{len(relationships)}."
            )

        return saved

    def add_relationship(
        self,
        relationship: Relationship,
    ) -> bool:
        """
        Añade una relación nueva.

        No permite identificadores duplicados ni relaciones
        estructuralmente idénticas.
        """

        if not isinstance(
            relationship,
            Relationship,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Relationship."
            )

        relationships = self.load_relationships()

        if self._find_index_by_id(
            relationships,
            relationship.id,
        ) is not None:

            info(
                "No se ha añadido la relación porque "
                f"el ID ya existe: {relationship.id}."
            )

            return False

        duplicate_exists = any(
            current_relationship.matches(
                source_entity_id=(
                    relationship.source_entity_id
                ),
                source_entity_type=(
                    relationship.source_entity_type
                ),
                relationship_type=(
                    relationship.relationship_type
                ),
                target_entity_id=(
                    relationship.target_entity_id
                ),
                target_entity_type=(
                    relationship.target_entity_type
                ),
            )
            for current_relationship
            in relationships
        )

        if duplicate_exists:

            info(
                "Relación duplicada ignorada: "
                f"{relationship.source_entity_id} "
                f"--{relationship.relationship_type}--> "
                f"{relationship.target_entity_id}."
            )

            return False

        relationships.append(
            relationship
        )

        saved = self.save_relationships(
            relationships
        )

        if saved:

            info(
                f"Relación añadida: "
                f"{relationship.source_entity_id} "
                f"--{relationship.relationship_type}--> "
                f"{relationship.target_entity_id}."
            )

        return saved

    def update_relationship(
        self,
        relationship: Relationship,
    ) -> bool:
        """
        Actualiza una relación existente por su ID.
        """

        if not isinstance(
            relationship,
            Relationship,
        ):

            raise TypeError(
                "El elemento debe ser un objeto Relationship."
            )

        relationships = self.load_relationships()

        relationship_index = self._find_index_by_id(
            relationships,
            relationship.id,
        )

        if relationship_index is None:
            return False

        relationships[
            relationship_index
        ] = relationship

        saved = self.save_relationships(
            relationships
        )

        if saved:

            info(
                f"Relación actualizada: "
                f"{relationship.id}."
            )

        return saved

    def delete_relationship(
        self,
        relationship_id: str,
    ) -> bool:
        """
        Elimina una relación por su identificador.
        """

        relationships = self.load_relationships()

        relationship_index = self._find_index_by_id(
            relationships,
            relationship_id,
        )

        if relationship_index is None:
            return False

        removed_relationship = relationships.pop(
            relationship_index
        )

        saved = self.save_relationships(
            relationships
        )

        if saved:

            info(
                "Relación eliminada: "
                f"{removed_relationship.id}."
            )

        return saved

    def get_relationship_by_id(
        self,
        relationship_id: str,
    ) -> Relationship | None:
        """
        Devuelve una relación por su identificador.
        """

        relationships = self.load_relationships()

        relationship_index = self._find_index_by_id(
            relationships,
            relationship_id,
        )

        if relationship_index is None:
            return None

        return relationships[
            relationship_index
        ]

    def delete_relationships_for_entity(
        self,
        entity_id: str,
        entity_type: str,
    ) -> int:
        """
        Elimina todas las relaciones asociadas a una entidad.

        Devuelve:
            int:
                Número de relaciones eliminadas.
        """

        relationships = self.load_relationships()

        remaining_relationships = [
            relationship
            for relationship in relationships
            if not relationship.involves_entity(
                entity_id=entity_id,
                entity_type=entity_type,
            )
        ]

        removed_count = (
            len(relationships)
            - len(remaining_relationships)
        )

        if removed_count == 0:
            return 0

        saved = self.save_relationships(
            remaining_relationships
        )

        if not saved:
            return 0

        info(
            f"Relaciones eliminadas para la entidad "
            f"{entity_type}:{entity_id}: "
            f"{removed_count}."
        )

        return removed_count

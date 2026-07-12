"""
===============================================================================
Proyecto Atlas
Archivo: memory/memory_manager.py

Descripción:
    Este módulo gestiona la memoria persistente de Atlas.

    Sus responsabilidades principales son:

    - Crear la carpeta donde se guardan los recuerdos.
    - Crear el archivo memories.json si todavía no existe.
    - Leer todos los recuerdos almacenados.
    - Guardar nuevos recuerdos.
    - Evitar recuerdos duplicados.
    - Asignar un identificador único a cada recuerdo.
    - Registrar la fecha de creación.
    - Filtrar los recuerdos según el usuario que los consulta.
    - Contar cuántos recuerdos pertenecen a una persona.

Archivo utilizado:

    memory/data/memories.json

Ejemplo de recuerdo almacenado:

    {
        "id": "f06f3bc0-5da8-4a85-b8e8-f474d129ab32",
        "owner": "Liam",
        "content": "Mi coche es un Hyundai i30 N.",
        "visibility": "known",
        "created_at": "2026-07-11T20:35:42"
    }

Importante:
    Este módulo gestiona el almacenamiento de los recuerdos.

    No decide por sí solo quién puede acceder a ellos.
    Esa decisión se delega a:

        memory/access_control.py

===============================================================================
"""


# =============================================================================
# IMPORTACIONES DE LA BIBLIOTECA ESTÁNDAR
# =============================================================================

# json permite convertir datos de Python en formato JSON
# y volver a leerlos posteriormente.
#
# Se utiliza para guardar la memoria en:
#
#     memory/data/memories.json
import json

# uuid permite generar identificadores únicos.
#
# Cada recuerdo tendrá un ID diferente, incluso aunque
# varios recuerdos se creen en el mismo segundo.
import uuid


# Importamos datetime para registrar la fecha y hora
# en la que se crea cada recuerdo.
from datetime import datetime

# Path permite trabajar con rutas de archivos y carpetas
# de forma compatible con Windows, Linux y macOS.
from pathlib import Path


# =============================================================================
# IMPORTACIONES DEL SISTEMA DE LOGS
# =============================================================================

# Registra errores en atlas.log.
from core.log_manager import error

# Registra eventos informativos en atlas.log.
from core.log_manager import info

# =============================================================================
# IMPORTACIÓN DEL CONTROL DE ACCESO
# =============================================================================

# Esta función comprueba si un usuario concreto
# tiene permiso para leer un recuerdo.
from memory.access_control import can_read_memory


class MemoryManager:
    """
    Gestiona el almacenamiento persistente de recuerdos.

    La memoria se guarda en un archivo JSON común.

    Cada recuerdo contiene:

    - Un identificador único.
    - Un propietario.
    - El contenido.
    - Un nivel de visibilidad.
    - La fecha de creación.
    """

    def __init__(self):
        """
        Inicializa el gestor de memoria.

        Durante la inicialización:

        1. Calcula la ruta de la carpeta data/.
        2. Crea la carpeta si no existe.
        3. Define el archivo memories.json.
        4. Crea el archivo si todavía no existe.
        5. Registra la inicialización en el log.
        """

        # ---------------------------------------------------------------------
        # Ruta de la carpeta donde se almacenará la memoria.
        #
        # __file__
        #     Representa la ruta del archivo actual:
        #
        #     memory/memory_manager.py
        #
        # resolve()
        #     Convierte la ruta en absoluta.
        #
        # parent
        #     Sube a la carpeta:
        #
        #     memory/
        #
        # / "data"
        #     Añade la subcarpeta data.
        #
        # Resultado aproximado:
        #
        # C:\Atlas\atlas_core\memory\data
        # ---------------------------------------------------------------------
        self.data_folder = (
            Path(__file__).resolve().parent
            / "data"
        )

        # ---------------------------------------------------------------------
        # Creamos la carpeta data si todavía no existe.
        #
        # parents=True
        #     También crea carpetas superiores necesarias.
        #
        # exist_ok=True
        #     Evita un error si la carpeta ya existe.
        # ---------------------------------------------------------------------
        self.data_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Definimos la ruta completa del archivo de memoria.
        self.memory_file = (
            self.data_folder
            / "memories.json"
        )

        # Nos aseguramos de que el archivo exista
        # antes de intentar leerlo.
        self._ensure_memory_file()

        # Registramos que el gestor se ha iniciado.
        info("Memory Manager inicializado.")

    def _ensure_memory_file(self):
        """
        Comprueba que exista el archivo memories.json.

        Si ya existe:
            No hace nada.

        Si no existe:
            Crea un archivo JSON vacío con una lista:

                []
        """

        # Si el archivo ya existe, terminamos la función.
        if self.memory_file.exists():
            return

        # Si no existe, guardamos una lista vacía.
        self._save_all_memories([])

    def _load_all_memories(self) -> list[dict]:
        """
        Carga todos los recuerdos almacenados.

        No recibe parámetros.

        Devuelve:
            list[dict]:
                Lista de recuerdos.

        Ejemplo:

            [
                {
                    "owner": "Liam",
                    "content": "Mi coche es...",
                    ...
                }
            ]

        Si ocurre un error:
            Registra el problema y devuelve una lista vacía.
        """

        try:

            # Abrimos el archivo en modo lectura.
            #
            # "r" significa:
            #     read / lectura.
            #
            # encoding="utf-8" permite guardar correctamente:
            #
            # - Acentos.
            # - Eñes.
            # - Símbolos.
            # - Emojis.
            with open(
                self.memory_file,
                "r",
                encoding="utf-8",
            ) as file:

                # json.load() convierte el contenido JSON
                # en estructuras de Python.
                data = json.load(file)

            # Comprobamos que el contenido raíz sea una lista.
            #
            # Si alguien modifica el archivo y guarda un diccionario
            # u otro tipo de dato, evitamos que Atlas falle.
            if not isinstance(data, list):
                return []

            return data

        # json.JSONDecodeError:
        #     El archivo JSON está mal escrito o dañado.
        #
        # OSError:
        #     Error al acceder al archivo.
        except (
            json.JSONDecodeError,
            OSError,
        ) as exception:

            # Registramos el error técnico.
            error(
                f"No se pudo cargar la memoria: "
                f"{exception}"
            )

            # Devolvemos una lista vacía para que Atlas
            # pueda seguir funcionando.
            return []

    def _save_all_memories(
        self,
        memories: list[dict],
    ) -> bool:
        """
        Guarda la lista completa de recuerdos en memories.json.

        Parámetros:
            memories:
                Lista completa que se desea almacenar.

        Devuelve:
            True:
                El archivo se ha guardado correctamente.

            False:
                Se ha producido un error.
        """

        try:

            # Abrimos el archivo en modo escritura.
            #
            # "w" significa:
            #     write / escritura.
            #
            # Este modo reemplaza el contenido anterior.
            with open(
                self.memory_file,
                "w",
                encoding="utf-8",
            ) as file:

                # json.dump() convierte las estructuras de Python
                # en texto JSON y las escribe en el archivo.
                json.dump(
                    memories,
                    file,

                    # Mantiene los caracteres Unicode reales.
                    #
                    # Ejemplo:
                    #
                    # "Saray" o "información"
                    #
                    # en lugar de secuencias escapadas.
                    ensure_ascii=False,

                    # Formatea el archivo con una sangría de cuatro espacios
                    # para que sea fácil de leer manualmente.
                    indent=4,
                )

            return True

        except OSError as exception:

            error(
                f"No se pudo guardar la memoria: "
                f"{exception}"
            )

            return False

    def remember(
        self,
        owner: str,
        content: str,
        visibility: str,
    ) -> bool:
        """
        Guarda un nuevo recuerdo.

        Parámetros:
            owner:
                Persona a la que pertenece el recuerdo.

            content:
                Información que debe almacenarse.

            visibility:
                Nivel de acceso del recuerdo.

                Ejemplos:
                    private
                    admin_managed
                    partner
                    family
                    known
                    public

        Devuelve:
            True:
                El recuerdo se ha guardado correctamente
                o ya existía.

            False:
                No se pudo guardar.
        """

        # Eliminamos espacios innecesarios al principio
        # y al final del contenido.
        content = content.strip()

        # No se permiten recuerdos vacíos.
        if not content:
            return False

        # Cargamos la memoria actual.
        memories = self._load_all_memories()

        # ---------------------------------------------------------------------
        # DETECCIÓN DE DUPLICADOS
        # ---------------------------------------------------------------------
        #
        # any() devuelve True si al menos un elemento
        # cumple la condición.
        #
        # Se considera duplicado si:
        #
        # - Tiene el mismo propietario.
        # - Tiene el mismo contenido.
        #
        # La comparación ignora mayúsculas y minúsculas.
        duplicate_exists = any(
            memory["owner"].lower()
            == owner.lower()
            and memory["content"].lower()
            == content.lower()
            for memory in memories
        )

        # Si ya existe, no lo guardamos otra vez.
        if duplicate_exists:

            info(
                f"Memoria duplicada ignorada para "
                f"{owner}: {content}"
            )

            # Devolvemos True porque el dato ya está almacenado.
            return True

        # ---------------------------------------------------------------------
        # CONSTRUCCIÓN DEL NUEVO RECUERDO
        # ---------------------------------------------------------------------
        memory = {

            # Genera un identificador único.
            #
            # uuid.uuid4() crea un UUID aleatorio.
            #
            # str() lo convierte en texto para poder
            # almacenarlo dentro del JSON.
            "id": str(uuid.uuid4()),

            # Persona propietaria de la información.
            "owner": owner,

            # Información que debe recordarse.
            "content": content,

            # Nivel de privacidad.
            "visibility": visibility,

            # Fecha y hora de creación.
            #
            # isoformat() genera un formato estándar:
            #
            # 2026-07-11T20:35:42
            #
            # timespec="seconds" elimina los microsegundos.
            "created_at": datetime.now().isoformat(
                timespec="seconds"
            ),

        }

        # Añadimos el nuevo recuerdo a la lista.
        memories.append(memory)

        # Guardamos nuevamente la lista completa.
        saved = self._save_all_memories(
            memories
        )

        # Si se ha guardado correctamente,
        # registramos el evento.
        if saved:

            info(
                f"Memoria guardada para {owner} "
                f"con visibilidad {visibility}: "
                f"{content}"
            )

        return saved

    def get_accessible_memories(
        self,
        owner: str,
        viewer: str,
        viewer_profile: dict,
    ) -> list[dict]:
        """
        Devuelve los recuerdos que un usuario puede consultar.

        Parámetros:
            owner:
                Propietario de los recuerdos buscados.

            viewer:
                Persona que está intentando verlos.

            viewer_profile:
                Perfil completo de la persona que consulta.

        Devuelve:
            list[dict]:
                Lista de recuerdos autorizados.

        Ejemplo:
            Saray pregunta qué sabe Atlas de Liam.

            owner:
                Liam

            viewer:
                Saray

            viewer_profile:
                Perfil de Saray
        """

        # Cargamos todos los recuerdos.
        memories = self._load_all_memories()

        # ---------------------------------------------------------------------
        # FILTRO POR PROPIETARIO
        # ---------------------------------------------------------------------
        #
        # Primero seleccionamos únicamente los recuerdos
        # que pertenecen a la persona solicitada.
        owner_memories = [
            memory
            for memory in memories
            if memory["owner"].lower()
            == owner.lower()
        ]

        # ---------------------------------------------------------------------
        # FILTRO DE PERMISOS
        # ---------------------------------------------------------------------
        #
        # De los recuerdos del propietario, devolvemos únicamente
        # los que can_read_memory() permite consultar.
        return [
            memory
            for memory in owner_memories
            if can_read_memory(
                memory=memory,
                viewer=viewer,
                viewer_profile=viewer_profile,
            )
        ]

    def count_memories(
        self,
        owner: str,
    ) -> int:
        """
        Cuenta cuántos recuerdos pertenecen a una persona.

        Parámetros:
            owner:
                Nombre del propietario.

        Devuelve:
            int:
                Número total de recuerdos encontrados.

        Importante:
            Este método cuenta todos los recuerdos del propietario,
            independientemente de su nivel de privacidad.
        """

        # Cargamos todos los recuerdos.
        memories = self._load_all_memories()

        # sum() suma un 1 por cada recuerdo cuyo
        # propietario coincida con el solicitado.
        return sum(
            1
            for memory in memories
            if memory["owner"].lower()
            == owner.lower()
        )
"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas.py

Descripción:
    Contiene la clase principal Atlas.

    Esta clase actúa como núcleo central de Daxter y coordina:

    - Procesamiento del texto.
    - Sistema de comandos.
    - Conversación básica.
    - Gestión de usuarios.
    - Gestión de memoria.
    - Registro de actividad.

    La lógica conversacional específica de la memoria se ha trasladado a:

        memory/memory_service.py

    De esta forma, la clase Atlas resulta más pequeña y manejable.

Flujo principal:

    Usuario
       │
       ▼
    Atlas.process()
       │
       ├── Memoria pendiente
       ├── Guardar recuerdos
       ├── Consultar recuerdos
       ├── Ejecutar comandos
       ├── Conversación
       └── Entrada desconocida

===============================================================================
"""


# =============================================================================
# CAPACIDADES
# =============================================================================

from capabilities.capabilities import CapabilityManager


# =============================================================================
# CONVERSACIÓN
# =============================================================================

from conversation.intent import detect
from conversation.personality import not_understood


# =============================================================================
# COMANDOS
# =============================================================================

from console.command_manager import COMMANDS
from console.command_manager import execute
from console.command_manager import resolve_command


# =============================================================================
# NÚCLEO
# =============================================================================

from core.log_manager import info
from core.user_manager import UserManager
from core.version import ASSISTANT_NAME
from core.version import PROJECT_NAME
from core.version import VERSION


# =============================================================================
# MEMORIA
# =============================================================================

from memory.memory_manager import MemoryManager
from memory.memory_service import MemoryService


# =============================================================================
# UTILIDADES DE TEXTO
# =============================================================================

from utils.memory_query_parser import parse_memory_query
from utils.text_normalizer import normalize_text


class Atlas:
    """
    Clase principal del Proyecto Atlas.

    Representa una única instancia activa de Daxter
    y coordina todos los subsistemas.
    """

    def __init__(self):
        """
        Inicializa el núcleo principal de Atlas.
        """

        # Identidad del proyecto y del asistente.
        self.name = ASSISTANT_NAME
        self.project = PROJECT_NAME
        self.version = VERSION

        # Gestor de usuarios y perfiles.
        self.users = UserManager()

        # Gestor de capacidades realmente disponibles.
        self.capabilities = CapabilityManager()

        # Gestor encargado de leer y guardar recuerdos.
        self.memory = MemoryManager()

        # Servicio que gestiona la conversación
        # relacionada con la memoria.
        self.memory_service = MemoryService(
            self
        )

        # Registramos la inicialización.
        info("Atlas Core inicializado.")

    def process(
        self,
        text: str,
    ) -> bool:
        """
        Procesa una entrada escrita por el usuario.

        El método actúa como coordinador. Cada tipo de entrada se delega
        en una función auxiliar para que el flujo principal sea fácil de
        leer y modificar.
        """

        original_text = text.strip()
        normalized_text = normalize_text(
            original_text,
            COMMANDS.keys(),
        )

        if normalized_text == "":
            return True

        info(f"Entrada del usuario: {normalized_text}")

        if self.memory_service.has_pending_memory():
            return self.memory_service.process_visibility_answer(
                normalized_text
            )

        if self._is_memory_storage_request(normalized_text):
            return self._handle_memory_storage_request(original_text)

        if self._handle_memory_query(original_text):
            return True

        command_result = self._handle_command(
            original_text,
            normalized_text,
        )

        if command_result is not None:
            return command_result

        if self._handle_conversation(original_text, normalized_text):
            return True

        self._show_not_understood(normalized_text)
        return True

    @staticmethod
    def _is_memory_storage_request(normalized_text: str) -> bool:
        """Indica si la entrada solicita guardar un recuerdo."""

        return normalized_text.startswith("recuerda que ")

    def _handle_memory_storage_request(self, original_text: str) -> bool:
        """Extrae y envía al servicio de memoria un nuevo recuerdo."""

        # "recuerda que " ocupa trece caracteres. Se usa el texto
        # original para conservar mayúsculas, nombres propios y acentos.
        content = original_text[13:].strip()
        return self.memory_service.process_memory_request(content)

    def _handle_memory_query(self, original_text: str) -> bool:
        """Procesa una consulta de recuerdos si la entrada contiene una."""

        memory_query = parse_memory_query(original_text)
        if memory_query is None:
            return False

        if memory_query["type"] == "self":
            self.memory_service.show_memories_about(self.get_user())
            return True

        requested_owner = memory_query["owner"]
        resolved_owner = self.users.resolve_user_name(requested_owner)

        if resolved_owner is None:
            print()
            print(
                f"No conozco ningún usuario llamado «{requested_owner}»."
            )
            return True

        self.memory_service.show_memories_about(resolved_owner)
        return True

    def _handle_command(
        self,
        original_text: str,
        normalized_text: str,
    ) -> bool | None:
        """
        Resuelve y ejecuta un comando reconocido.

        Devuelve:
            None:
                La entrada no corresponde a ningún comando.

            True:
                El comando se ejecutó y Atlas debe continuar.

            False:
                El comando se ejecutó y Atlas debe finalizar.
        """

        resolved_command = resolve_command(
            normalized_text
        )

        if resolved_command is None:
            return None

        info(
            f"Comando ejecutado: {resolved_command}. "
            f"Entrada original: {original_text}"
        )

        return execute(
            resolved_command
        )

    @staticmethod
    def _handle_conversation(
        original_text: str,
        normalized_text: str,
    ) -> bool:
        """Muestra una respuesta de conversación básica si existe."""

        response = detect(original_text)
        if not response:
            return False

        info(f"Conversación: {normalized_text}")
        print()
        print(response)
        return True

    @staticmethod
    def _show_not_understood(normalized_text: str) -> None:
        """Registra y muestra la respuesta para una entrada desconocida."""

        info(f"No entendido: {normalized_text}")
        print()
        print(not_understood())

    def execute(
        self,
        command: str,
    ):
        """
        Ejecuta directamente un comando.
        """

        return execute(command)

    def get_name(self):
        """
        Devuelve el nombre del asistente.
        """

        return self.name

    def get_version(self):
        """
        Devuelve la versión de Atlas.
        """

        return self.version

    def get_project(self):
        """
        Devuelve el nombre del proyecto.
        """

        return self.project

    def get_user(self):
        """
        Devuelve el usuario activo.
        """

        return self.users.get_current_user()

    def get_main_user(self):
        """
        Devuelve el usuario principal.
        """

        return self.users.get_main_user()

    def change_user(
        self,
        user: str,
    ):
        """
        Cambia el usuario activo.
        """

        previous_user = self.get_user()

        self.users.change_user(
            user
        )

        info(
            f"Cambio de usuario: "
            f"{previous_user} -> {user}"
        )

    def return_to_main_user(self):
        """
        Devuelve la sesión al usuario principal.
        """

        previous_user = self.get_user()

        self.users.return_to_main()

        info(
            f"Regreso al usuario principal: "
            f"{previous_user} -> "
            f"{self.get_user()}"
        )

    def is_main_user(self):
        """
        Indica si el usuario activo es el principal.
        """

        return self.users.is_main_user()

    def remember(
        self,
        content: str,
        visibility: str,
    ) -> bool:
        """
        Guarda un recuerdo para el usuario activo.

        Parámetros:
            content:
                Información que debe almacenarse.

            visibility:
                Nivel de privacidad.
        """

        return self.memory.remember(
            owner=self.get_user(),
            content=content,
            visibility=visibility,
        )

    def can_chat(self) -> bool:
        """
        Indica si la conversación básica está disponible.
        """

        return self.capabilities.is_enabled(
            "chat"
        )

    def can_use_memory(self) -> bool:
        """
        Indica si el sistema de memoria está disponible.
        """

        return self.capabilities.is_enabled(
            "memory"
        )

    def can_use_ai(self) -> bool:
        """
        Indica si la inteligencia artificial está disponible.
        """

        return self.capabilities.is_enabled(
            "ai"
        )

    def can_use_voice(self) -> bool:
        """
        Indica si el sistema de voz está disponible.
        """

        return self.capabilities.is_enabled(
            "voice"
        )

    def can_use_tools(self) -> bool:
        """
        Indica si las herramientas de IA están disponibles.
        """

        return self.capabilities.is_enabled(
            "tools"
        )

    def can_use_automation(self) -> bool:
        """
        Indica si las automatizaciones están disponibles.
        """

        return self.capabilities.is_enabled(
            "automation"
        )

    def can_access_internet(self) -> bool:
        """
        Indica si Atlas puede utilizar Internet.
        """

        return self.capabilities.is_enabled(
            "internet"
        )

    def get_capabilities(self) -> dict:
        """
        Devuelve todas las capacidades conocidas.
        """

        return self.capabilities.get_all()

    def get_commands(self):
        """
        Devuelve todos los comandos disponibles.
        """

        return COMMANDS
"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas.py

Descripción:
    Contiene la clase principal Atlas.

    Atlas actúa como coordinador de los subsistemas del proyecto.

    La lógica especializada se distribuye entre varios mixins:

    - atlas_ai.py
    - atlas_capabilities.py
    - atlas_commands.py
    - atlas_memory.py
    - atlas_tools.py
    - atlas_users.py
    - atlas_utils.py

Flujo principal:

    Usuario
       │
       ▼
    Atlas.process()
       │
       ├── Confirmación pendiente
       ├── Memoria pendiente
       ├── Selección automática de modo
       ├── Guardar recuerdos
       ├── Consultar recuerdos
       ├── Ejecutar comandos
       ├── Conversación básica
       ├── Consultas de contexto
       ├── Herramientas locales
       ├── Inteligencia artificial local
       └── Entrada desconocida

===============================================================================
"""


# =============================================================================
# INTELIGENCIA ARTIFICIAL
# =============================================================================

from ai.cache.response_cache import ResponseCache
from ai.context.context_manager import AIContextManager
from ai.models.model_registry import ModelRegistry
from ai.prompts.builder import PromptBuilder
from ai.providers.base_provider import BaseAIProvider
from ai.tools.tool_registry import ToolRegistry
from ai.tools.tool_selector import ToolSelector


# =============================================================================
# IDENTIDAD DEL ASISTENTE
# =============================================================================

from assistant_identity.identity_manager import IdentityManager


# =============================================================================
# CAPACIDADES
# =============================================================================

from capabilities.capabilities import CapabilityManager


# =============================================================================
# COMANDOS
# =============================================================================

from console.command_manager import COMMANDS


# =============================================================================
# NÚCLEO
# =============================================================================

from core.atlas_ai import AtlasAIMixin
from core.atlas_capabilities import AtlasCapabilitiesMixin
from core.atlas_commands import AtlasCommandsMixin
from core.atlas_memory import AtlasMemoryMixin
from core.atlas_tools import AtlasToolsMixin
from core.atlas_users import AtlasUsersMixin
from core.atlas_utils import AtlasUtilsMixin

from core.confirmation_manager import ConfirmationManager
from core.log_manager import info
from core.user_manager import UserManager
from core.version import ASSISTANT_NAME
from core.version import PROJECT_NAME
from core.version import VERSION


# =============================================================================
# IDENTIDAD DE PERSONAS
# =============================================================================

from identity.conversation_identity import ConversationIdentity
from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.visitor_manager import VisitorManager


# =============================================================================
# MEMORIA
# =============================================================================

from memory.memory_manager import MemoryManager
from memory.memory_retriever import MemoryRetriever
from memory.memory_service import MemoryService


# =============================================================================
# UTILIDADES
# =============================================================================

from utils.text_normalizer import normalize_text


from identity.family_initializer import FamilyInitializer
from identity.family_service import FamilyService
from identity.relationship_engine import RelationshipEngine


# =============================================================================
# CLASE PRINCIPAL
# =============================================================================

class Atlas(
    AtlasAIMixin,
    AtlasCapabilitiesMixin,
    AtlasCommandsMixin,
    AtlasMemoryMixin,
    AtlasToolsMixin,
    AtlasUsersMixin,
    AtlasUtilsMixin,
):
    """
    Clase principal del Proyecto Atlas.

    Coordina todos los subsistemas mediante composición
    y herencia de mixins.
    """

    def __init__(
        self,
        ai_provider: BaseAIProvider | None = None,
    ) -> None:
        """
        Inicializa el núcleo principal de Atlas.
        """

        # ---------------------------------------------------------------------
        # INFORMACIÓN DEL PROYECTO
        # ---------------------------------------------------------------------

        self.name = ASSISTANT_NAME
        self.project = PROJECT_NAME
        self.version = VERSION

        # ---------------------------------------------------------------------
        # USUARIOS
        # ---------------------------------------------------------------------

        self.users = UserManager()

        # ---------------------------------------------------------------------
        # IDENTIDAD DE PERSONAS
        # ---------------------------------------------------------------------

        # Almacenamiento persistente de personas,
        # relaciones y animales.
        self.identity_storage = IdentityStorage()

        # Gestor principal de personas y animales.
        self.people_manager = PeopleManager(
            self.identity_storage
        )

        # Gestiona la evolución de visitantes,
        # conocidos, habituales y usuarios.
        self.visitor_manager = VisitorManager(
            self.people_manager
        )

        self.relationship_engine = (
            RelationshipEngine(
                people_manager=self.people_manager,
                storage=self.identity_storage,
            )
        )

        self.family_initializer = (
            FamilyInitializer(
                people_manager=self.people_manager,
                relationship_engine=(
                    self.relationship_engine
                ),
            )
        )

        self.family_service = (
            FamilyService(
                people_manager=self.people_manager,
                relationship_engine=(
                    self.relationship_engine
                ),
            )
        )

        self.family_initializer.initialize()

        # Separa:
        #
        # - El usuario autenticado.
        # - La persona que está hablando.
        self.conversation_identity = ConversationIdentity(
            people_manager=self.people_manager,
            visitor_manager=self.visitor_manager,
        )

        # El usuario activo inicia la sesión autenticada.
        self.conversation_identity.set_authenticated_user(
            self.get_user()
        )

        # Al comenzar, la persona que habla es el propio
        # usuario autenticado.
        self.conversation_identity.identify_person(
            self.get_user()
        )

        # ---------------------------------------------------------------------
        # IDENTIDAD DEL ASISTENTE
        # ---------------------------------------------------------------------

        # Gestiona:
        #
        # - Daxter y Coco.
        # - El modo activo.
        # - El cambio automático de modo.
        # - Las preferencias separadas por interlocutor.
        self.identity_manager = IdentityManager()

        # Las preferencias deben corresponder a la persona
        # que está hablando, no necesariamente al usuario
        # autenticado de la sesión.
        identity_user = (
            self.conversation_identity
            .get_conversation_owner()
        )

        if identity_user is None:
            identity_user = self.get_user()

        self.identity_manager.load_user(
            identity_user
        )

        # ---------------------------------------------------------------------
        # CAPACIDADES
        # ---------------------------------------------------------------------

        self.capabilities = CapabilityManager()

        # ---------------------------------------------------------------------
        # CONFIRMACIONES
        # ---------------------------------------------------------------------

        self.confirmations = ConfirmationManager(
            expiration_minutes=5
        )

        # ---------------------------------------------------------------------
        # MEMORIA
        # ---------------------------------------------------------------------

        self.memory = MemoryManager()

        self.memory_retriever = MemoryRetriever(
            memory_manager=self.memory
        )

        self.memory_service = MemoryService(
            self
        )

        # ---------------------------------------------------------------------
        # INTELIGENCIA ARTIFICIAL
        # ---------------------------------------------------------------------

        self.ai_provider = ai_provider

        self.model_registry = ModelRegistry()

        self.prompt_builder = PromptBuilder()

        # ---------------------------------------------------------------------
        # HERRAMIENTAS
        # ---------------------------------------------------------------------

        self.tool_registry = ToolRegistry()

        self.tool_selector = ToolSelector(
            self.tool_registry
        )

        # ---------------------------------------------------------------------
        # CACHÉ DE IA
        # ---------------------------------------------------------------------

        self.ai_cache = ResponseCache(
            max_entries=100
        )

        # ---------------------------------------------------------------------
        # CONTEXTOS TEMPORALES
        # ---------------------------------------------------------------------

        self.ai_contexts: dict[
            str,
            AIContextManager,
        ] = {}

        self.ai_context_max_messages = 10

        self._get_ai_context_for_user(
            self.get_user()
        )

        info(
            "Atlas Core inicializado."
        )

    def process(
        self,
        text: str,
    ) -> bool:
        """
        Procesa una entrada escrita por el usuario.

        Devuelve:
            True:
                Atlas continúa funcionando.

            False:
                Atlas debe finalizar.
        """

        original_text = text.strip()

        normalized_text = normalize_text(
            original_text,
            COMMANDS.keys(),
        )

        if normalized_text == "":
            return True

        info(
            f"Entrada del usuario: "
            f"{normalized_text}"
        )

        # ---------------------------------------------------------------------
        # 1. CONFIRMACIÓN PENDIENTE
        # ---------------------------------------------------------------------

        # Una respuesta como «sí» o «no» no debe provocar
        # un cambio automático de personalidad antes de
        # resolver la confirmación.
        if self.confirmations.has_pending_confirmation():

            confirmation_result = (
                self._handle_pending_confirmation(
                    normalized_text
                )
            )

            if confirmation_result is not None:
                return confirmation_result

        # ---------------------------------------------------------------------
        # 2. PRIVACIDAD DE MEMORIA PENDIENTE
        # ---------------------------------------------------------------------

        # Una respuesta como «familia», «pareja» o «cancelar»
        # debe procesarse antes de evaluar el modo.
        if self.memory_service.has_pending_memory():

            return (
                self.memory_service
                .process_visibility_answer(
                    normalized_text
                )
            )

        # ---------------------------------------------------------------------
        # 3. GUARDAR UN RECUERDO
        # ---------------------------------------------------------------------

        if self._is_memory_storage_request(
            normalized_text
        ):

            return self._handle_memory_storage_request(
                original_text
            )

        # ---------------------------------------------------------------------
        # 4. CONSULTAR RECUERDOS
        # ---------------------------------------------------------------------

        if self._handle_memory_query(
            original_text
        ):
            return True

        # ---------------------------------------------------------------------
        # 5. EJECUTAR COMANDOS
        # ---------------------------------------------------------------------

        command_result = self._handle_command(
            original_text,
            normalized_text,
        )

        if command_result is not None:
            return command_result

        # ---------------------------------------------------------------------
        # 6. CAMBIO AUTOMÁTICO DE MODO
        # ---------------------------------------------------------------------

        # IdentityManager decide si debe aplicar la sugerencia.
        #
        # No realizará cambios cuando:
        #
        # - El cambio automático esté desactivado.
        # - El usuario haya bloqueado manualmente un modo.
        # - La confianza sea insuficiente.
        mode_selection = (
            self.identity_manager
            .apply_automatic_mode(
                original_text
            )
        )

        info(
            f"Modo sugerido: "
            f"{mode_selection.mode_name}. "
            f"Confianza: "
            f"{mode_selection.confidence:.2f}. "
            f"Modo activo: "
            f"{self.identity_manager.get_active_mode_name()}."
        )

        # ---------------------------------------------------------------------
        # 7. CONVERSACIÓN BÁSICA
        # ---------------------------------------------------------------------

        if self._handle_conversation(
            original_text,
            normalized_text,
        ):
            return True

        # ---------------------------------------------------------------------
        # 8. CONSULTAS ADMINISTRATIVAS DE CONTEXTO
        # ---------------------------------------------------------------------

        if self._handle_user_context_query(
            original_text
        ):
            return True

        # ---------------------------------------------------------------------
        # 9. HERRAMIENTAS LOCALES
        # ---------------------------------------------------------------------

        if self._handle_tool(
            original_text
        ):
            return True

        # ---------------------------------------------------------------------
        # 10. INTELIGENCIA ARTIFICIAL LOCAL
        # ---------------------------------------------------------------------

        if self._handle_ai(
            original_text
        ):
            return True

        # ---------------------------------------------------------------------
        # 11. ENTRADA NO COMPRENDIDA
        # ---------------------------------------------------------------------

        self._show_not_understood(
            normalized_text
        )

        return True
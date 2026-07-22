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


from pathlib import Path
import re


# =============================================================================
# INTELIGENCIA ARTIFICIAL
# =============================================================================

from ai.cache.response_cache import ResponseCache
from ai.context.context_manager import AIContextManager
from ai.models.model_registry import ModelRegistry
from ai.prompts.builder import PromptBuilder
from ai.providers.base_provider import BaseAIProvider
from ai.tools.tool_registry import ToolRegistry as LegacyToolRegistry
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
from core.atlas_social import AtlasSocialMixin
from core.atlas_interuser import AtlasInteruserMixin
from core.atlas_daily import AtlasDailyMixin
from core.atlas_daily_brief import AtlasDailyBriefMixin
from core.atlas_understanding import AtlasUnderstandingMixin
from core.atlas_family import AtlasFamilyMixin
from core.atlas_family_assistance import AtlasFamilyAssistanceMixin
from core.atlas_humor import AtlasHumorMixin
from core.atlas_self_knowledge import AtlasSelfKnowledgeMixin
from core.atlas_tools import AtlasToolsMixin
from core.atlas_telegram import AtlasTelegramMixin
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
from memory.semantic_index import PersonalMemorySemanticIndex
from memory.links import MemoryLinkStore
from memory.long_term import LongTermMemoryService
from memory.workflow.conversation import MemoryWorkflowConversation
from memory.workflow.service import MemoryWorkflowService
from conversation.continuity_store import ConversationContinuityStore

from knowledge.retriever import KnowledgeRetriever
from knowledge.service import KnowledgeService
from knowledge.sources import (
    DriveIndexKnowledgeSource,
    IdentityKnowledgeSource,
    MemoryKnowledgeSource,
    PersonalSemanticMemoryKnowledgeSource,
    LinkedMemoryKnowledgeSource,
    SemanticKnowledgeSource,
)


# =============================================================================
# UTILIDADES
# =============================================================================

from utils.text_normalizer import normalize_text


# =============================================================================
# NUEVO FRAMEWORK DE HERRAMIENTAS
# =============================================================================

from tools.atlas_adapter import AtlasToolAdapter
from tools.filesystem_read import FilesystemReadTool
from tools.google_drive import (
    GoogleDriveReadTool,
    UnavailableGoogleDriveClient,
)
from tools.google_drive_index import (
    GoogleDriveDocumentIndex,
    GoogleDriveIndexTool,
)
from tools.google_drive_rag import (
    GoogleDriveRagTool,
)
from tools.google_drive_semantic import (
    GoogleDriveSemanticIndex,
    GoogleDriveSemanticTool,
    build_embedding_client_from_provider,
)
from tools.google_drive_structure import (
    DriveNavigationService,
    GoogleDriveStructureIndex,
    GoogleDriveStructureTool,
)
from tools.knowledge import KnowledgeTool
from tools.memory_write import MemoryWorkflowTool
from tools.manager import ToolManager
from tools.registry import ToolRegistry as FrameworkToolRegistry
from tools.system_status import SystemStatusTool
from tools.telegram_accounts import TelegramAccountTool
from telegram_interface.identity_linker import TelegramIdentityLinker
from telegram_interface.storage import TelegramStorage
from telegram_interface.audit import TelegramAuditLogger


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
    AtlasSocialMixin,
    AtlasInteruserMixin,
    AtlasDailyMixin,
    AtlasDailyBriefMixin,
    AtlasUnderstandingMixin,
    AtlasFamilyMixin,
    AtlasFamilyAssistanceMixin,
    AtlasSelfKnowledgeMixin,
    AtlasHumorMixin,
    AtlasToolsMixin,
    AtlasTelegramMixin,
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

        # Solo las personas pueden tener perfiles de usuario.
        # Se consulta dinámicamente para cubrir también animales añadidos
        # después del arranque.
        self.users.set_profile_validator(
            lambda name: (
                self.people_manager.find_animal_by_name(name) is None
            )
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

        # Reconstruye al arrancar los perfiles dinámicos persistidos en
        # people.json. Así un familiar dado de alta conserva su perfil tras
        # reiniciar Atlas y puede volver a usar Telegram sin errores.
        self.sync_identity_user_profiles()

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

        # Las preferencias de Daxter/Coco pertenecen al usuario
        # autenticado. Mencionar o identificar a otra persona no debe
        # cambiar la identidad del asistente de la sesión.
        self.identity_manager.load_user(
            self.get_user()
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

        self.memory_workflow_service = MemoryWorkflowService(
            self.memory,
            data_folder=(
                Path(__file__).resolve().parent.parent
                / "data"
                / "memory_workflow"
            ),
            people_manager=self.people_manager,
            relationship_engine=self.relationship_engine,
        )

        self.memory_workflow_conversation = MemoryWorkflowConversation()

        self.memory_links = MemoryLinkStore(
            Path(__file__).resolve().parent.parent
            / "data" / "knowledge" / "memory_links.json",
            self.memory,
        )
        self.long_term_memory = LongTermMemoryService(
            Path(__file__).resolve().parent.parent
            / "data" / "knowledge" / "long_term_memory.json",
            self.memory,
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

        # Sistema de herramientas heredado.
        #
        # Se conserva sin cambios durante la migración para mantener
        # operativo AtlasToolsMixin y todas las herramientas actuales.
        self.tool_registry = LegacyToolRegistry()

        self.tool_selector = ToolSelector(
            self.tool_registry
        )

        # Nuevo Atlas Tools Framework.
        #
        # Utiliza atributos independientes para evitar colisiones con
        # el registro y el selector heredados.
        self.framework_tool_registry = (
            FrameworkToolRegistry()
        )

        self.framework_tool_registry.register(
            SystemStatusTool()
        )

        # Primera herramienta funcional del nuevo framework.
        #
        # La raíz permitida se calcula a partir de este archivo:
        # core/atlas.py -> atlas_core/
        self.framework_tool_registry.register(
            FilesystemReadTool(
                allowed_roots=(
                    Path(__file__).resolve().parent.parent,
                )
            )
        )

        # Integración de Google Drive en modo seguro.
        #
        # Se registra con un cliente no disponible y queda desactivada
        # hasta que una capa de autenticación inyecte un cliente real.
        google_drive_unavailable_client = (
            UnavailableGoogleDriveClient()
        )

        self.framework_tool_registry.register(
            GoogleDriveReadTool(
                google_drive_unavailable_client
            )
        )

        self.google_drive_document_index = (
            GoogleDriveDocumentIndex(
                Path(__file__)
                .resolve()
                .parent
                .parent
                / "data"
                / "integrations"
                / "google_drive"
                / "document_index.json"
            )
        )

        self.google_drive_structure_index = GoogleDriveStructureIndex(
            Path(__file__).resolve().parent.parent
            / "data" / "integrations" / "google_drive" / "structure_index.json"
        )
        self.google_drive_navigation = DriveNavigationService(
            self.google_drive_structure_index
        )

        self.framework_tool_registry.register(
            GoogleDriveStructureTool(
                google_drive_unavailable_client,
                self.google_drive_structure_index,
                self.google_drive_navigation,
            )
        )

        self.framework_tool_registry.register(
            GoogleDriveIndexTool(
                google_drive_unavailable_client,
                self.google_drive_document_index,
                self.google_drive_structure_index,
            )
        )

        self.google_drive_semantic_index = (
            GoogleDriveSemanticIndex(
                Path(__file__)
                .resolve()
                .parent
                .parent
                / "data"
                / "integrations"
                / "google_drive"
                / "semantic_index.json",
                self.google_drive_document_index,
                build_embedding_client_from_provider(
                    self.ai_provider
                ),
            )
        )

        self.personal_memory_semantic_index = PersonalMemorySemanticIndex(
            Path(__file__).resolve().parent.parent
            / "data" / "knowledge" / "personal_memory_semantic.json",
            self.memory,
            build_embedding_client_from_provider(self.ai_provider),
        )
        if self.personal_memory_semantic_index.embedder is not None:
            try:
                self.personal_memory_semantic_index.sync()
            except Exception as exception:
                info(
                    "El índice semántico personal queda pendiente de "
                    f"sincronización: {type(exception).__name__}."
                )

        self.framework_tool_registry.register(
            GoogleDriveSemanticTool(
                self.google_drive_semantic_index
            )
        )

        self.framework_tool_registry.register(
            GoogleDriveRagTool(
                self.google_drive_document_index,
                self.ai_provider,
                self.google_drive_semantic_index,
            )
        )

        self.knowledge_retriever = KnowledgeRetriever(
            (
                MemoryKnowledgeSource(
                    self.memory_retriever,
                    self.users.get_profile,
                ),
                PersonalSemanticMemoryKnowledgeSource(
                    self.personal_memory_semantic_index
                ),
                LinkedMemoryKnowledgeSource(
                    self.memory_links
                ),
                IdentityKnowledgeSource(
                    self.people_manager,
                    self.relationship_engine,
                ),
                DriveIndexKnowledgeSource(
                    self.google_drive_document_index
                ),
                SemanticKnowledgeSource(
                    self.google_drive_semantic_index
                ),
            )
        )

        self.knowledge_service = KnowledgeService(
            self.knowledge_retriever,
            self.ai_provider,
        )

        self.framework_tool_registry.register(
            KnowledgeTool(self.knowledge_service)
        )

        self.framework_tool_registry.register(
            MemoryWorkflowTool(
                self.memory_workflow_service
            )
        )

        # Administracion local de la vinculacion Telegram. El almacen existe
        # aunque el canal no tenga token, pero no inicia red ni polling.
        self.telegram_storage = TelegramStorage(
            Path(__file__).resolve().parent.parent
            / "data" / "integrations" / "telegram" / "state.json"
        )
        self.telegram_identity_linker = TelegramIdentityLinker(
            self.telegram_storage
        )
        self.framework_tool_registry.register(
            TelegramAccountTool(
                self.telegram_identity_linker,
                # UserManager es la fuente canónica de perfiles Atlas.
                # people.json describe personas y relaciones, pero no debe
                # impedir la vinculación de un perfil válido por desajustes
                # temporales de sincronización entre ambos almacenes.
                user_exists=lambda user: (
                    self.users.resolve_user_name(str(user)) is not None
                ),
                audit=TelegramAuditLogger(
                    Path(__file__).resolve().parent.parent
                    / "data" / "integrations" / "telegram" / "audit.jsonl"
                ),
            )
        )

        self.tool_manager = ToolManager(
            self.framework_tool_registry
        )

        # Estado de la integración OAuth.
        self.google_drive_oauth_provider = None
        self.google_drive_oauth_error = None

        # Estado conversacional temporal de Google Drive.
        self.google_drive_conversation = None

        # Restaura una sesión existente sin abrir el navegador.
        # Si faltan dependencias, credenciales o token, Atlas continúa
        # normalmente con la herramienta de Drive desactivada.
        self.configure_google_drive_oauth(
            interactive=False
        )

        # Adaptador seguro entre Atlas y el nuevo framework.
        #
        # En este Sprint todavía no participa automáticamente en
        # Atlas.process(). Su uso queda disponible para pruebas,
        # comandos internos y la migración gradual.
        self.framework_tool_adapter = AtlasToolAdapter(
            self.tool_manager
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

        # Contexto breve compartido entre CLI y Telegram. No sustituye la
        # memoria; solo permite retomar el hilo reciente entre interfaces.
        self.conversation_continuity = ConversationContinuityStore(
            Path(__file__).resolve().parents[1]
            / "data" / "conversation" / "continuity.json"
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

        raw_original_text = text.strip()
        original_text = self._interpret_user_text(raw_original_text)

        normalized_text = normalize_text(
            original_text,
            COMMANDS.keys(),
        )

        if normalized_text == "":
            # Los mensajes formados solo por emojis se quedan vacíos tras la
            # normalización textual. Deben pasar por la conversación social
            # antes de descartarse, especialmente en canales como Telegram.
            if original_text and self._handle_social_conversation(original_text):
                return True
            return True

        request_context = getattr(self, "channel_request_context", None)
        if getattr(request_context, "channel", None) == "telegram":
            logged_text = "[CONTENIDO TELEGRAM OMITIDO]"
        else:
            logged_text = (
                "[CONTENIDO SENSIBLE OMITIDO]"
                if self.memory_workflow_service.detector.contains_secret(original_text)
                else normalized_text
            )
        info(f"Entrada del usuario: {logged_text}")

        # Cambio explícito de usuario en la consola local.
        # Telegram conserva siempre la identidad vinculada a su cuenta.
        request_context = getattr(self, "channel_request_context", None)
        if getattr(request_context, "channel", None) != "telegram":
            user_switch_match = re.match(
                r"^(?:soy|cambiar usuario(?: a)?|cambia(?:r)? "
                r"(?:el )?usuario(?: a)?)\s+(.+?)\s*$",
                self.users._normalize_identity_name(original_text),
            )
            if user_switch_match is not None:
                requested_user = user_switch_match.group(1).strip(" .,:;!?¡¿")
                resolved_user = self.users.resolve_user_name(requested_user)
                if resolved_user is None:
                    print()
                    print(
                        "Ese perfil de usuario no existe en Atlas. "
                        "Usa «listar usuarios» para ver los perfiles disponibles."
                    )
                    return True
                if self.change_user(resolved_user):
                    print()
                    print(f"Hola, {self.get_user()}. He cambiado a tu perfil.")
                return True

        # Conocimiento determinista sobre Atlas, identidades, modos, memoria y vinculación.
        # Debe resolverse antes de la IA para impedir invenciones sobre el propio sistema.
        if self._handle_self_knowledge(original_text):
            return True

        # Los comandos simples y la ayuda deben resolverse antes de los
        # manejadores conversacionales. De lo contrario, palabras como «ayuda»
        # pueden ser absorbidas por la conversación general y no ejecutar el
        # catálogo real de comandos.
        command_result = self._handle_command(
            original_text,
            normalized_text,
        )
        if command_result is not None:
            return command_result

        # Consultas deterministas de perfiles disponibles y usuario autenticado.
        if self._handle_user_management_request(original_text):
            return True

        # Preparación para beta familiar: incorporación guiada, cancelación
        # universal, confirmaciones sensibles, privacidad, incidencias y salud.
        # Debe ejecutarse antes de cualquier confirmación o flujo pendiente.
        if self._handle_family_readiness(original_text):
            return True

        # Las confirmaciones de búsquedas web son por sesión y deben resolverse
        # antes que saludos, memoria, modos o IA. Así «sí» no se interpreta como
        # una conversación nueva ni se pierde entre CLI y Telegram.
        if self._handle_pending_internet_lookup(original_text):
            return True

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

        # Sprint 18: la vinculación local de Telegram es determinista.
        # Nunca debe llegar al modelo de IA, que podría inventar una web o
        # instrucciones inexistentes para introducir el código.
        if self._handle_profile_creation_request(original_text):
            return True

        if self._handle_telegram_link_request(original_text):
            return True

        # Sprint 18.1: mensajes y recordatorios entre usuarios vinculados.
        # Se resuelven de forma determinista y funcionan igual desde CLI y Telegram.
        if self._handle_interuser_request(original_text):
            return True

        # Humor cotidiano clasificado. Se resuelve antes que la IA para que
        # respete el tema pedido y no repita siempre chistes genéricos de IA.
        if self._handle_classified_humor(original_text):
            return True

        # Consultas meteorológicas: siempre se resuelven automáticamente y no
        # pasan por la confirmación genérica de Internet.
        if self._handle_weather(original_text):
            return True

        # Resumen de inicio y cierre del día, compartido por todas las interfaces.
        if self._handle_daily_brief(original_text):
            return True

        # Guías interactivas, accesibilidad y tratamiento seguro de enlaces.
        if self._handle_family_assistance(original_text):
            return True

        # Funciones cotidianas: recordatorios propios, listas, cálculos,
        # redacción y gestión conversacional de memoria.
        if self._handle_daily_life(original_text):
            return True

        # Comprensión humana e interactiva: aclaraciones, hipótesis y seguimiento.
        self._emit_due_wellbeing_followup(original_text)
        if self._handle_pending_understanding(original_text):
            return True

        if self._handle_human_understanding(original_text):
            return True

        # Sprint 13: convierte la intención en una acción estructurada antes
        # de que el flujo heredado pueda escribir directamente.
        if self._handle_memory_workflow(original_text):
            return True

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
        # 6. CONOCIMIENTO UNIFICADO
        # ---------------------------------------------------------------------

        if self._handle_framework_knowledge(
            original_text
        ):
            return True

        # ---------------------------------------------------------------------
        # 7. GOOGLE DRIVE CONVERSACIONAL
        # ---------------------------------------------------------------------

        # Solo intercepta peticiones explícitas relacionadas con Drive.
        # Una búsqueda genérica continúa por el flujo habitual.
        if self._handle_framework_google_drive(
            original_text
        ):
            return True

        # ---------------------------------------------------------------------
        # 8. CAMBIO AUTOMÁTICO DE MODO
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
        # 9. CONVERSACIÓN SOCIAL COTIDIANA
        # ---------------------------------------------------------------------

        if self._handle_social_conversation(original_text):
            return True

        # ---------------------------------------------------------------------
        # 10. CONVERSACIÓN BÁSICA
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

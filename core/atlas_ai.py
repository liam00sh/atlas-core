"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_ai.py

Descripción:
    Contiene la lógica de inteligencia artificial utilizada por Atlas.

    Incluye:

    - Gestión de contextos temporales por interlocutor.
    - Construcción del prompt.
    - Obtención de información real del sistema.
    - Comunicación con el proveedor de IA.
    - Consulta y administración de contextos conversacionales.

    Esta clase se utiliza como mixin de la clase principal Atlas.
===============================================================================
"""
import hashlib
import json

from ai.context.context_manager import AIContextManager

from core.log_manager import info
from core.system_info import format_system_info_for_ai
from core.system_info import get_system_info

from conversation.personality import private_context_denied

from utils.text_normalizer import normalize_text


class AtlasAIMixin:
    """
    Añade a Atlas las funciones relacionadas con IA local.
    """

    @staticmethod
    def _normalize_ai_context_user(
        user: str,
    ) -> str:
        """
        Normaliza un nombre para utilizarlo como clave de contexto.
        """

        if not isinstance(user, str):

            raise TypeError(
                "El usuario del contexto debe ser texto."
            )

        normalized_user = user.strip().casefold()

        if not normalized_user:

            raise ValueError(
                "El usuario del contexto no puede estar vacío."
            )

        return normalized_user

    def _get_current_conversation_user(
        self,
    ) -> str:
        """
        Devuelve la persona que está hablando actualmente.

        Si todavía no existe una identidad conversacional
        reconocida, utiliza el usuario autenticado.
        """

        conversation_identity = getattr(
            self,
            "conversation_identity",
            None,
        )

        if conversation_identity is None:
            return self.get_user()

        conversation_user = (
            conversation_identity
            .get_conversation_owner()
        )

        if conversation_user is None:
            return self.get_user()

        return conversation_user

    def _get_ai_context_for_user(
        self,
        user: str,
    ) -> AIContextManager:
        """
        Devuelve el contexto temporal de un usuario.

        Si todavía no existe, lo crea automáticamente.
        """

        context_key = self._normalize_ai_context_user(
            user
        )

        if context_key not in self.ai_contexts:

            self.ai_contexts[context_key] = (
                AIContextManager(
                    max_messages=(
                        self.ai_context_max_messages
                    )
                )
            )

            info(
                f"Contexto temporal de IA creado "
                f"para {user}."
            )

        return self.ai_contexts[
            context_key
        ]

    def get_current_ai_context(
        self,
    ) -> AIContextManager:
        """
        Devuelve el contexto temporal de la persona
        que está hablando actualmente.

        El contexto pertenece al interlocutor real,
        no necesariamente al usuario autenticado.
        """

        current_conversation_user = (
            self._get_current_conversation_user()
        )

        return self._get_ai_context_for_user(
            current_conversation_user
        )

    def _handle_user_context_query(
        self,
        original_text: str,
    ) -> bool:
        """
        Detecta consultas sobre la conversación temporal
        de otro usuario.

        Ejemplos reconocidos:

            de qué estabas hablando con Saray
            de qué hablabas con Saray
            qué hablaste con Saray
            qué ha hablado Saray
            conversación de Saray
            conversación Saray
            contexto de Saray
            contexto Saray
            contecto Saray

        Devuelve:
            True:
                La consulta ha sido reconocida y procesada.

            False:
                No era una consulta sobre el contexto
                de otro usuario.
        """

        normalized_text = normalize_text(
            original_text
        )

        prefixes = (
            "de que estabas hablando con ",
            "de que hablabas con ",
            "que estabas hablando con ",
            "que hablabas con ",
            "que hablaste con ",
            "que has hablado con ",
            "que ha hablado ",
            "conversacion de ",
            "conversacion ",
            "contexto de ",
            "contexto ",
            "que sabes de la conversacion de ",
            "que sabes del contexto de ",
        )

        requested_user = None

        for prefix in prefixes:

            if normalized_text.startswith(
                prefix
            ):

                requested_user = normalized_text[
                    len(prefix):
                ].strip()

                break

        # La entrada no era una consulta de contexto.
        if not requested_user:
            return False

        resolved_user = self.users.resolve_user_name(
            requested_user
        )

        if resolved_user is None:

            print()

            print(
                f"No conozco ningún usuario llamado "
                f"«{requested_user}»."
            )

            return True

        summary = self.summarize_ai_context_for_user(
            resolved_user
        )

        # None significa que el usuario activo
        # no tiene permiso para acceder.
        if summary is None:

            grammatical_gender = (
                self.get_user_grammatical_gender(
                    resolved_user
                )
            )

            print()

            print(
                private_context_denied(
                    requested_user=resolved_user,
                    grammatical_gender=grammatical_gender,
                )
            )

            return True

        # Cadena vacía significa que sí tiene permiso,
        # pero no hay conversación guardada.
        if not summary:

            print()

            print(
                f"No tengo ninguna conversación temporal "
                f"guardada con {resolved_user}."
            )

            return True

        print()

        print(summary)

        return True

    def _handle_ai(
        self,
        original_text: str,
    ) -> bool:
        """
        Intenta responder mediante la inteligencia artificial local.

        Devuelve:
            True:
                La entrada fue gestionada por la capa de IA.

            False:
                La IA está desactivada o no está disponible.
        """

        if not self.can_use_ai():
            return False

        if self.ai_provider is None:

            info(
                "IA no disponible: "
                "no existe ningún proveedor configurado."
            )

            return False

        if not self.ai_provider.is_available():

            info(
                "IA no disponible: "
                "el proveedor no responde."
            )

            return False

        # ---------------------------------------------------------------------
        # INTERLOCUTOR ACTUAL
        # ---------------------------------------------------------------------

        conversation_user = (
            self._get_current_conversation_user()
        )

        # Nos aseguramos de que IdentityManager tenga cargadas
        # las preferencias de la persona que está hablando.
        if (
            self.identity_manager.get_current_user()
            != conversation_user
        ):

            self.identity_manager.load_user(
                conversation_user
            )

        # ---------------------------------------------------------------------
        # CONTEXTO TEMPORAL DE LA CONVERSACIÓN
        # ---------------------------------------------------------------------

        current_ai_context = (
            self._get_ai_context_for_user(
                conversation_user
            )
        )

        conversation_context = (
            current_ai_context.format_for_prompt()
        )

        # ---------------------------------------------------------------------
        # INFORMACIÓN REAL DEL SISTEMA
        # ---------------------------------------------------------------------

        current_system_info = get_system_info()

        system_information = format_system_info_for_ai(
            current_system_info
        )

        # ---------------------------------------------------------------------
        # MEMORIA PERSISTENTE RELEVANTE
        # ---------------------------------------------------------------------

        # El propietario de los recuerdos sigue siendo
        # el usuario autenticado de la sesión.
        memory_owner = self.get_user()

        # La persona que consulta los recuerdos es siempre
        # el interlocutor actual.
        memory_viewer = (
            self.conversation_identity
            .get_memory_viewer()
        )

        if memory_viewer is None:

            memory_viewer = conversation_user

        viewer_profile = (
            self.users.get_profile(
                memory_viewer
            )
        )

        relevant_memories = (
            self.memory_retriever.find(
                query=original_text,
                owner=memory_owner,
                viewer=memory_viewer,
                viewer_profile=viewer_profile,
                limit=5,
            )
        )

        relevant_memories_text = (
            self.memory_retriever.format_for_prompt(
                relevant_memories
            )
        )

        if relevant_memories:

            info(
                f"Recuerdos añadidos al prompt de IA. "
                f"Propietario: {memory_owner}. "
                f"Consultante: {memory_viewer}. "
                f"Cantidad: {len(relevant_memories)}."
            )

        # ---------------------------------------------------------------------
        # IDENTIDAD DE LA PERSONA QUE HABLA
        # ---------------------------------------------------------------------

        conversation_identity_context = (
            self.conversation_identity
            .build_prompt_context()
        )

        # ---------------------------------------------------------------------
        # IDENTIDAD DEL ASISTENTE
        # ---------------------------------------------------------------------

        assistant_identity_context = (
            self.identity_manager
            .build_prompt_context()
        )

        active_assistant_name = (
            self.identity_manager
            .get_active_display_name()
        )

        # Ambos contextos se mantienen separados para que
        # el modelo no confunda al interlocutor con el asistente.
        identity_context = "\n\n".join(
            [
                (
                    "IDENTIDAD DE LA PERSONA "
                    "QUE ESTÁ HABLANDO\n\n"
                    f"{conversation_identity_context}"
                ),
                (
                    "IDENTIDAD Y PERSONALIDAD "
                    "DEL ASISTENTE\n\n"
                    f"{assistant_identity_context}"
                ),
            ]
        )

        # ---------------------------------------------------------------------
        # CONSTRUCCIÓN DEL PROMPT
        # ---------------------------------------------------------------------

        prompt = self.prompt_builder.build(
            user_message=original_text,
            user_name=conversation_user,
            project_name=self.get_project(),
            assistant_name=active_assistant_name,
            atlas_version=self.get_version(),
            capabilities=self.get_capabilities(),
            system_information=system_information,
            identity_context=identity_context,
            relevant_memories=relevant_memories_text,
            conversation_context=conversation_context,
        )

        try:

            response = self.ai_provider.generate(
                prompt
            )

        except (
            RuntimeError,
            ValueError,
        ) as exception:

            info(
                f"Error de IA: {exception}"
            )

            print()
            print(
                "No he podido consultar la inteligencia "
                "artificial local."
            )

            return True

        current_ai_context.add_message(
            role="user",
            content=original_text,
        )

        current_ai_context.add_message(
            role="assistant",
            content=response,
        )

        info(
            f"Respuesta generada por IA local. "
            f"Proveedor: "
            f"{self.ai_provider.get_provider_name()}. "
            f"Modelo: "
            f"{self.ai_provider.get_model_name()}."
        )

        print()
        print(response)

        return True

    def clear_ai_context(
        self,
    ) -> None:
        """
        Elimina el contexto temporal de la persona
        que está hablando actualmente.
        """

        current_conversation_user = (
            self._get_current_conversation_user()
        )

        current_context = (
            self._get_ai_context_for_user(
                current_conversation_user
            )
        )

        current_context.clear()

        info(
            f"Contexto temporal de IA eliminado "
            f"para {current_conversation_user}."
        )

    def clear_ai_context_for_user(
        self,
        user: str,
    ) -> bool:
        """
        Elimina el contexto temporal de un usuario.

        El propio usuario puede borrar su contexto.
        El propietario del sistema puede borrar cualquiera.
        """

        current_user = (
            self._get_current_conversation_user()
        )

        same_user = (
            self._normalize_ai_context_user(
                current_user
            )
            == self._normalize_ai_context_user(
                user
            )
        )

        if (
            not same_user
            and not self.can_manage_user_contexts()
        ):

            info(
                f"Intento no autorizado de eliminar "
                f"el contexto de {user}. "
                f"Solicitante: {current_user}."
            )

            return False

        context_key = self._normalize_ai_context_user(
            user
        )

        user_context = self.ai_contexts.get(
            context_key
        )

        if user_context is not None:
            user_context.clear()

        info(
            f"Contexto temporal de IA eliminado. "
            f"Solicitante: {current_user}. "
            f"Propietario: {user}."
        )

        return True

    def get_ai_context_size(
        self,
    ) -> int:
        """
        Devuelve la cantidad de mensajes del interlocutor actual.
        """

        return (
            self.get_current_ai_context()
            .count_messages()
        )

    def get_ai_context_size_for_user(
        self,
        user: str,
    ) -> int:
        """
        Devuelve la cantidad de mensajes de un usuario.
        """

        return (
            self._get_ai_context_for_user(
                user
            ).count_messages()
        )

    def get_ai_context_users(
        self,
    ) -> list[str]:
        """
        Devuelve las claves de interlocutores con contexto creado.
        """

        return sorted(
            self.ai_contexts.keys()
        )

    def can_manage_user_contexts(
        self,
    ) -> bool:
        """
        Indica si la persona que está hablando puede
        administrar contextos de otros usuarios.

        Los permisos pertenecen al interlocutor real,
        no al usuario autenticado de la sesión.
        """

        conversation_identity = getattr(
            self,
            "conversation_identity",
            None,
        )

        permission_viewer = None

        if conversation_identity is not None:
            permission_viewer = (
                conversation_identity
                .get_permission_viewer()
            )

        if permission_viewer is None:
            permission_viewer = self.get_user()

        current_profile = self.users.get_profile(
            permission_viewer
        )

        return "owner" in current_profile.get(
            "roles",
            [],
        )

    def get_ai_context_messages_for_user(
        self,
        user: str,
    ) -> list[dict[str, str]] | None:
        """
        Devuelve una copia del contexto de un usuario.

        Devuelve None cuando no existe autorización.
        """

        current_user = (
            self._get_current_conversation_user()
        )

        same_user = (
            self._normalize_ai_context_user(
                current_user
            )
            == self._normalize_ai_context_user(
                user
            )
        )

        if (
            not same_user
            and not self.can_manage_user_contexts()
        ):

            info(
                f"Acceso denegado al contexto de {user}. "
                f"Solicitante: {current_user}."
            )

            return None

        context_key = self._normalize_ai_context_user(
            user
        )

        user_context = self.ai_contexts.get(
            context_key
        )

        if user_context is None:
            return []

        info(
            f"Contexto de IA consultado. "
            f"Solicitante: {current_user}. "
            f"Propietario: {user}."
        )

        return user_context.get_messages()

    def _format_context_messages(
        self,
        user: str,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Convierte una colección de mensajes en texto legible.

        Este formato se utiliza internamente para enviar
        una conversación al modelo y generar un resumen.
        """

        assistant_name = (
            self.identity_manager
            .get_active_display_name()
        )

        role_labels = {
            "user": user,
            "assistant": assistant_name,
            "system": "Sistema",
        }

        formatted_messages = []

        for message in messages:

            role = message.get(
                "role",
                "unknown",
            )

            content = message.get(
                "content",
                "",
            ).strip()

            if not content:
                continue

            label = role_labels.get(
                role,
                role,
            )

            formatted_messages.append(
                f"{label}: {content}"
            )

        return "\n\n".join(
            formatted_messages
        )

    def format_ai_context_for_user(
        self,
        user: str,
    ) -> str | None:
        """
        Devuelve el contexto completo de un usuario
        en formato legible.

        Este método conserva el historial literal y puede utilizarse
        para tareas administrativas o de depuración.
        """

        messages = (
            self.get_ai_context_messages_for_user(
                user
            )
        )

        if messages is None:
            return None

        if not messages:
            return ""

        return self._format_context_messages(
            user=user,
            messages=messages,
        )

    def _build_context_summary_cache_key(
        self,
        user: str,
        messages: list[dict[str, str]],
    ) -> str:
        """
        Crea una clave única para el resumen de una conversación.

        La clave cambia automáticamente cuando:

        - Se añaden mensajes.
        - Se modifica el contenido.
        - Se cambia de modelo.
        """

        serialized_messages = json.dumps(
            messages,
            ensure_ascii=False,
            sort_keys=True,
        )

        context_hash = hashlib.sha256(
            serialized_messages.encode(
                "utf-8"
            )
        ).hexdigest()

        model_name = (
            self.ai_provider.get_model_name()
            if self.ai_provider is not None
            else "no-provider"
        )

        normalized_user = (
            self._normalize_ai_context_user(
                user
            )
        )

        assistant_identity_name = (
            self.identity_manager
            .get_active_identity_name()
        )

        return (
            f"context-summary:"
            f"{normalized_user}:"
            f"{assistant_identity_name}:"
            f"{model_name}:"
            f"{context_hash}"
        )

    def summarize_ai_context_for_user(
        self,
        user: str,
    ) -> str | None:
        """
        Genera un resumen natural de la conversación
        mantenida con un usuario.

        El resumen indica:

        - Qué preguntó el usuario.
        - Qué se le respondió.
        - Si pidió realizar alguna acción.
        - Si quedó algo pendiente.

        No devuelve una copia literal del historial.
        """

        messages = (
            self.get_ai_context_messages_for_user(
                user
            )
        )

        if messages is None:
            return None

        if not messages:
            return ""

        if (
            self.ai_provider is None
            or not self.ai_provider.is_available()
        ):

            info(
                f"No se pudo resumir el contexto de {user}: "
                "el proveedor de IA no está disponible."
            )

            return (
                f"{user} mantuvo una conversación conmigo, "
                "pero ahora mismo no puedo preparar un resumen "
                "fiable porque la inteligencia artificial local "
                "no está disponible."
            )

        cache_key = (
            self._build_context_summary_cache_key(
                user=user,
                messages=messages,
            )
        )

        cached_summary = self.ai_cache.get(
            cache_key
        )

        if cached_summary is not None:

            info(
                f"Resumen de contexto recuperado "
                f"desde caché para {user}."
            )

            return cached_summary

        summary = (
            self._format_context_messages(
                user=user,
                messages=messages,
            )
        )

        active_assistant_name = (
            self.identity_manager
            .get_active_display_name()
        )

        summary_prompt = (
            f"Eres {active_assistant_name}, una identidad "
            f"del asistente del Proyecto Atlas.\n\n"

            f"Resume brevemente la conversación que mantuviste "
            f"con {user}.\n\n"

            "Debes explicar de forma natural:\n"
            "- Qué te preguntó o pidió.\n"
            "- Qué le respondiste.\n"
            "- Si realizaste alguna acción.\n"
            "- Si quedó algo pendiente.\n\n"

            "No copies literalmente toda la conversación.\n"
            "No inventes información.\n"
            "No añadas detalles que no aparezcan en el historial.\n"

            f"Habla en primera persona como "
            f"{active_assistant_name}.\n"

            "Utiliza uno o dos párrafos breves.\n\n"

            "CONVERSACIÓN:\n\n"

            f"{summary}"
        )

        try:

            summary = self.ai_provider.generate(
                summary_prompt
            ).strip()

        except (
            RuntimeError,
            ValueError,
        ) as exception:

            info(
                f"No se pudo resumir el contexto "
                f"de {user}: {exception}"
            )

            return (
                f"{user} mantuvo una conversación conmigo, "
                "pero ahora mismo no he podido preparar "
                "un resumen fiable."
            )

        self.ai_cache.set(
            key=cache_key,
            value=summary,
            ttl_seconds=600,
        )

        info(
            f"Resumen de contexto almacenado "
            f"en caché para {user}."
        )

        return summary

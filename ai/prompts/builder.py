"""
===============================================================================
Proyecto Atlas
Archivo: ai/prompts/builder.py

Descripción:
    Construye el prompt completo que Atlas envía al modelo de IA.

    Combina:

    - Prompt base del sistema.
    - Información actual del proyecto.
    - Identidad activa del asistente.
    - Modo de personalidad activo.
    - Persona que está hablando.
    - Usuario autenticado de la sesión.
    - Capacidades realmente disponibles.
    - Información actual obtenida del sistema operativo.
    - Recuerdos autorizados y relevantes.
    - Contexto conversacional reciente.
    - Mensaje actual del interlocutor.

    Este módulo no decide:

    - Qué identidad está activa.
    - Qué modo debe utilizarse.
    - Qué persona está hablando.
    - Qué recuerdos son accesibles.
    - Qué permisos tiene el interlocutor.

    Toda esa información debe llegar previamente validada
    desde los gestores correspondientes.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.prompts.system_prompt import BASE_SYSTEM_PROMPT


# =============================================================================
# CONSTRUCTOR DE PROMPTS
# =============================================================================

class PromptBuilder:
    """
    Construye el prompt final enviado al modelo de lenguaje.
    """

    def __init__(
        self,
        system_prompt: str = BASE_SYSTEM_PROMPT,
    ) -> None:
        """
        Inicializa el constructor de prompts.

        Parámetros:
            system_prompt:
                Prompt base utilizado como primera sección.
        """

        normalized_system_prompt = (
            system_prompt.strip()
        )

        if not normalized_system_prompt:

            raise ValueError(
                "El prompt del sistema "
                "no puede estar vacío."
            )

        self.system_prompt = (
            normalized_system_prompt
        )

    # =========================================================================
    # CAPACIDADES
    # =========================================================================

    @staticmethod
    def _format_capabilities(
        capabilities: dict,
    ) -> str:
        """
        Convierte el diccionario de capacidades en texto legible.

        Parámetros:
            capabilities:
                Diccionario de capacidades de Atlas.

        Devuelve:
            str:
                Capacidades formateadas para el prompt.
        """

        if not capabilities:

            return (
                "No se han proporcionado capacidades."
            )

        lines = []

        for name, data in capabilities.items():

            if not isinstance(
                data,
                dict,
            ):

                continue

            enabled = bool(
                data.get(
                    "enabled",
                    False,
                )
            )

            state = (
                "Disponible"
                if enabled
                else "No disponible"
            )

            description = str(
                data.get(
                    "description",
                    "",
                )
            ).strip()

            line = (
                f"- {name}: {state}"
            )

            if description:

                line += (
                    f". {description}"
                )

            lines.append(
                line
            )

        if not lines:

            return (
                "No se han proporcionado "
                "capacidades válidas."
            )

        return "\n".join(
            lines
        )

    # =========================================================================
    # CONSTRUCCIÓN DEL PROMPT
    # =========================================================================

    def build(
        self,
        user_message: str,
        user_name: str,
        project_name: str,
        assistant_name: str,
        atlas_version: str,
        capabilities: dict,
        system_information: str = "",
        identity_context: str = "",
        relevant_memories: str = "",
        conversation_context: str = "",
    ) -> str:
        """
        Construye el prompt final.

        Parámetros:
            user_message:
                Mensaje actual de la persona que habla.

            user_name:
                Nombre del interlocutor actual.

                No tiene por qué coincidir con el usuario
                autenticado de la sesión.

            project_name:
                Nombre del proyecto.

            assistant_name:
                Nombre visible de la identidad activa.

                Ejemplos:

                    Daxter
                    Coco

            atlas_version:
                Versión actual de Atlas.

            capabilities:
                Capacidades realmente disponibles.

            system_information:
                Información obtenida directamente
                del sistema operativo.

            identity_context:
                Contexto combinado que describe:

                - Usuario autenticado.
                - Persona que está hablando.
                - Identidad utilizada para permisos.
                - Identidad activa del asistente.
                - Modo de personalidad activo.
                - Reglas de comportamiento.

            relevant_memories:
                Recuerdos persistentes previamente
                autorizados y seleccionados.

            conversation_context:
                Conversación reciente del interlocutor
                actual, ya formateada.

        Devuelve:
            str:
                Prompt completo.
        """

        # ---------------------------------------------------------------------
        # NORMALIZACIÓN
        # ---------------------------------------------------------------------

        user_message = user_message.strip()

        user_name = user_name.strip()

        project_name = project_name.strip()

        assistant_name = assistant_name.strip()

        atlas_version = atlas_version.strip()

        system_information = (
            system_information.strip()
        )

        identity_context = (
            identity_context.strip()
        )

        relevant_memories = (
            relevant_memories.strip()
        )

        conversation_context = (
            conversation_context.strip()
        )

        # ---------------------------------------------------------------------
        # VALIDACIONES
        # ---------------------------------------------------------------------

        if not user_message:

            raise ValueError(
                "El mensaje del usuario "
                "no puede estar vacío."
            )

        if not user_name:

            raise ValueError(
                "El nombre del interlocutor "
                "no puede estar vacío."
            )

        if not project_name:

            raise ValueError(
                "El nombre del proyecto "
                "no puede estar vacío."
            )

        if not assistant_name:

            raise ValueError(
                "El nombre del asistente "
                "no puede estar vacío."
            )

        if not atlas_version:

            raise ValueError(
                "La versión de Atlas "
                "no puede estar vacía."
            )

        # ---------------------------------------------------------------------
        # CAPACIDADES
        # ---------------------------------------------------------------------

        capabilities_text = (
            self._format_capabilities(
                capabilities
            )
        )

        # ---------------------------------------------------------------------
        # SECCIONES PRINCIPALES
        # ---------------------------------------------------------------------

        sections = [
            self.system_prompt,

            (
                "INFORMACIÓN ACTUAL DE ATLAS\n\n"

                f"Proyecto: {project_name}\n"
                f"Identidad activa del asistente: "
                f"{assistant_name}\n"
                f"Versión de Atlas: {atlas_version}\n"
                f"Persona que está hablando: {user_name}"
            ),

            (
                "CAPACIDADES REALES DE ATLAS\n\n"

                f"{capabilities_text}\n\n"

                "Estas capacidades representan el estado real "
                "del sistema. No afirmes poder realizar una acción "
                "cuando la capacidad correspondiente figure como "
                "no disponible."
            ),
        ]

        # ---------------------------------------------------------------------
        # IDENTIDADES Y PERMISOS
        # ---------------------------------------------------------------------

        if identity_context:

            sections.append(
                (
                    "IDENTIDADES, PERSONALIDAD Y PERMISOS\n\n"

                    f"{identity_context}\n\n"

                    "Reglas obligatorias:\n"

                    "- Mantén separada la identidad del asistente "
                    "de la identidad de la persona que habla.\n"

                    "- No confundas a Daxter o Coco con el usuario.\n"

                    "- El usuario autenticado mantiene abierta "
                    "la sesión, pero no tiene por qué ser quien "
                    "está hablando.\n"

                    "- Los permisos, la privacidad y el acceso "
                    "a recuerdos corresponden al interlocutor real.\n"

                    "- Una persona invitada no hereda los permisos "
                    "del propietario de la sesión.\n"

                    "- Mantén la identidad y el modo activos durante "
                    "toda la respuesta.\n"

                    "- El modo modifica el comportamiento, pero no "
                    "sustituye la personalidad de la identidad activa."
                )
            )

        # ---------------------------------------------------------------------
        # INFORMACIÓN REAL DEL SISTEMA
        # ---------------------------------------------------------------------

        if system_information:

            sections.append(
                (
                    "INFORMACIÓN REAL DEL SISTEMA\n\n"

                    f"{system_information}\n\n"

                    "Estos datos proceden directamente del sistema "
                    "operativo y deben considerarse la fuente válida "
                    "para la respuesta actual.\n\n"

                    "No los sustituyas por datos aprendidos durante "
                    "el entrenamiento del modelo.\n"

                    "No inventes valores que no aparezcan en esta sección."
                )
            )

        # ---------------------------------------------------------------------
        # MEMORIA PERSISTENTE
        # ---------------------------------------------------------------------

        if relevant_memories:

            sections.append(
                (
                    "RECUERDOS AUTORIZADOS Y RELEVANTES\n\n"

                    f"{relevant_memories}\n\n"

                    "Estos recuerdos han sido seleccionados previamente "
                    "por Atlas y el interlocutor actual tiene permiso "
                    "para utilizarlos.\n\n"

                    "Reglas:\n"

                    "- Utilízalos únicamente cuando sean relevantes "
                    "para la petición actual.\n"

                    "- No inventes recuerdos.\n"

                    "- No añadas información que no aparezca en ellos.\n"

                    "- No reveles niveles internos de privacidad.\n"

                    "- No expliques las reglas internas de acceso.\n"

                    "- No confundas estos recuerdos persistentes "
                    "con la conversación reciente.\n"

                    "- Si no responden realmente a la pregunta, "
                    "ignóralos.\n"

                    "- No afirmes recordar información que no aparezca "
                    "en esta sección o en la conversación reciente."
                )
            )

        # ---------------------------------------------------------------------
        # CONTEXTO CONVERSACIONAL
        # ---------------------------------------------------------------------

        if conversation_context:

            sections.append(
                (
                    "CONVERSACIÓN RECIENTE DEL INTERLOCUTOR\n\n"

                    f"{conversation_context}\n\n"

                    "Utiliza esta conversación únicamente para mantener "
                    "la continuidad del diálogo actual.\n"

                    "No atribuyas estos mensajes a otra persona."
                )
            )

        # ---------------------------------------------------------------------
        # MENSAJE ACTUAL
        # ---------------------------------------------------------------------

        sections.append(
            (
                "MENSAJE ACTUAL DEL INTERLOCUTOR\n\n"

                f"{user_name}: {user_message}"
            )
        )

        # ---------------------------------------------------------------------
        # INSTRUCCIÓN FINAL
        # ---------------------------------------------------------------------

        sections.append(
            (
                "INSTRUCCIÓN FINAL\n\n"

                f"Responde ahora como {assistant_name}, respetando "
                "la identidad y el modo activos descritos anteriormente.\n\n"

                "Responde a la persona que está hablando actualmente.\n"

                "No inventes información actual que no aparezca "
                "en los datos proporcionados.\n"

                "No afirmes recordar algo si no aparece en los recuerdos "
                "autorizados o en la conversación reciente.\n"

                "No reveles información privada ni concedas permisos "
                "basándote únicamente en el usuario que mantiene abierta "
                "la sesión.\n"

                "Prioriza siempre la seguridad, la privacidad, "
                "la exactitud y la utilidad de la respuesta."
            )
        )

        return "\n\n".join(
            sections
        )
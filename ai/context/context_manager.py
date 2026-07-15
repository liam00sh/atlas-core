"""
===============================================================================
Proyecto Atlas
Archivo: ai/context/context_manager.py

Descripción:
    Gestiona el contexto temporal de conversación utilizado por la IA.

    Este contexto permite comprender referencias como:

        Usuario:
            ¿Qué es Docker?

        Usuario después:
            ¿Y para qué lo usaremos en Atlas?

    No sustituye al sistema de memoria persistente.

    Los datos actuales del sistema, como fecha y hora, no se almacenan
    aquí. Se obtienen dinámicamente antes de construir cada prompt.

===============================================================================
"""


class AIContextManager:
    """
    Gestiona los mensajes recientes de una conversación.
    """

    VALID_ROLES = {
        "user",
        "assistant",
        "system",
    }

    def __init__(
        self,
        max_messages: int = 10,
    ) -> None:
        """
        Inicializa el contexto.

        Parámetros:
            max_messages:
                Número máximo de mensajes conservados.
        """

        if max_messages < 1:
            raise ValueError(
                "max_messages debe ser mayor que cero."
            )

        self.max_messages = max_messages

        self.messages: list[dict[str, str]] = []

    def add_message(
        self,
        role: str,
        content: str,
    ) -> None:
        """
        Añade un mensaje al contexto.
        """

        role = role.strip().lower()
        content = content.strip()

        if role not in self.VALID_ROLES:
            raise ValueError(
                f"Rol de contexto no válido: {role}"
            )

        if not content:
            raise ValueError(
                "El contenido del mensaje no puede estar vacío."
            )

        self.messages.append(
            {
                "role": role,
                "content": content,
            }
        )

        self._trim()

    def _trim(self) -> None:
        """
        Elimina los mensajes más antiguos cuando se supera el límite.
        """

        if len(self.messages) <= self.max_messages:
            return

        self.messages = self.messages[
            -self.max_messages:
        ]

    def get_messages(
        self,
    ) -> list[dict[str, str]]:
        """
        Devuelve una copia de los mensajes.
        """

        return [
            message.copy()
            for message in self.messages
        ]

    def format_for_prompt(
        self,
    ) -> str:
        """
        Convierte los mensajes en texto para PromptBuilder.
        """

        role_labels = {
            "user": "Usuario",
            "assistant": "Daxter",
            "system": "Sistema",
        }

        formatted_messages = []

        for message in self.messages:

            label = role_labels.get(
                message["role"],
                message["role"],
            )

            formatted_messages.append(
                f"{label}: {message['content']}"
            )

        return "\n\n".join(
            formatted_messages
        )

    def clear(
        self,
    ) -> None:
        """
        Elimina el contexto temporal.
        """

        self.messages.clear()

    def count_messages(
        self,
    ) -> int:
        """
        Devuelve la cantidad de mensajes almacenados.
        """

        return len(self.messages)

    def is_empty(
        self,
    ) -> bool:
        """
        Indica si no hay mensajes en el contexto.
        """

        return not self.messages
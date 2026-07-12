"""
===============================================================================
Proyecto Atlas
Archivo: ai/context/context_manager.py

Descripción:
    Gestionará la información contextual enviada a los modelos de IA.

    En futuras fases podrá combinar:
        - Usuario activo.
        - Conversación reciente.
        - Memoria persistente.
        - Capacidades de Atlas.
        - Estado del sistema.
        - Proyecto activo.

Estado:
    Preparado para la Fase 3.
===============================================================================
"""


class AIContextManager:
    """
    Gestor provisional del contexto de inteligencia artificial.
    """

    def __init__(self):
        """
        Inicializa un contexto vacío.
        """

        self.messages = []

    def add_message(
        self,
        role: str,
        content: str,
    ) -> None:
        """
        Añade un mensaje al contexto temporal.

        Parámetros:
            role:
                Rol del mensaje, por ejemplo: user, assistant o system.

            content:
                Texto del mensaje.
        """

        self.messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    def get_messages(self) -> list[dict]:
        """
        Devuelve una copia de los mensajes almacenados.
        """

        return self.messages.copy()

    def clear(self) -> None:
        """
        Elimina todo el contexto temporal.
        """

        self.messages.clear()

    def count_messages(self) -> int:
        """
        Devuelve la cantidad de mensajes almacenados.
        """

        return len(self.messages)

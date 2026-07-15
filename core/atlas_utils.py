"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_utils.py

Descripción:
    Contiene utilidades auxiliares del flujo principal de Atlas.

    Incluye:

    - Conversación básica.
    - Respuesta para entradas no comprendidas.

    Esta clase se utiliza como mixin de la clase principal Atlas.
===============================================================================
"""


from conversation.intent import detect
from conversation.personality import not_understood

from core.log_manager import info


class AtlasUtilsMixin:
    """
    Añade utilidades conversacionales al núcleo.
    """

    @staticmethod
    def _handle_conversation(
        original_text: str,
        normalized_text: str,
    ) -> bool:
        """
        Muestra una respuesta de conversación básica si existe.
        """

        response = detect(
            original_text
        )

        if not response:
            return False

        info(
            f"Conversación: {normalized_text}"
        )

        print()
        print(response)

        return True

    @staticmethod
    def _show_not_understood(
        normalized_text: str,
    ) -> None:
        """
        Registra y muestra una entrada no comprendida.
        """

        info(
            f"No entendido: {normalized_text}"
        )

        print()
        print(not_understood())
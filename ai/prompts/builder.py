"""
===============================================================================
Proyecto Atlas
Archivo: ai/prompts/builder.py

Descripción:
    Será responsable de construir el prompt completo que se enviará
    al modelo de inteligencia artificial.

    En el futuro combinará:
        - Prompt del sistema.
        - Usuario activo.
        - Personalidad.
        - Capacidades reales.
        - Memoria.
        - Contexto reciente.
        - Petición actual.

Estado:
    Preparado para la Fase 3.
===============================================================================
"""

from ai.prompts.system_prompt import BASE_SYSTEM_PROMPT


class PromptBuilder:
    """
    Constructor provisional de prompts.
    """

    def build(
        self,
        user_message: str,
        context: str = "",
    ) -> str:
        """
        Construye un prompt básico.

        Todavía no se envía a ningún modelo.
        """

        sections = [
            BASE_SYSTEM_PROMPT,
        ]

        if context:
            sections.append(
                f"Contexto:\n{context}"
            )

        sections.append(
            f"Usuario:\n{user_message}"
        )

        return "\n\n".join(sections)

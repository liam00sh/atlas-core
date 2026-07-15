"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_capabilities.py

Descripción:
    Contiene los métodos de consulta de capacidades de Atlas.

    Esta clase se utiliza como mixin de la clase principal Atlas.
===============================================================================
"""


class AtlasCapabilitiesMixin:
    """
    Añade los métodos de consulta de capacidades.
    """

    def can_chat(self) -> bool:
        """Indica si la conversación básica está disponible."""

        return self.capabilities.is_enabled(
            "chat"
        )

    def can_use_memory(self) -> bool:
        """Indica si la memoria está disponible."""

        return self.capabilities.is_enabled(
            "memory"
        )

    def can_use_ai(self) -> bool:
        """Indica si la inteligencia artificial está disponible."""

        return self.capabilities.is_enabled(
            "ai"
        )

    def can_use_voice(self) -> bool:
        """Indica si la voz está disponible."""

        return self.capabilities.is_enabled(
            "voice"
        )

    def can_use_tools(self) -> bool:
        """Indica si las herramientas de IA están disponibles."""

        return self.capabilities.is_enabled(
            "tools"
        )

    def can_use_automation(self) -> bool:
        """Indica si la automatización está disponible."""

        return self.capabilities.is_enabled(
            "automation"
        )

    def can_access_internet(self) -> bool:
        """Indica si Atlas tiene acceso a Internet."""

        return self.capabilities.is_enabled(
            "internet"
        )

    def get_capabilities(self) -> dict:
        """Devuelve todas las capacidades conocidas."""

        return self.capabilities.get_all()
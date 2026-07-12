"""
===============================================================================
Proyecto Atlas
Archivo: capabilities/capabilities.py

Descripción:
    Define las capacidades reales disponibles en Atlas.

    Este módulo permite que el núcleo conozca qué funciones están
    activadas y evita que futuras capas de IA inventen herramientas
    o posibilidades inexistentes.

Estado:
    Activo durante la Fase 2.
===============================================================================
"""


CAPABILITIES = {
    "chat": {
        "enabled": True,
        "description": (
            "Conversación básica basada en reglas."
        ),
    },
    "memory": {
        "enabled": True,
        "description": (
            "Memoria persistente con permisos "
            "y niveles de visibilidad."
        ),
    },
    "ai": {
        "enabled": False,
        "description": (
            "Inteligencia artificial local."
        ),
    },
    "voice": {
        "enabled": False,
        "description": (
            "Reconocimiento y síntesis de voz."
        ),
    },
    "tools": {
        "enabled": False,
        "description": (
            "Herramientas ejecutables por la IA."
        ),
    },
    "automation": {
        "enabled": False,
        "description": (
            "Automatización de tareas y dispositivos."
        ),
    },
    "internet": {
        "enabled": False,
        "description": (
            "Acceso externo a Internet."
        ),
    },
}


class CapabilityManager:
    """
    Gestiona las capacidades activadas en Atlas.
    """

    def __init__(self):
        """
        Crea una copia local de las capacidades.

        De esta forma la instancia puede modificarlas sin alterar
        directamente la constante original.
        """

        self.capabilities = {
            name: data.copy()
            for name, data in CAPABILITIES.items()
        }

    def is_enabled(
        self,
        capability: str,
    ) -> bool:
        """
        Comprueba si una capacidad está activada.
        """

        capability_data = self.capabilities.get(
            capability
        )

        if capability_data is None:
            return False

        return bool(
            capability_data.get(
                "enabled",
                False,
            )
        )

    def enable(
        self,
        capability: str,
    ) -> bool:
        """
        Activa una capacidad existente.

        Devuelve False si no existe.
        """

        if capability not in self.capabilities:
            return False

        self.capabilities[
            capability
        ]["enabled"] = True

        return True

    def disable(
        self,
        capability: str,
    ) -> bool:
        """
        Desactiva una capacidad existente.

        Devuelve False si no existe.
        """

        if capability not in self.capabilities:
            return False

        self.capabilities[
            capability
        ]["enabled"] = False

        return True

    def get_capability(
        self,
        capability: str,
    ) -> dict | None:
        """
        Devuelve los datos de una capacidad.
        """

        capability_data = self.capabilities.get(
            capability
        )

        if capability_data is None:
            return None

        return capability_data.copy()

    def get_all(
        self,
    ) -> dict:
        """
        Devuelve todas las capacidades.
        """

        return {
            name: data.copy()
            for name, data in self.capabilities.items()
        }

    def get_enabled(
        self,
    ) -> list[str]:
        """
        Devuelve los nombres de las capacidades activadas.
        """

        return [
            name
            for name, data in self.capabilities.items()
            if data.get("enabled", False)
        ]

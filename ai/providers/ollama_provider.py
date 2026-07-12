"""
===============================================================================
Proyecto Atlas
Archivo: ai/providers/ollama_provider.py

Descripción:
    Contendrá la integración entre Atlas y Ollama.

    En futuras versiones será responsable de:
        - Comprobar si Ollama está disponible.
        - Seleccionar un modelo local.
        - Enviar prompts.
        - Recibir respuestas.
        - Gestionar errores de conexión.

Estado:
    Reservado para la Fase 3.
    Ollama todavía no está conectado.
===============================================================================
"""

from ai.providers.base_provider import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """
    Proveedor preparado para la futura integración con Ollama.

    Actualmente todos sus métodos indican que el proveedor
    no está disponible.
    """

    def __init__(
        self,
        model_name: str | None = None,
    ):
        """
        Inicializa la configuración futura de Ollama.

        Parámetros:
            model_name:
                Nombre del modelo que se utilizará cuando
                Ollama esté integrado.
        """

        self.model_name = model_name

    def is_available(self) -> bool:
        """
        Ollama todavía no está conectado a Atlas.
        """

        return False

    def generate(
        self,
        prompt: str,
    ) -> str:
        """
        Impide utilizar Ollama antes de su implementación.
        """

        raise RuntimeError(
            "Ollama todavía no está integrado en Atlas."
        )

    def get_provider_name(self) -> str:
        """
        Devuelve el nombre identificativo del proveedor.
        """

        return "Ollama"

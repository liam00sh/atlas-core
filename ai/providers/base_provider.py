"""
===============================================================================
Proyecto Atlas
Archivo: ai/providers/base_provider.py

Descripción:
    Define la interfaz común que deben implementar todos los proveedores
    de inteligencia artificial compatibles con Atlas.

    El núcleo no debería depender directamente de Ollama, OpenAI,
    LM Studio u otro motor concreto.

    Atlas trabajará siempre con un proveedor que respete esta interfaz.

===============================================================================
"""


from abc import ABC
from abc import abstractmethod


class BaseAIProvider(ABC):
    """
    Clase base abstracta para proveedores de inteligencia artificial.

    Una clase abstracta no se utiliza directamente.

    Debe heredarse desde una implementación concreta, por ejemplo:

        class OllamaProvider(BaseAIProvider):
            ...
    """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Comprueba si el proveedor está disponible.

        Devuelve:
            True:
                El proveedor responde correctamente.

            False:
                El proveedor no está instalado, iniciado o accesible.
        """

        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        prompt: str,
    ) -> str:
        """
        Envía un prompt al modelo y devuelve su respuesta.

        Parámetros:
            prompt:
                Texto completo que debe procesar el modelo.

        Devuelve:
            str:
                Texto generado por la inteligencia artificial.
        """

        raise NotImplementedError

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Devuelve el nombre del proveedor.

        Ejemplo:
            Ollama
        """

        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Devuelve el nombre del modelo configurado.

        Ejemplo:
            qwen2.5:7b
        """

        raise NotImplementedError
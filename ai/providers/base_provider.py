"""
===============================================================================
Proyecto Atlas
Archivo: ai/providers/base_provider.py

Descripción:
    Define la interfaz común para todos los proveedores de inteligencia
    artificial que pueda utilizar Atlas.

    Un proveedor será responsable de enviar prompts a un modelo y
    devolver la respuesta generada.

Estado:
    Interfaz preparada.
    No contiene ninguna conexión real.
===============================================================================
"""


from abc import ABC
from abc import abstractmethod


class BaseAIProvider(ABC):
    """
    Clase base para proveedores de inteligencia artificial.

    Cualquier proveedor futuro deberá heredar de esta clase
    e implementar sus métodos obligatorios.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Comprueba si el proveedor está disponible.

        Devuelve:
            True:
                El proveedor puede utilizarse.

            False:
                El proveedor no está instalado, configurado
                o disponible.
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
                Texto completo que se enviará al modelo.

        Devuelve:
            Respuesta generada por el modelo.
        """

        raise NotImplementedError

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Devuelve el nombre del proveedor.
        """

        raise NotImplementedError

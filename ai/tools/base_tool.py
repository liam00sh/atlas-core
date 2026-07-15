"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/base_tool.py

Descripción:
    Define la interfaz común que deben respetar todas las herramientas
    disponibles para la inteligencia artificial de Atlas.

    Una herramienta permite obtener información real o ejecutar una acción
    controlada sin depender del conocimiento interno del modelo.

Ejemplos futuros:

    - Consultar fecha y hora.
    - Obtener información del sistema.
    - Consultar memoria.
    - Consultar usuarios.
    - Comprobar Docker.
    - Utilizar Home Assistant.
    - Buscar información en Internet.

Seguridad:
    Una herramienta no es ejecutada directamente por el modelo.

    Atlas conserva el control y decide:

    - Si la herramienta está habilitada.
    - Si el usuario tiene permiso.
    - Si necesita confirmación.
    - Si puede ejecutarse de forma segura.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from abc import ABC
from abc import abstractmethod

from dataclasses import dataclass
from typing import Any


# =============================================================================
# RESULTADO DE UNA HERRAMIENTA
# =============================================================================

@dataclass
class ToolResult:
    """
    Representa el resultado normalizado de una herramienta.

    Atributos:
        success:
            Indica si la ejecución terminó correctamente.

        message:
            Texto legible que puede utilizar Atlas o enviarse al modelo.

        data:
            Datos estructurados opcionales.

        error:
            Descripción técnica del error, si existe.
    """

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None


# =============================================================================
# HERRAMIENTA BASE
# =============================================================================

class BaseTool(ABC):
    """
    Clase base abstracta para todas las herramientas de Atlas.
    """

    # Nombre interno único.
    name: str = ""

    # Descripción utilizada por Atlas y, en el futuro,
    # por el modelo para decidir cuándo solicitarla.
    description: str = ""

    # Indica si la herramienta debe pedir confirmación
    # antes de ejecutarse.
    requires_confirmation: bool = False

    # Indica si necesita acceso a Internet.
    requires_internet: bool = False

    # Indica si modifica el sistema.
    is_destructive: bool = False

    def get_metadata(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve los metadatos públicos de la herramienta.
        """

        return {
            "name": self.name,
            "description": self.description,
            "requires_confirmation": self.requires_confirmation,
            "requires_internet": self.requires_internet,
            "is_destructive": self.is_destructive,
        }

    @abstractmethod
    def execute(
        self,
        atlas,
        **kwargs,
    ) -> ToolResult:
        """
        Ejecuta la herramienta.

        Parámetros:
            atlas:
                Instancia principal de Atlas.

            **kwargs:
                Parámetros específicos de cada herramienta.

        Devuelve:
            ToolResult:
                Resultado normalizado de la ejecución.
        """

        raise NotImplementedError
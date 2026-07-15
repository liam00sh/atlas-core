"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/ram_tool.py

Descripción:
    Implementa la herramienta encargada de consultar el estado actual
    de la memoria RAM del equipo donde se ejecuta Atlas.

    La información se obtiene mediante:

        core/system_info.py

    Actualmente proporciona:

    - Memoria RAM total.
    - Memoria RAM utilizada.
    - Memoria RAM disponible.
    - Porcentaje actual de utilización.

    No utiliza Internet.

    No modifica el sistema.

    No utiliza el conocimiento interno del modelo de lenguaje.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import bytes_to_gigabytes
from core.system_info import get_ram_info


class RAMTool(BaseTool):
    """
    Herramienta que proporciona información real
    sobre la memoria RAM del sistema.
    """

    name = "get_ram_info"

    description = (
        "Obtiene la memoria RAM total, utilizada y disponible, "
        "además del porcentaje actual de uso."
    )

    requires_confirmation = False
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        **kwargs,
    ) -> ToolResult:
        """
        Consulta el estado actual de la memoria RAM.

        Parámetros:
            atlas:
                Instancia principal de Atlas.

                Actualmente no es necesaria para consultar la RAM,
                pero forma parte del contrato común de herramientas.

            **kwargs:
                Argumentos adicionales reservados para futuras versiones.

        Devuelve:
            ToolResult:
                Resultado normalizado de la consulta.
        """

        try:

            ram_info = get_ram_info()

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    "No he podido consultar el estado "
                    "de la memoria RAM."
                ),
                error=str(exception),
            )

        total_gb = bytes_to_gigabytes(
            ram_info["total_bytes"]
        )

        used_gb = bytes_to_gigabytes(
            ram_info["used_bytes"]
        )

        available_gb = bytes_to_gigabytes(
            ram_info["available_bytes"]
        )

        usage_percent = ram_info[
            "usage_percent"
        ]

        message = (
            "Memoria RAM del sistema:\n\n"
            f"Total: {total_gb} GB\n"
            f"Utilizada: {used_gb} GB\n"
            f"Disponible: {available_gb} GB\n"
            f"Uso actual: {usage_percent}%"
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "total_bytes": ram_info["total_bytes"],
                "used_bytes": ram_info["used_bytes"],
                "available_bytes": ram_info["available_bytes"],
                "total_gb": total_gb,
                "used_gb": used_gb,
                "available_gb": available_gb,
                "usage_percent": usage_percent,
            },
        )
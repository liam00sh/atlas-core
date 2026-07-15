"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/cpu_tool.py

Descripción:
    Implementa la herramienta encargada de consultar información real
    del procesador del equipo donde se está ejecutando Atlas.

    La información se obtiene mediante:

        core/system_info.py

    Actualmente proporciona:

    - Modelo del procesador.
    - Arquitectura.
    - Tipo de sistema.
    - Número de núcleos físicos.
    - Número de procesadores lógicos.
    - Frecuencia actual.
    - Frecuencia mínima y máxima.
    - Porcentaje de utilización actual.

    No utiliza Internet.

    No modifica el sistema.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import get_cpu_info


class CPUTool(BaseTool):
    """
    Herramienta que proporciona información real
    sobre el procesador del sistema.
    """

    name = "get_cpu_info"

    description = (
        "Obtiene el modelo, la arquitectura, los núcleos, "
        "los procesadores lógicos, la frecuencia y el uso de la CPU."
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
        Consulta la información actual del procesador.
        """

        try:

            cpu_info = get_cpu_info()

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    "No he podido consultar la información "
                    "del procesador."
                ),
                error=str(exception),
            )

        physical_cores = cpu_info.get(
            "physical_cores"
        )

        logical_cores = cpu_info.get(
            "logical_cores"
        )

        current_frequency = cpu_info.get(
            "current_frequency_mhz"
        )

        maximum_frequency = cpu_info.get(
            "maximum_frequency_mhz"
        )

        usage_percent = cpu_info.get(
            "usage_percent"
        )

        lines = [
            "Información del procesador:",
            "",
            (
                "Modelo: "
                f"{cpu_info.get('processor', 'No disponible')}"
            ),
            (
                "Arquitectura: "
                f"{cpu_info.get('architecture', 'No disponible')}"
            ),
            (
                "Sistema: "
                f"{cpu_info.get('system_bits', 'No disponible')}"
            ),
            (
                "Núcleos físicos: "
                f"{physical_cores if physical_cores is not None else 'No disponible'}"
            ),
            (
                "Procesadores lógicos: "
                f"{logical_cores if logical_cores is not None else 'No disponible'}"
            ),
        ]

        if current_frequency is not None:

            lines.append(
                f"Frecuencia actual: "
                f"{current_frequency} MHz"
            )

        else:

            lines.append(
                "Frecuencia actual: No disponible"
            )

        if maximum_frequency is not None:

            lines.append(
                f"Frecuencia máxima: "
                f"{maximum_frequency} MHz"
            )

        else:

            lines.append(
                "Frecuencia máxima: No disponible"
            )

        if usage_percent is not None:

            lines.append(
                f"Uso actual: {usage_percent}%"
            )

        message = "\n".join(
            lines
        )

        return ToolResult(
            success=True,
            message=message,
            data=cpu_info,
        )
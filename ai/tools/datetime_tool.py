"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/datetime_tool.py

Descripción:
    Proporciona a Atlas la fecha y la hora reales del sistema.

    Evita que el modelo intente adivinar:

    - Fecha actual.
    - Hora actual.
    - Día de la semana.

    No requiere Internet ni confirmación.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import get_system_info


class DateTimeTool(BaseTool):
    """
    Herramienta de fecha y hora local.
    """

    name = "get_current_datetime"

    description = (
        "Obtiene la fecha, la hora y el día de la semana "
        "actuales directamente del sistema."
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
        Devuelve la fecha y la hora actuales.
        """

        system_info = get_system_info()

        date = system_info.get(
            "date",
            "No disponible",
        )

        time = system_info.get(
            "time",
            "No disponible",
        )

        weekday = system_info.get(
            "weekday",
            "No disponible",
        )

        message = (
            f"Hoy es {weekday}, {date}, "
            f"y la hora actual es {time}."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "date": date,
                "time": time,
                "weekday": weekday,
            },
        )
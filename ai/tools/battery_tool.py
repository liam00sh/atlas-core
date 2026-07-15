"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/battery_tool.py

Descripción:
    Implementa la herramienta encargada de consultar el estado
    de la batería del equipo donde se ejecuta Atlas.

    La información se obtiene mediante:

        core/system_info.py

    Actualmente proporciona:

    - Disponibilidad de batería.
    - Porcentaje de carga.
    - Estado de conexión a la corriente.
    - Autonomía restante estimada.

    En equipos de sobremesa puede indicar que no existe batería.

    No utiliza Internet.

    No modifica el sistema.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import get_battery_info


class BatteryTool(BaseTool):
    """
    Herramienta que proporciona información real
    sobre la batería del sistema.
    """

    name = "get_battery_info"

    description = (
        "Obtiene el porcentaje de batería, el estado de carga "
        "y la autonomía restante del equipo."
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
        Consulta el estado actual de la batería.

        Parámetros:
            atlas:
                Instancia principal de Atlas.

            **kwargs:
                Argumentos adicionales reservados
                para futuras versiones.

        Devuelve:
            ToolResult:
                Resultado normalizado de la consulta.
        """

        try:

            battery_info = get_battery_info()

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    "No he podido consultar el estado "
                    "de la batería."
                ),
                error=str(exception),
            )

        if not battery_info.get(
            "available",
            False,
        ):

            return ToolResult(
                success=True,
                message=(
                    "Este equipo no dispone de una batería "
                    "detectable. Parece un ordenador de sobremesa, "
                    "así que Daxter no tiene nada que vigilar por aquí."
                ),
                data=battery_info,
            )

        percent = battery_info.get(
            "percent",
            0.0,
        )

        power_plugged = battery_info.get(
            "power_plugged"
        )

        seconds_left = battery_info.get(
            "seconds_left"
        )

        time_status = battery_info.get(
            "time_status",
            "unknown",
        )

        if power_plugged is True:

            power_state = (
                "El equipo está conectado a la corriente."
            )

        elif power_plugged is False:

            power_state = (
                "El equipo está funcionando con batería."
            )

        else:

            power_state = (
                "No he podido determinar si está conectado "
                "a la corriente."
            )

        autonomy_text = self._format_autonomy(
            seconds_left=seconds_left,
            time_status=time_status,
            power_plugged=power_plugged,
        )

        message = (
            "Estado de la batería:\n\n"
            f"Carga actual: {percent:.1f}%\n"
            f"{power_state}\n"
            f"{autonomy_text}"
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "available": True,
                "percent": percent,
                "power_plugged": power_plugged,
                "seconds_left": seconds_left,
                "time_status": time_status,
            },
        )

    @staticmethod
    def _format_autonomy(
        seconds_left: int | None,
        time_status: str,
        power_plugged: bool | None,
    ) -> str:
        """
        Convierte la autonomía restante en una frase legible.
        """

        if (
            power_plugged is True
            or time_status == "unlimited"
        ):

            return (
                "Autonomía restante: no aplicable "
                "mientras está conectado."
            )

        if (
            seconds_left is None
            or time_status == "unknown"
        ):

            return (
                "Autonomía restante: no se puede estimar."
            )

        hours, remaining_seconds = divmod(
            seconds_left,
            3600,
        )

        minutes, _ = divmod(
            remaining_seconds,
            60,
        )

        if hours > 0:

            return (
                "Autonomía restante estimada: "
                f"{hours} h y {minutes} min."
            )

        return (
            "Autonomía restante estimada: "
            f"{minutes} min."
        )
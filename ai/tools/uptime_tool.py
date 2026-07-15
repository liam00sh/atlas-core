"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/uptime_tool.py

Descripción:
    Implementa la herramienta encargada de consultar el tiempo
    de funcionamiento del equipo donde se ejecuta Atlas.

    La información se obtiene mediante:

        core/system_info.py

    Actualmente proporciona:

    - Fecha de inicio del sistema.
    - Hora de inicio del sistema.
    - Días de funcionamiento.
    - Horas restantes.
    - Minutos restantes.
    - Segundos restantes.
    - Tiempo total en segundos.

    No utiliza Internet.

    No modifica el sistema.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import get_uptime_info


class UptimeTool(BaseTool):
    """
    Herramienta que proporciona información real
    sobre el tiempo de actividad del sistema.
    """

    name = "get_uptime_info"

    description = (
        "Obtiene cuándo se inició el sistema y cuánto tiempo "
        "lleva funcionando el equipo."
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
        Consulta el tiempo de actividad actual del sistema.

        Parámetros:
            atlas:
                Instancia principal de Atlas.

                Actualmente no es necesaria para calcular el uptime,
                pero forma parte del contrato común de herramientas.

            **kwargs:
                Argumentos adicionales reservados
                para futuras versiones.

        Devuelve:
            ToolResult:
                Resultado normalizado de la consulta.
        """

        try:

            uptime_info = get_uptime_info()

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    "No he podido consultar cuánto tiempo "
                    "lleva encendido el equipo."
                ),
                error=str(exception),
            )

        days = uptime_info[
            "days"
        ]

        hours = uptime_info[
            "hours"
        ]

        minutes = uptime_info[
            "minutes"
        ]

        seconds = uptime_info[
            "seconds"
        ]

        # Construimos una descripción natural evitando mostrar
        # unidades con valor cero cuando no son necesarias.
        duration_parts = []

        if days:

            duration_parts.append(
                self._format_unit(
                    value=days,
                    singular="día",
                    plural="días",
                )
            )

        if hours:

            duration_parts.append(
                self._format_unit(
                    value=hours,
                    singular="hora",
                    plural="horas",
                )
            )

        if minutes:

            duration_parts.append(
                self._format_unit(
                    value=minutes,
                    singular="minuto",
                    plural="minutos",
                )
            )

        # Mostramos los segundos cuando el tiempo es muy corto
        # o cuando no existe ninguna unidad superior.
        if seconds or not duration_parts:

            duration_parts.append(
                self._format_unit(
                    value=seconds,
                    singular="segundo",
                    plural="segundos",
                )
            )

        formatted_duration = self._join_duration_parts(
            duration_parts
        )

        message = (
            "Tiempo de actividad del sistema:\n\n"
            f"El equipo lleva encendido {formatted_duration}.\n"
            f"Se inició el {uptime_info['boot_date']} "
            f"a las {uptime_info['boot_time']}."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "boot_timestamp": uptime_info[
                    "boot_timestamp"
                ],
                "boot_datetime": uptime_info[
                    "boot_datetime"
                ],
                "boot_date": uptime_info[
                    "boot_date"
                ],
                "boot_time": uptime_info[
                    "boot_time"
                ],
                "total_seconds": uptime_info[
                    "total_seconds"
                ],
                "days": days,
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
                "formatted_duration": formatted_duration,
            },
        )

    @staticmethod
    def _format_unit(
        value: int,
        singular: str,
        plural: str,
    ) -> str:
        """
        Da formato a una unidad de tiempo.

        Ejemplos:
            1 día
            2 días
        """

        unit = (
            singular
            if value == 1
            else plural
        )

        return f"{value} {unit}"

    @staticmethod
    def _join_duration_parts(
        parts: list[str],
    ) -> str:
        """
        Une las unidades temporales en una frase natural.

        Ejemplos:
            ["2 días"]
                -> "2 días"

            ["2 días", "3 horas"]
                -> "2 días y 3 horas"

            ["2 días", "3 horas", "14 minutos"]
                -> "2 días, 3 horas y 14 minutos"
        """

        if not parts:
            return "0 segundos"

        if len(parts) == 1:
            return parts[0]

        return (
            ", ".join(
                parts[:-1]
            )
            + " y "
            + parts[-1]
        )
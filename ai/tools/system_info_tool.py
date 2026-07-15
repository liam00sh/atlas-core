"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/system_info_tool.py

Descripción:
    Permite consultar información real del sistema donde se ejecuta Atlas.

    Actualmente ofrece:

    - Sistema operativo.
    - Versión del sistema operativo.
    - Versión de Python.
    - Fecha.
    - Hora.
    - Día de la semana.

    Más adelante podrá ampliarse con CPU, RAM, GPU, almacenamiento,
    temperatura y tiempo de actividad.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import get_system_info


class SystemInfoTool(BaseTool):
    """
    Herramienta de información básica del sistema.
    """

    name = "get_system_info"

    description = (
        "Obtiene información real sobre el sistema operativo, "
        "Python, fecha y hora del equipo donde se ejecuta Atlas."
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
        Consulta la información actual del sistema.
        """

        system_info = get_system_info()

        operating_system = system_info.get(
            "os",
            "No disponible",
        )

        os_version = system_info.get(
            "os_version",
            "",
        )

        python_version = system_info.get(
            "python",
            "No disponible",
        )

        message = (
            f"Sistema operativo: "
            f"{operating_system} {os_version}.\n"
            f"Versión de Python: {python_version}.\n"
            f"Fecha: {system_info.get('date', 'No disponible')}.\n"
            f"Día: {system_info.get('weekday', 'No disponible')}.\n"
            f"Hora: {system_info.get('time', 'No disponible')}."
        )

        return ToolResult(
            success=True,
            message=message,
            data=system_info,
        )
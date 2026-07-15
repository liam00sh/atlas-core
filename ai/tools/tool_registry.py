"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/tool_registry.py

Descripción:
    Mantiene el registro central de herramientas disponibles para Atlas.

    El registro permite:

    - Añadir herramientas.
    - Buscar herramientas por nombre.
    - Consultar sus metadatos.
    - Ejecutarlas de forma controlada.
    - Evitar nombres duplicados.

    El modelo no utiliza este registro directamente.
    Atlas conserva siempre el control de ejecución.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from ai.tools.datetime_tool import DateTimeTool
from ai.tools.memory_tool import MemoryTool
from ai.tools.system_info_tool import SystemInfoTool
from ai.tools.user_tool import UserTool

from ai.tools.ram_tool import RAMTool
from ai.tools.disk_tool import DiskTool
from ai.tools.gpu_tool import GPUTool
from ai.tools.network_tool import NetworkTool
from ai.tools.uptime_tool import UptimeTool
from ai.tools.battery_tool import BatteryTool
from ai.tools.cpu_tool import CPUTool

from ai.tools.test_confirmation_tool import TestConfirmationTool


class ToolRegistry:
    """
    Registro central de herramientas disponibles.
    """

    def __init__(
        self,
    ) -> None:
        """
        Inicializa el registro y carga las herramientas básicas.
        """

        self._tools: dict[str, BaseTool] = {}

        self.register(
            DateTimeTool()
        )

        self.register(
            SystemInfoTool()
        )

        self.register(
            UserTool()
        )

        self.register(
            MemoryTool()
        )

        self.register(
            RAMTool()
        )

        self.register(
            DiskTool()
        )

        self.register(
            GPUTool()
        )

        self.register(
            NetworkTool()
        )

        self.register(
            UptimeTool()
        )

        self.register(
            BatteryTool()
        )

        self.register(
            CPUTool()
        )

        self.register(
            TestConfirmationTool()
        )

    def register(
        self,
        tool: BaseTool,
    ) -> None:
        """
        Registra una herramienta.

        Errores:
            TypeError:
                El objeto no hereda de BaseTool.

            ValueError:
                El nombre está vacío o ya existe.
        """

        if not isinstance(
            tool,
            BaseTool,
        ):

            raise TypeError(
                "La herramienta debe heredar de BaseTool."
            )

        tool_name = tool.name.strip()

        if not tool_name:

            raise ValueError(
                "La herramienta debe tener un nombre."
            )

        if tool_name in self._tools:

            raise ValueError(
                f"La herramienta «{tool_name}» "
                f"ya está registrada."
            )

        self._tools[
            tool_name
        ] = tool

    def unregister(
        self,
        tool_name: str,
    ) -> bool:
        """
        Elimina una herramienta del registro.
        """

        if tool_name not in self._tools:
            return False

        del self._tools[
            tool_name
        ]

        return True

    def get(
        self,
        tool_name: str,
    ) -> BaseTool | None:
        """
        Devuelve una herramienta por su nombre.
        """

        return self._tools.get(
            tool_name
        )

    def exists(
        self,
        tool_name: str,
    ) -> bool:
        """
        Indica si una herramienta está registrada.
        """

        return tool_name in self._tools

    def list_names(
        self,
    ) -> list[str]:
        """
        Devuelve los nombres registrados.
        """

        return sorted(
            self._tools.keys()
        )

    def get_all_metadata(
        self,
    ) -> list[dict]:
        """
        Devuelve los metadatos públicos de las herramientas.
        """

        return [
            self._tools[name].get_metadata()
            for name in self.list_names()
        ]

    def count(
        self,
    ) -> int:
        """
        Devuelve el número de herramientas registradas.
        """

        return len(
            self._tools
        )

    def execute(
        self,
        tool_name: str,
        atlas,
        **kwargs,
    ) -> ToolResult:
        """
        Ejecuta una herramienta registrada.

        Esta primera versión todavía no gestiona confirmaciones.
        Antes de conectar herramientas destructivas, añadiremos
        una capa específica de autorización.
        """

        tool = self.get(
            tool_name
        )

        if tool is None:

            return ToolResult(
                success=False,
                message=(
                    f"No existe ninguna herramienta "
                    f"llamada «{tool_name}»."
                ),
                error="tool_not_found",
            )

        try:

            return tool.execute(
                atlas=atlas,
                **kwargs,
            )

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    f"La herramienta «{tool_name}» "
                    f"no ha podido ejecutarse."
                ),
                error=str(exception),
            )

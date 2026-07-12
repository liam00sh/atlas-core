"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/tool_registry.py

Descripción:
    Mantendrá el registro de herramientas que los modelos de IA podrán
    solicitar a Atlas.

    Ejemplos futuros:
        - Consultar memoria.
        - Ejecutar comandos.
        - Obtener la fecha.
        - Consultar el sistema.
        - Ejecutar automatizaciones.

Estado:
    Preparado para futuras fases.
===============================================================================
"""


class ToolRegistry:
    """
    Registro de herramientas disponibles para la IA.
    """

    def __init__(self):
        """
        Inicializa un registro vacío.
        """

        self.tools = {}

    def register_tool(
        self,
        name: str,
        tool,
    ) -> None:
        """
        Registra una herramienta.
        """

        self.tools[name] = tool

    def get_tool(
        self,
        name: str,
    ):
        """
        Devuelve una herramienta registrada.
        """

        return self.tools.get(name)

    def get_tool_names(self) -> list[str]:
        """
        Devuelve los nombres de todas las herramientas.
        """

        return sorted(
            self.tools.keys()
        )

    def count_tools(self) -> int:
        """
        Devuelve el número de herramientas registradas.
        """

        return len(self.tools)

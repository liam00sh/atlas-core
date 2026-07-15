"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/memory_tool.py

Descripción:
    Permite consultar información básica del sistema de memoria de Atlas.

    Primera versión:

    - Cuenta los recuerdos del usuario activo.
    - No revela automáticamente el contenido.
    - No modifica recuerdos.
    - No evita ni sustituye las comprobaciones de privacidad.

    Más adelante podrá realizar búsquedas autorizadas y devolver
    únicamente recuerdos accesibles para el usuario activo.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult


class MemoryTool(BaseTool):
    """
    Herramienta de consulta básica de memoria.
    """

    name = "get_memory_status"

    description = (
        "Consulta el número de recuerdos guardados "
        "para el usuario activo sin revelar su contenido."
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
        Obtiene el estado básico de memoria del usuario activo.
        """

        active_user = atlas.get_user()

        try:

            memory_count = atlas.memory.count_memories(
                active_user
            )

        except AttributeError as exception:

            return ToolResult(
                success=False,
                message=(
                    "El gestor de memoria no permite "
                    "contar recuerdos actualmente."
                ),
                error=str(exception),
            )

        message = (
            f"{active_user} tiene "
            f"{memory_count} recuerdos guardados."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "owner": active_user,
                "memory_count": memory_count,
            },
        )
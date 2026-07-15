"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/test_confirmation_tool.py

Descripción:
    Herramienta segura utilizada para comprobar el sistema
    de confirmaciones de Atlas.

    No modifica archivos, servicios ni configuración.

    Su única finalidad es verificar:

    - Creación de confirmaciones pendientes.
    - Confirmación del usuario.
    - Cancelación.
    - Validación del usuario solicitante.
    - Ejecución única.

===============================================================================
"""


from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult


class TestConfirmationTool(BaseTool):
    """
    Herramienta segura para probar confirmaciones.
    """

    name = "test_confirmation"

    description = (
        "Ejecuta una prueba segura del sistema "
        "de confirmaciones de Atlas."
    )

    requires_confirmation = True
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        **kwargs,
    ) -> ToolResult:
        """
        Ejecuta una prueba sin modificar el sistema.
        """

        return ToolResult(
            success=True,
            message=(
                "La prueba de confirmación se ha ejecutado "
                "correctamente. No se ha modificado nada."
            ),
            data={
                "test": "confirmation",
                "executed": True,
                "safe": True,
            },
        )
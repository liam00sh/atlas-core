"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/user_tool.py

Descripción:
    Proporciona información controlada sobre el usuario activo.

    Esta herramienta no revela conversaciones ni recuerdos privados.

    Actualmente permite consultar:

    - Usuario activo.
    - Usuario principal.
    - Si el usuario activo es el principal.
    - Género gramatical.
    - Pronombres configurados.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult


class UserTool(BaseTool):
    """
    Herramienta de información del usuario activo.
    """

    name = "get_current_user"

    description = (
        "Obtiene información básica y autorizada "
        "sobre el usuario activo de Atlas."
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
        Obtiene información sobre el perfil activo.
        """

        active_user = atlas.get_user()
        main_user = atlas.get_main_user()

        grammatical_gender = (
            atlas.get_user_grammatical_gender(
                active_user
            )
        )

        pronouns = atlas.get_user_pronouns(
            active_user
        )

        is_main_user = atlas.is_main_user()

        message = (
            f"El usuario activo es {active_user}. "
            f"El usuario principal es {main_user}. "
            f"{active_user} "
            f"{'es' if is_main_user else 'no es'} "
            f"el usuario principal."
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "active_user": active_user,
                "main_user": main_user,
                "is_main_user": is_main_user,
                "grammatical_gender": grammatical_gender,
                "pronouns": pronouns,
            },
        )
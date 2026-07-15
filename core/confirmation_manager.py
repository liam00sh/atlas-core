"""
===============================================================================

Proyecto Atlas

Archivo: core/confirmation_manager.py

Descripción:

    Gestiona las confirmaciones pendientes de acciones sensibles.

    Su responsabilidad consiste en:

    - Registrar acciones pendientes de confirmar.
    - Asociar cada acción al usuario que la solicitó.
    - Comprobar si existe una confirmación pendiente.
    - Recuperar la acción pendiente.
    - Cancelarla.
    - Evitar reutilizar confirmaciones antiguas.

    ConfirmationManager no ejecuta ninguna acción.

    Únicamente conserva temporalmente la información necesaria
    para que Atlas pueda decidir posteriormente si una herramienta
    debe ejecutarse.

===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

from datetime import datetime
from datetime import timedelta

from core.log_manager import info


class ConfirmationManager:
    """
    Gestiona acciones pendientes de confirmación.
    """

    def __init__(
        self,
        expiration_minutes: int = 5,
    ) -> None:
        """
        Inicializa el gestor de confirmaciones.

        Parámetros:
            expiration_minutes:
                Tiempo máximo que permanece válida una
                confirmación pendiente.
        """

        self.expiration = timedelta(
            minutes=expiration_minutes
        )

        self.pending_confirmation = None

    def has_pending_confirmation(
        self,
    ) -> bool:
        """
        Indica si existe una acción pendiente.

        Si la confirmación ha caducado,
        también se elimina automáticamente.
        """

        self._remove_if_expired()

        return (
            self.pending_confirmation
            is not None
        )

    def create_confirmation(
        self,
        *,
        user: str,
        action_type: str,
        action_name: str,
        arguments: dict,
    ) -> None:
        """
        Registra una nueva confirmación pendiente.
        """

        self.pending_confirmation = {

            "user": user,

            "action_type": action_type,

            "action_name": action_name,

            "arguments": arguments,

            "created_at": datetime.now(),

        }

        info(
            f"Confirmación creada. "
            f"Usuario: {user}. "
            f"Acción: {action_name}."
        )

    def get_confirmation(
        self,
    ) -> dict | None:
        """
        Devuelve la confirmación pendiente.

        Si ha caducado devuelve None.
        """

        self._remove_if_expired()

        return self.pending_confirmation

    def clear_confirmation(
        self,
    ) -> None:
        """
        Elimina la confirmación pendiente.
        """

        if self.pending_confirmation is not None:

            info(
                "Confirmación eliminada."
            )

        self.pending_confirmation = None

    def belongs_to_user(
        self,
        user: str,
    ) -> bool:
        """
        Comprueba si la confirmación pertenece
        al usuario indicado.
        """

        confirmation = (
            self.get_confirmation()
        )

        if confirmation is None:
            return False

        return (
            confirmation["user"].casefold()
            == user.casefold()
        )

    def _remove_if_expired(
        self,
    ) -> None:
        """
        Elimina automáticamente una confirmación
        cuando supera el tiempo máximo permitido.
        """

        if self.pending_confirmation is None:
            return

        created_at = (
            self.pending_confirmation[
                "created_at"
            ]
        )

        if (
            datetime.now()
            - created_at
        ) > self.expiration:

            info(
                "Confirmación caducada."
            )

            self.pending_confirmation = None
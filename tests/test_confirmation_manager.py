"""
===============================================================================
Proyecto Atlas
Archivo: tests/test_confirmation_manager.py

Descripción:
    Contiene las pruebas automáticas del gestor de confirmaciones
    del Proyecto Atlas.

    Estas pruebas verifican que ConfirmationManager pueda:

    - Crear una confirmación pendiente.
    - Detectar que existe una confirmación.
    - Recuperar sus datos.
    - Asociarla correctamente a un usuario.
    - Eliminarla manualmente.
    - Sustituir una confirmación anterior.
    - Detectar confirmaciones caducadas.
    - Evitar que una confirmación caducada siga disponible.
    - Trabajar con nombres de usuario sin distinguir mayúsculas.
    - Conservar los argumentos de la acción solicitada.

    Las pruebas no ejecutan herramientas reales.

    Únicamente comprueban el comportamiento interno de:

        core/confirmation_manager.py

Ejecución:

    Desde la raíz de atlas_core:

        python -m unittest tests.test_confirmation_manager

    Para ejecutar todas las pruebas:

        python -m unittest discover -s tests

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import unittest

from datetime import datetime
from datetime import timedelta

from core.confirmation_manager import ConfirmationManager


# =============================================================================
# CLASE DE PRUEBAS
# =============================================================================

class TestConfirmationManager(
    unittest.TestCase,
):
    """
    Pruebas automáticas de ConfirmationManager.

    Cada prueba crea una instancia nueva del gestor para evitar
    que una confirmación pendiente afecte a otras pruebas.
    """

    def setUp(
        self,
    ) -> None:
        """
        Prepara un gestor limpio antes de cada prueba.
        """

        self.manager = ConfirmationManager(
            expiration_minutes=5
        )

    def test_initial_state_has_no_pending_confirmation(
        self,
    ) -> None:
        """
        Comprueba que un gestor recién creado
        no contiene ninguna confirmación.
        """

        self.assertFalse(
            self.manager.has_pending_confirmation()
        )

        self.assertIsNone(
            self.manager.get_confirmation()
        )

    def test_create_confirmation(
        self,
    ) -> None:
        """
        Comprueba que puede crearse una confirmación pendiente.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="test_confirmation",
            arguments={
                "example": True,
            },
        )

        self.assertTrue(
            self.manager.has_pending_confirmation()
        )

        confirmation = (
            self.manager.get_confirmation()
        )

        self.assertIsNotNone(
            confirmation
        )

        self.assertEqual(
            confirmation["user"],
            "Liam",
        )

        self.assertEqual(
            confirmation["action_type"],
            "tool",
        )

        self.assertEqual(
            confirmation["action_name"],
            "test_confirmation",
        )

        self.assertEqual(
            confirmation["arguments"],
            {
                "example": True,
            },
        )

        self.assertIsInstance(
            confirmation["created_at"],
            datetime,
        )

    def test_confirmation_belongs_to_correct_user(
        self,
    ) -> None:
        """
        Comprueba que la confirmación queda asociada
        al usuario que la creó.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="test_confirmation",
            arguments={},
        )

        self.assertTrue(
            self.manager.belongs_to_user(
                "Liam"
            )
        )

        self.assertFalse(
            self.manager.belongs_to_user(
                "Saray"
            )
        )

    def test_user_comparison_is_case_insensitive(
        self,
    ) -> None:
        """
        Comprueba que la comparación de usuarios
        ignora mayúsculas y minúsculas.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="test_confirmation",
            arguments={},
        )

        self.assertTrue(
            self.manager.belongs_to_user(
                "liam"
            )
        )

        self.assertTrue(
            self.manager.belongs_to_user(
                "LIAM"
            )
        )

        self.assertTrue(
            self.manager.belongs_to_user(
                "LiAm"
            )
        )

    def test_clear_confirmation(
        self,
    ) -> None:
        """
        Comprueba que una confirmación puede eliminarse.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="test_confirmation",
            arguments={},
        )

        self.assertTrue(
            self.manager.has_pending_confirmation()
        )

        self.manager.clear_confirmation()

        self.assertFalse(
            self.manager.has_pending_confirmation()
        )

        self.assertIsNone(
            self.manager.get_confirmation()
        )

    def test_clear_confirmation_when_empty(
        self,
    ) -> None:
        """
        Comprueba que eliminar una confirmación inexistente
        no produce ningún error.
        """

        self.manager.clear_confirmation()

        self.assertFalse(
            self.manager.has_pending_confirmation()
        )

        self.assertIsNone(
            self.manager.get_confirmation()
        )

    def test_new_confirmation_replaces_previous_one(
        self,
    ) -> None:
        """
        Comprueba que solo puede existir una confirmación
        pendiente al mismo tiempo.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="first_action",
            arguments={
                "value": 1,
            },
        )

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="second_action",
            arguments={
                "value": 2,
            },
        )

        confirmation = (
            self.manager.get_confirmation()
        )

        self.assertIsNotNone(
            confirmation
        )

        self.assertEqual(
            confirmation["action_name"],
            "second_action",
        )

        self.assertEqual(
            confirmation["arguments"],
            {
                "value": 2,
            },
        )

    def test_arguments_are_preserved(
        self,
    ) -> None:
        """
        Comprueba que los argumentos de la acción
        se conservan sin alteraciones.
        """

        arguments = {
            "path": "C:/Atlas",
            "force": False,
            "items": [
                "uno",
                "dos",
            ],
        }

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="example_action",
            arguments=arguments,
        )

        confirmation = (
            self.manager.get_confirmation()
        )

        self.assertEqual(
            confirmation["arguments"],
            arguments,
        )

    def test_expired_confirmation_is_removed(
        self,
    ) -> None:
        """
        Comprueba que una confirmación caducada
        se elimina automáticamente.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="test_confirmation",
            arguments={},
        )

        confirmation = (
            self.manager.pending_confirmation
        )

        confirmation["created_at"] = (
            datetime.now()
            - timedelta(
                minutes=10
            )
        )

        self.assertFalse(
            self.manager.has_pending_confirmation()
        )

        self.assertIsNone(
            self.manager.get_confirmation()
        )

        self.assertIsNone(
            self.manager.pending_confirmation
        )

    def test_non_expired_confirmation_remains_available(
        self,
    ) -> None:
        """
        Comprueba que una confirmación reciente
        continúa disponible.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="test_confirmation",
            arguments={},
        )

        confirmation = (
            self.manager.pending_confirmation
        )

        confirmation["created_at"] = (
            datetime.now()
            - timedelta(
                minutes=2
            )
        )

        self.assertTrue(
            self.manager.has_pending_confirmation()
        )

        self.assertIsNotNone(
            self.manager.get_confirmation()
        )

    def test_confirmation_expires_with_short_duration(
        self,
    ) -> None:
        """
        Comprueba la caducidad utilizando un gestor
        configurado con un plazo muy corto.
        """

        manager = ConfirmationManager(
            expiration_minutes=1
        )

        manager.create_confirmation(
            user="Liam",
            action_type="tool",
            action_name="test_confirmation",
            arguments={},
        )

        manager.pending_confirmation[
            "created_at"
        ] = (
            datetime.now()
            - timedelta(
                minutes=2
            )
        )

        self.assertFalse(
            manager.has_pending_confirmation()
        )

        self.assertIsNone(
            manager.get_confirmation()
        )

    def test_belongs_to_user_returns_false_without_confirmation(
        self,
    ) -> None:
        """
        Comprueba que belongs_to_user() devuelve False
        cuando no existe ninguna confirmación pendiente.
        """

        self.assertFalse(
            self.manager.belongs_to_user(
                "Liam"
            )
        )

    def test_confirmation_can_store_other_action_types(
        self,
    ) -> None:
        """
        Comprueba que el gestor no depende exclusivamente
        de acciones de tipo herramienta.

        La validación del tipo corresponde posteriormente
        a la capa que vaya a ejecutar la acción.
        """

        self.manager.create_confirmation(
            user="Liam",
            action_type="automation",
            action_name="example_automation",
            arguments={
                "enabled": True,
            },
        )

        confirmation = (
            self.manager.get_confirmation()
        )

        self.assertEqual(
            confirmation["action_type"],
            "automation",
        )

        self.assertEqual(
            confirmation["action_name"],
            "example_automation",
        )


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":

    unittest.main()
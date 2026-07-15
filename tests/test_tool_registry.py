"""
===============================================================================
Proyecto Atlas
Archivo: tests/test_tool_registry.py

Descripción:
    Contiene las pruebas automáticas del registro central de herramientas.

    ToolRegistry carga automáticamente las herramientas básicas de Atlas
    durante su inicialización.

    Estas pruebas verifican:

    - Carga automática de herramientas.
    - Registro de herramientas adicionales.
    - Rechazo de objetos que no heredan de BaseTool.
    - Rechazo de nombres vacíos.
    - Rechazo de nombres duplicados.
    - Consulta por nombre.
    - Comprobación de existencia.
    - Eliminación de herramientas.
    - Listado ordenado de nombres.
    - Conteo de herramientas.
    - Obtención de metadatos.
    - Ejecución correcta.
    - Gestión de herramientas inexistentes.
    - Captura de excepciones durante la ejecución.

Ejecución:

    python -m unittest tests.test_tool_registry -v

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import unittest

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from ai.tools.tool_registry import ToolRegistry


# =============================================================================
# HERRAMIENTAS AUXILIARES PARA LAS PRUEBAS
# =============================================================================

class DummyTool(BaseTool):
    """
    Herramienta segura utilizada únicamente por las pruebas.
    """

    name = "dummy_test_tool"

    description = (
        "Herramienta temporal utilizada para probar ToolRegistry."
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
        Devuelve correctamente los argumentos recibidos.
        """

        return ToolResult(
            success=True,
            message="La herramienta de prueba se ejecutó correctamente.",
            data={
                "received_arguments": kwargs,
            },
        )


class SecondDummyTool(BaseTool):
    """
    Segunda herramienta utilizada para probar registros múltiples.
    """

    name = "second_dummy_test_tool"

    description = "Segunda herramienta temporal."

    requires_confirmation = True
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        **kwargs,
    ) -> ToolResult:

        return ToolResult(
            success=True,
            message="Segunda herramienta ejecutada.",
            data={},
        )


class EmptyNameTool(BaseTool):
    """
    Herramienta inválida con nombre vacío.
    """

    name = "   "

    description = "Herramienta con nombre inválido."

    requires_confirmation = False
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        **kwargs,
    ) -> ToolResult:

        return ToolResult(
            success=True,
            message="No debería ejecutarse.",
            data={},
        )


class FailingTool(BaseTool):
    """
    Herramienta que lanza una excepción intencionadamente.
    """

    name = "failing_test_tool"

    description = "Herramienta que simula un error interno."

    requires_confirmation = False
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        **kwargs,
    ) -> ToolResult:

        raise RuntimeError(
            "Fallo intencionado durante la prueba."
        )


# =============================================================================
# PRUEBAS
# =============================================================================

class TestToolRegistry(
    unittest.TestCase,
):
    """
    Pruebas automáticas de ToolRegistry.
    """

    def setUp(
        self,
    ) -> None:
        """
        Crea un registro real antes de cada prueba.
        """

        self.registry = ToolRegistry()

        self.initial_count = (
            self.registry.count()
        )

    def test_registry_loads_base_tools(
        self,
    ) -> None:
        """
        Comprueba que las herramientas base se cargan automáticamente.
        """

        expected_tools = {
            "get_current_datetime",
            "get_system_info",
            "get_current_user",
            "get_memory_status",
            "get_cpu_info",
            "get_ram_info",
            "get_disk_info",
            "get_gpu_info",
            "get_network_info",
            "get_uptime_info",
            "get_battery_info",
            "test_confirmation",
        }

        registered_tools = set(
            self.registry.list_names()
        )

        self.assertTrue(
            expected_tools.issubset(
                registered_tools
            )
        )

    def test_registry_is_not_empty(
        self,
    ) -> None:
        """
        Comprueba que el registro inicial contiene herramientas.
        """

        self.assertGreater(
            self.registry.count(),
            0,
        )

    def test_register_additional_tool(
        self,
    ) -> None:
        """
        Registrar una herramienta adicional aumenta el contador en uno.
        """

        tool = DummyTool()

        self.registry.register(
            tool
        )

        self.assertEqual(
            self.registry.count(),
            self.initial_count + 1,
        )

        self.assertIs(
            self.registry.get(
                "dummy_test_tool"
            ),
            tool,
        )

    def test_register_multiple_additional_tools(
        self,
    ) -> None:
        """
        Comprueba que pueden registrarse varias herramientas nuevas.
        """

        self.registry.register(
            DummyTool()
        )

        self.registry.register(
            SecondDummyTool()
        )

        self.assertEqual(
            self.registry.count(),
            self.initial_count + 2,
        )

    def test_register_rejects_non_tool_object(
        self,
    ) -> None:
        """
        Un objeto que no hereda de BaseTool debe rechazarse.
        """

        with self.assertRaises(
            TypeError
        ):

            self.registry.register(
                object()
            )

    def test_register_rejects_empty_name(
        self,
    ) -> None:
        """
        Una herramienta con nombre vacío debe rechazarse.
        """

        with self.assertRaises(
            ValueError
        ):

            self.registry.register(
                EmptyNameTool()
            )

    def test_register_rejects_duplicate_name(
        self,
    ) -> None:
        """
        No se permite registrar dos herramientas con el mismo nombre.
        """

        self.registry.register(
            DummyTool()
        )

        with self.assertRaises(
            ValueError
        ):

            self.registry.register(
                DummyTool()
            )

    def test_get_existing_tool(
        self,
    ) -> None:
        """
        get() devuelve la instancia registrada.
        """

        tool = self.registry.get(
            "get_cpu_info"
        )

        self.assertIsNotNone(
            tool
        )

        self.assertEqual(
            tool.name,
            "get_cpu_info",
        )

    def test_get_unknown_tool_returns_none(
        self,
    ) -> None:
        """
        get() devuelve None para herramientas inexistentes.
        """

        self.assertIsNone(
            self.registry.get(
                "tool_that_does_not_exist"
            )
        )

    def test_exists_returns_true_for_registered_tool(
        self,
    ) -> None:
        """
        exists() devuelve True cuando el nombre está registrado.
        """

        self.assertTrue(
            self.registry.exists(
                "get_ram_info"
            )
        )

    def test_exists_returns_false_for_unknown_tool(
        self,
    ) -> None:
        """
        exists() devuelve False para nombres inexistentes.
        """

        self.assertFalse(
            self.registry.exists(
                "unknown_test_tool"
            )
        )

    def test_unregister_existing_tool(
        self,
    ) -> None:
        """
        unregister() elimina correctamente una herramienta.
        """

        self.registry.register(
            DummyTool()
        )

        removed = self.registry.unregister(
            "dummy_test_tool"
        )

        self.assertTrue(
            removed
        )

        self.assertFalse(
            self.registry.exists(
                "dummy_test_tool"
            )
        )

        self.assertEqual(
            self.registry.count(),
            self.initial_count,
        )

    def test_unregister_unknown_tool_returns_false(
        self,
    ) -> None:
        """
        Eliminar una herramienta inexistente devuelve False.
        """

        self.assertFalse(
            self.registry.unregister(
                "unknown_test_tool"
            )
        )

    def test_list_names_is_sorted(
        self,
    ) -> None:
        """
        Los nombres deben devolverse ordenados alfabéticamente.
        """

        names = self.registry.list_names()

        self.assertEqual(
            names,
            sorted(names),
        )

    def test_list_names_contains_registered_tool(
        self,
    ) -> None:
        """
        Una herramienta nueva aparece en list_names().
        """

        self.registry.register(
            DummyTool()
        )

        self.assertIn(
            "dummy_test_tool",
            self.registry.list_names(),
        )

    def test_metadata_contains_all_registered_tools(
        self,
    ) -> None:
        """
        El número de metadatos coincide con el número de herramientas.
        """

        metadata = (
            self.registry.get_all_metadata()
        )

        self.assertEqual(
            len(metadata),
            self.registry.count(),
        )

    def test_metadata_contains_expected_fields(
        self,
    ) -> None:
        """
        Cada herramienta expone sus metadatos públicos.
        """

        metadata = (
            self.registry.get_all_metadata()
        )

        cpu_metadata = next(
            (
                item
                for item in metadata
                if item.get("name")
                == "get_cpu_info"
            ),
            None,
        )

        self.assertIsNotNone(
            cpu_metadata
        )

        self.assertIn(
            "description",
            cpu_metadata,
        )

        self.assertIn(
            "requires_confirmation",
            cpu_metadata,
        )

        self.assertIn(
            "requires_internet",
            cpu_metadata,
        )

        self.assertIn(
            "is_destructive",
            cpu_metadata,
        )

    def test_metadata_includes_new_tool(
        self,
    ) -> None:
        """
        Los metadatos incluyen herramientas registradas posteriormente.
        """

        self.registry.register(
            DummyTool()
        )

        metadata_names = {
            item["name"]
            for item in self.registry.get_all_metadata()
        }

        self.assertIn(
            "dummy_test_tool",
            metadata_names,
        )

    def test_execute_registered_tool(
        self,
    ) -> None:
        """
        El registro ejecuta correctamente una herramienta registrada.
        """

        self.registry.register(
            DummyTool()
        )

        result = self.registry.execute(
            tool_name="dummy_test_tool",
            atlas=None,
            example=123,
        )

        self.assertTrue(
            result.success
        )

        self.assertEqual(
            result.message,
            (
                "La herramienta de prueba "
                "se ejecutó correctamente."
            ),
        )

        self.assertEqual(
            result.data[
                "received_arguments"
            ],
            {
                "example": 123,
            },
        )

    def test_execute_unknown_tool_returns_error_result(
        self,
    ) -> None:
        """
        Ejecutar un nombre inexistente devuelve un ToolResult de error.
        """

        result = self.registry.execute(
            tool_name="unknown_test_tool",
            atlas=None,
        )

        self.assertFalse(
            result.success
        )

        self.assertEqual(
            result.error,
            "tool_not_found",
        )

        self.assertIn(
            "unknown_test_tool",
            result.message,
        )

    def test_execute_catches_tool_exception(
        self,
    ) -> None:
        """
        Una excepción interna debe convertirse en ToolResult de error.
        """

        self.registry.register(
            FailingTool()
        )

        result = self.registry.execute(
            tool_name="failing_test_tool",
            atlas=None,
        )

        self.assertFalse(
            result.success
        )

        self.assertIn(
            "Fallo intencionado",
            result.error,
        )

    def test_confirmation_metadata_is_preserved(
        self,
    ) -> None:
        """
        Los metadatos reflejan si una herramienta exige confirmación.
        """

        tool = self.registry.get(
            "test_confirmation"
        )

        self.assertIsNotNone(
            tool
        )

        self.assertTrue(
            tool.requires_confirmation
        )

        self.assertFalse(
            tool.is_destructive
        )


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":

    unittest.main()
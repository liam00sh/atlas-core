"""
===============================================================================
Proyecto Atlas
Archivo: tests/test_tool_selector.py

Descripción:
    Contiene las pruebas automáticas de ToolSelector.

    Estas pruebas utilizan el ToolRegistry real de Atlas y verifican:

    - Selección determinista de cada herramienta.
    - Extracción de argumentos.
    - Rechazo de conversación general.
    - Método can_handle().
    - Selección asistida por IA.
    - Parseo seguro de JSON.
    - Rechazo de herramientas inexistentes.
    - Rechazo de argumentos inválidos.
    - Rechazo de baja confianza.
    - Gestión de errores del proveedor.

    No se conecta realmente con Ollama.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import unittest

from ai.tools.tool_registry import ToolRegistry

from ai.tools.tool_selector import ToolSelection
from ai.tools.tool_selector import ToolSelector


# =============================================================================
# PROVEEDOR FALSO
# =============================================================================

class FakeAIProvider:
    """
    Simula un proveedor de IA sin utilizar Ollama.
    """

    def __init__(
        self,
        response: str = "",
        exception: Exception | None = None,
    ) -> None:

        self.response = response
        self.exception = exception
        self.received_prompt = None

    def generate(
        self,
        prompt: str,
    ) -> str:

        self.received_prompt = prompt

        if self.exception is not None:
            raise self.exception

        return self.response


# =============================================================================
# PRUEBAS
# =============================================================================

class TestToolSelector(
    unittest.TestCase,
):
    """
    Pruebas automáticas del selector real de Atlas.
    """

    def setUp(
        self,
    ) -> None:

        self.registry = ToolRegistry()

        self.selector = ToolSelector(
            self.registry
        )

    def assert_tool_selected(
        self,
        text: str,
        expected_tool: str,
    ) -> ToolSelection:
        """
        Comprueba y devuelve una selección determinista.
        """

        selection = self.selector.select(
            text
        )

        self.assertIsNotNone(
            selection,
            msg=(
                f"No se seleccionó ninguna herramienta "
                f"para: {text}"
            ),
        )

        self.assertEqual(
            selection.tool_name,
            expected_tool,
        )

        return selection

    # =========================================================================
    # SELECTOR DETERMINISTA
    # =========================================================================

    def test_select_datetime_by_time(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Qué hora es?",
            "get_current_datetime",
        )

    def test_select_datetime_by_date(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Qué fecha es hoy?",
            "get_current_datetime",
        )

    def test_select_system_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Qué versión de Python tengo?",
            "get_system_info",
        )

    def test_select_cpu_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Qué procesador tengo?",
            "get_cpu_info",
        )

    def test_select_cpu_core_count(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuántos núcleos tiene mi CPU?",
            "get_cpu_info",
        )

    def test_select_ram_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuánta RAM tengo?",
            "get_ram_info",
        )

    def test_select_ram_usage(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuánta memoria RAM estoy utilizando?",
            "get_ram_info",
        )

    def test_select_disk_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuánto espacio libre tengo?",
            "get_disk_info",
        )

    def test_select_disk_drive_argument(
        self,
    ) -> None:

        selection = self.assert_tool_selected(
            "¿Cuánto espacio queda en C:?",
            "get_disk_info",
        )

        self.assertEqual(
            selection.arguments,
            {
                "drive": "C:",
            },
        )

    def test_select_gpu_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Qué tarjeta gráfica tengo?",
            "get_gpu_info",
        )

    def test_select_gpu_temperature(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Qué temperatura tiene la GPU?",
            "get_gpu_info",
        )

    def test_select_network_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuál es mi IP local?",
            "get_network_info",
        )

    def test_select_network_mac(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuál es mi dirección MAC?",
            "get_network_info",
        )

    def test_select_uptime_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuánto lleva encendido el ordenador?",
            "get_uptime_info",
        )

    def test_select_battery_info(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuánta batería queda?",
            "get_battery_info",
        )

    def test_select_memory_status(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Cuántos recuerdos tengo?",
            "get_memory_status",
        )

    def test_select_current_user(
        self,
    ) -> None:

        self.assert_tool_selected(
            "¿Quién soy?",
            "get_current_user",
        )

    def test_select_confirmation_test(
        self,
    ) -> None:

        self.assert_tool_selected(
            "Probar sistema de confirmaciones",
            "test_confirmation",
        )

    def test_general_question_returns_none(
        self,
    ) -> None:

        self.assertIsNone(
            self.selector.select(
                "Explícame qué es Docker."
            )
        )

    def test_empty_input_returns_none(
        self,
    ) -> None:

        self.assertIsNone(
            self.selector.select("")
        )

        self.assertIsNone(
            self.selector.select("   ")
        )

    def test_can_handle_known_request(
        self,
    ) -> None:

        self.assertTrue(
            self.selector.can_handle(
                "¿Qué hora es?"
            )
        )

    def test_can_handle_general_question(
        self,
    ) -> None:

        self.assertFalse(
            self.selector.can_handle(
                "¿Por qué el cielo es azul?"
            )
        )

    # =========================================================================
    # CREACIÓN SEGURA DE SELECCIONES
    # =========================================================================

    def test_create_selection_rejects_unknown_tool(
        self,
    ) -> None:

        selection = self.selector._create_selection(
            tool_name="invented_tool",
            confidence=1.0,
            reason="Prueba.",
        )

        self.assertIsNone(
            selection
        )

    def test_create_selection_accepts_registered_tool(
        self,
    ) -> None:

        selection = self.selector._create_selection(
            tool_name="get_cpu_info",
            confidence=0.9,
            reason="Prueba.",
        )

        self.assertIsNotNone(
            selection
        )

        self.assertEqual(
            selection.tool_name,
            "get_cpu_info",
        )

    # =========================================================================
    # EXTRACCIÓN DE UNIDADES
    # =========================================================================

    def test_extract_drive_with_colon(
        self,
    ) -> None:

        self.assertEqual(
            self.selector._extract_drive(
                "espacio libre en d:"
            ),
            "D:",
        )

    def test_extract_drive_without_colon(
        self,
    ) -> None:

        self.assertEqual(
            self.selector._extract_drive(
                "espacio libre en e"
            ),
            "E:",
        )

    def test_extract_drive_returns_none_without_drive(
        self,
    ) -> None:

        self.assertIsNone(
            self.selector._extract_drive(
                "cuanto espacio libre tengo"
            )
        )

    # =========================================================================
    # SELECTOR ASISTIDO POR IA
    # =========================================================================

    def test_ai_selector_accepts_valid_json(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "get_cpu_info",'
                '"arguments": {},'
                '"confidence": 0.95,'
                '"reason": "Consulta del procesador."'
                "}"
            )
        )

        selection = self.selector.select_with_ai(
            text="Dime las características del procesador.",
            provider=provider,
        )

        self.assertIsNotNone(
            selection
        )

        self.assertEqual(
            selection.tool_name,
            "get_cpu_info",
        )

        self.assertEqual(
            selection.confidence,
            0.95,
        )

    def test_ai_selector_accepts_markdown_json(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "```json\n"
                "{\n"
                '  "tool_name": "get_ram_info",\n'
                '  "arguments": {},\n'
                '  "confidence": 0.91,\n'
                '  "reason": "Consulta de RAM."\n'
                "}\n"
                "```"
            )
        )

        selection = self.selector.select_with_ai(
            text="Dime cómo va la memoria del equipo.",
            provider=provider,
        )

        self.assertIsNotNone(
            selection
        )

        self.assertEqual(
            selection.tool_name,
            "get_ram_info",
        )

    def test_ai_selector_accepts_text_around_json(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "Resultado:\n"
                "{"
                '"tool_name": "get_gpu_info",'
                '"arguments": {},'
                '"confidence": 0.90,'
                '"reason": "Consulta gráfica."'
                "}\n"
                "Fin."
            )
        )

        selection = self.selector.select_with_ai(
            text="Información del hardware gráfico.",
            provider=provider,
        )

        self.assertIsNotNone(
            selection
        )

        self.assertEqual(
            selection.tool_name,
            "get_gpu_info",
        )

    def test_ai_selector_returns_none_for_null_tool(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": null,'
                '"arguments": {},'
                '"confidence": 1.0,'
                '"reason": "Conversación general."'
                "}"
            )
        )

        selection = self.selector.select_with_ai(
            text="Explícame qué es una VLAN.",
            provider=provider,
        )

        self.assertIsNone(
            selection
        )

    def test_ai_selector_rejects_unknown_tool(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "delete_everything",'
                '"arguments": {},'
                '"confidence": 1.0,'
                '"reason": "Herramienta inventada."'
                "}"
            )
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Haz algo imposible.",
                provider=provider,
            )
        )

    def test_ai_selector_rejects_low_confidence(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "get_cpu_info",'
                '"arguments": {},'
                '"confidence": 0.50,'
                '"reason": "Selección dudosa."'
                "}"
            )
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Tal vez necesito información.",
                provider=provider,
            )
        )

    def test_ai_selector_accepts_minimum_confidence(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "get_cpu_info",'
                '"arguments": {},'
                '"confidence": 0.75,'
                '"reason": "Confianza mínima válida."'
                "}"
            )
        )

        selection = self.selector.select_with_ai(
            text="Información del procesador.",
            provider=provider,
        )

        self.assertIsNotNone(
            selection
        )

    def test_ai_selector_rejects_invalid_arguments(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "get_disk_info",'
                '"arguments": ["C:"],'
                '"confidence": 0.95,'
                '"reason": "Argumentos inválidos."'
                "}"
            )
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Consulta el disco.",
                provider=provider,
            )
        )

    def test_ai_selector_preserves_arguments(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "get_disk_info",'
                '"arguments": {"drive": "D:"},'
                '"confidence": 0.96,'
                '"reason": "Consulta de unidad."'
                "}"
            )
        )

        selection = self.selector.select_with_ai(
            text="Consulta mi segunda unidad.",
            provider=provider,
        )

        self.assertIsNotNone(
            selection
        )

        self.assertEqual(
            selection.arguments,
            {
                "drive": "D:",
            },
        )

    def test_ai_selector_rejects_invalid_json(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response="Utiliza la herramienta de CPU."
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Información de CPU.",
                provider=provider,
            )
        )

    def test_ai_selector_rejects_non_dictionary_json(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response='["get_cpu_info"]'
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Información de CPU.",
                provider=provider,
            )
        )

    def test_ai_selector_rejects_non_string_tool_name(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": 123,'
                '"arguments": {},'
                '"confidence": 1.0,'
                '"reason": "Nombre inválido."'
                "}"
            )
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Información.",
                provider=provider,
            )
        )

    def test_ai_selector_rejects_invalid_confidence(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "get_cpu_info",'
                '"arguments": {},'
                '"confidence": "desconocida",'
                '"reason": "Confianza inválida."'
                "}"
            )
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Información.",
                provider=provider,
            )
        )

    def test_ai_selector_clamps_confidence_above_one(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": "get_cpu_info",'
                '"arguments": {},'
                '"confidence": 5,'
                '"reason": "Confianza excesiva."'
                "}"
            )
        )

        selection = self.selector.select_with_ai(
            text="Información de CPU.",
            provider=provider,
        )

        self.assertIsNotNone(
            selection
        )

        self.assertEqual(
            selection.confidence,
            1.0,
        )

    def test_ai_selector_returns_none_without_provider(
        self,
    ) -> None:

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Información.",
                provider=None,
            )
        )

    def test_ai_selector_handles_runtime_error(
        self,
    ) -> None:

        provider = FakeAIProvider(
            exception=RuntimeError(
                "Proveedor no disponible."
            )
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Información.",
                provider=provider,
            )
        )

    def test_ai_selector_handles_value_error(
        self,
    ) -> None:

        provider = FakeAIProvider(
            exception=ValueError(
                "Respuesta inválida."
            )
        )

        self.assertIsNone(
            self.selector.select_with_ai(
                text="Información.",
                provider=provider,
            )
        )

    def test_ai_prompt_contains_request(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": null,'
                '"arguments": {},'
                '"confidence": 1.0,'
                '"reason": "Conversación general."'
                "}"
            )
        )

        request = (
            "Comprueba si alguna herramienta resuelve esto."
        )

        self.selector.select_with_ai(
            text=request,
            provider=provider,
        )

        self.assertIsNotNone(
            provider.received_prompt
        )

        self.assertIn(
            request,
            provider.received_prompt,
        )

    def test_ai_prompt_contains_registered_tools(
        self,
    ) -> None:

        provider = FakeAIProvider(
            response=(
                "{"
                '"tool_name": null,'
                '"arguments": {},'
                '"confidence": 1.0,'
                '"reason": "Conversación general."'
                "}"
            )
        )

        self.selector.select_with_ai(
            text="Pregunta general.",
            provider=provider,
        )

        self.assertIn(
            "get_cpu_info",
            provider.received_prompt,
        )

        self.assertIn(
            "get_ram_info",
            provider.received_prompt,
        )


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":

    unittest.main()
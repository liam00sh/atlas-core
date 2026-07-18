"""Pruebas de validación y recorte del contexto conversacional de IA."""

import unittest

from ai.context.context_manager import AIContextManager


class AIContextManagerTests(unittest.TestCase):
    def test_odd_limit_does_not_leave_orphan_assistant_message(self):
        context = AIContextManager(max_messages=5)
        context.add_message("user", "pregunta uno")
        context.add_message("assistant", "respuesta uno")
        context.add_message("user", "pregunta dos")
        context.add_message("assistant", "respuesta dos")
        context.add_message("user", "pregunta tres")
        context.add_message("assistant", "respuesta tres")

        messages = context.get_messages()
        self.assertLessEqual(len(messages), 5)
        self.assertTrue(messages)
        self.assertNotEqual(messages[0]["role"], "assistant")
        for index, message in enumerate(messages):
            if message["role"] == "assistant":
                self.assertGreater(index, 0)
                self.assertEqual(messages[index - 1]["role"], "user")

    def test_empty_assistant_messages_are_rejected(self):
        context = AIContextManager(max_messages=5)
        for invalid in ("", "   "):
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaises(ValueError):
                    context.add_message("assistant", invalid)

    def test_non_text_values_are_rejected(self):
        context = AIContextManager(max_messages=5)
        for role, content in ((None, "texto"), ("assistant", None), (7, "texto"), ("user", 9)):
            with self.subTest(role=role, content=content):
                with self.assertRaises((TypeError, ValueError)):
                    context.add_message(role, content)


if __name__ == "__main__":
    unittest.main()

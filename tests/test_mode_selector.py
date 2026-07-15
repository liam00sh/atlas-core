"""Pruebas del selector automático de modos."""

import unittest

from assistant_identity.mode import CLASSIC_MODE, EMPATHETIC_MODE, FUN_MODE, WORK_MODE
from assistant_identity.mode_selector import ModeSelection, ModeSelector


class ModeSelectorTests(unittest.TestCase):
    def setUp(self):
        self.selector = ModeSelector()

    def test_technical_messages_select_work(self):
        messages = (
            "Necesito corregir un error de Python y revisar este archivo",
            "Ayúdame con Docker, Linux y la configuración de red",
            "Vamos a preparar los tests del proyecto",
        )
        for message in messages:
            with self.subTest(message=message):
                result = self.selector.select(message)
                self.assertEqual(result.mode_name, WORK_MODE)
                self.assertGreater(result.confidence, 0)

    def test_emotional_messages_select_empathetic(self):
        messages = (
            "Estoy muy triste y necesito hablar con alguien",
            "Me siento mal y necesito apoyo emocional",
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(self.selector.select(message).mode_name, EMPATHETIC_MODE)

    def test_fun_messages_select_fun(self):
        messages = (
            "Cuéntame un chiste divertido para pasar el rato",
            "Vamos a jugar y a reírnos un poco",
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertEqual(self.selector.select(message).mode_name, FUN_MODE)

    def test_neutral_message_selects_classic(self):
        self.assertEqual(self.selector.select("Hola, ¿qué tal?").mode_name, CLASSIC_MODE)

    def test_explicit_command_text_is_still_classifiable_but_not_authoritative(self):
        result = self.selector.select("cambia a modo trabajo")
        self.assertIn(result.mode_name, {CLASSIC_MODE, WORK_MODE, FUN_MODE, EMPATHETIC_MODE})
        self.assertIsInstance(result.reason, str)

    def test_selection_validates_confidence(self):
        with self.assertRaises(ValueError):
            ModeSelection(CLASSIC_MODE, 1.1, "Motivo")
        with self.assertRaises(ValueError):
            ModeSelection(CLASSIC_MODE, -0.1, "Motivo")


if __name__ == "__main__":
    unittest.main()

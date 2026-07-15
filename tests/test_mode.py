"""Pruebas para AssistantMode."""

import unittest

from assistant_identity.mode import AssistantMode, CLASSIC_MODE, get_mode_label, is_valid_mode_name


class AssistantModeTests(unittest.TestCase):
    def test_normalizes_and_serializes_mode(self):
        mode = AssistantMode(" CLASSIC ", " Clásico ", " Conversación normal ", " Responde normal. ")
        self.assertEqual(mode.name, CLASSIC_MODE)
        self.assertEqual(mode.label, "Clásico")
        self.assertEqual(mode.to_dict()["name"], CLASSIC_MODE)
        self.assertIn("Responde normal", mode.get_prompt_context())

    def test_rejects_invalid_levels_and_names(self):
        with self.assertRaises(ValueError):
            AssistantMode("invalid", "X", "X", "X")
        with self.assertRaises(ValueError):
            AssistantMode(CLASSIC_MODE, "X", "X", "X", humor_level=11)

    def test_helpers(self):
        self.assertTrue(is_valid_mode_name(CLASSIC_MODE))
        self.assertEqual(get_mode_label(CLASSIC_MODE), "Clásico")


if __name__ == "__main__":
    unittest.main()

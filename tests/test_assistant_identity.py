"""Pruebas de las identidades Daxter y Coco."""

import unittest

from assistant_identity.assistant_identity import AssistantIdentity
from assistant_identity.identity_registry import get_identity
from assistant_identity.mode import CLASSIC_MODE, EMPATHETIC_MODE, FUN_MODE, WORK_MODE, AssistantMode
from assistant_identity.phrase_bank import GREETINGS, PhraseBank


class AssistantIdentityTests(unittest.TestCase):
    def setUp(self):
        mode = AssistantMode(CLASSIC_MODE, "Clásico", "Normal", "Responde con naturalidad.")
        self.identity = AssistantIdentity(
            name="daxter",
            display_name="Test",
            grammatical_gender="neutral",
            description="Identidad de prueba",
            base_personality_prompt="Sé útil.",
            default_mode=CLASSIC_MODE,
            modes={CLASSIC_MODE: mode},
            phrase_bank=PhraseBank("daxter", {GREETINGS: ("Hola",)}),
            aliases=("Prueba",),
        )

    def test_lookup_alias_mode_and_phrase(self):
        self.assertTrue(self.identity.matches_name("prueba"))
        self.assertTrue(self.identity.has_mode(CLASSIC_MODE))
        self.assertEqual(self.identity.get_random_phrase(GREETINGS), "Hola")

    def test_prompt_context_contains_identity_and_mode(self):
        context = self.identity.get_prompt_context(CLASSIC_MODE)
        self.assertIn("Test", context)
        self.assertIn("Clásico", context)
        self.assertIn("Sé útil", context)

    def test_invalid_default_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            AssistantIdentity(
                name="daxter",
                display_name="Bad",
                grammatical_gender="neutral",
                description="x",
                base_personality_prompt="x",
                default_mode=WORK_MODE,
                modes={CLASSIC_MODE: self.identity.get_mode(CLASSIC_MODE)},
            )

    def test_daxter_and_coco_have_complete_mode_sets(self):
        for name in ("daxter", "coco"):
            identity = get_identity(name)
            self.assertIsNotNone(identity)
            self.assertEqual(identity.default_mode, CLASSIC_MODE)
            for mode_name in (CLASSIC_MODE, WORK_MODE, FUN_MODE, EMPATHETIC_MODE):
                with self.subTest(identity=name, mode=mode_name):
                    self.assertTrue(identity.has_mode(mode_name))
                    self.assertIsNotNone(identity.get_mode(mode_name))
                    context = identity.get_prompt_context(mode_name)
                    self.assertIn(identity.display_name, context)

    def test_identity_aliases_do_not_overlap(self):
        daxter = get_identity("daxter")
        coco = get_identity("coco")
        self.assertFalse(daxter.matches_name("coco"))
        self.assertFalse(coco.matches_name("daxter"))


if __name__ == "__main__":
    unittest.main()

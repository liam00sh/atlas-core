"""Pruebas para los bancos de frases de Daxter y Coco."""

import unittest

from assistant_identity.identity_registry import get_identity
from assistant_identity.phrase_bank import GREETINGS, IDENTITY_CHANGED, JOKES, MODE_CHANGED, PhraseBank


class PhraseBankTests(unittest.TestCase):
    def test_normalizes_categories_and_removes_duplicates(self):
        bank = PhraseBank("Daxter", {GREETINGS: [" Hola ", "Hola", "Buenas"], JOKES: []})
        self.assertEqual(bank.identity_name, "daxter")
        self.assertEqual(bank.get_phrases(GREETINGS), ("Hola", "Buenas"))
        self.assertEqual(bank.count_phrases(GREETINGS), 2)

    def test_random_phrase_and_default(self):
        bank = PhraseBank("Coco", {GREETINGS: ("Hola",)})
        self.assertEqual(bank.get_random_phrase(GREETINGS), "Hola")
        self.assertEqual(bank.get_random_phrase(JOKES, "Sin bromas"), "Sin bromas")

    def test_invalid_category_is_rejected(self):
        with self.assertRaises(ValueError):
            PhraseBank("Daxter", {"invalid": ("x",)})

    def test_both_official_identities_have_operational_phrase_banks(self):
        for identity_name in ("daxter", "coco"):
            identity = get_identity(identity_name)
            bank = identity.phrase_bank
            self.assertGreater(len(bank.list_categories()), 0)
            self.assertGreater(bank.count_phrases(GREETINGS), 0)
            self.assertGreater(bank.count_phrases(IDENTITY_CHANGED), 0)
            self.assertGreater(bank.count_phrases(MODE_CHANGED), 0)
            self.assertIsInstance(bank.get_random_phrase(GREETINGS), str)


if __name__ == "__main__":
    unittest.main()

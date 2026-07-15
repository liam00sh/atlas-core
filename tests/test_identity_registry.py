"""Pruebas del registro de identidades Daxter y Coco."""

import unittest

from assistant_identity.identity_registry import get_default_identity, get_identity, has_identity, list_identities


class IdentityRegistryTests(unittest.TestCase):
    def test_contains_exactly_registered_main_identities(self):
        names = {
            identity.name
            for identity in list_identities()
        }
        self.assertEqual(names, {"daxter", "coco"})
        self.assertTrue(has_identity("DAXTER"))
        self.assertTrue(has_identity("coco"))

    def test_lookup_and_default(self):
        self.assertEqual(get_identity("Daxter").display_name, "Daxter")
        self.assertEqual(get_identity("Coco").display_name, "Coco")
        self.assertEqual(get_default_identity().name, "daxter")

    def test_lookup_accepts_visible_names_and_aliases_without_confusion(self):
        self.assertEqual(get_identity("daxter").name, "daxter")
        self.assertEqual(get_identity("coco").name, "coco")
        self.assertNotEqual(get_identity("daxter").name, get_identity("coco").name)

    def test_unknown_identity_raises_key_error(self):
        with self.assertRaises(KeyError):
            get_identity("desconocida")
        self.assertFalse(has_identity("desconocida"))


if __name__ == "__main__":
    unittest.main()

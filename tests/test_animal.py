"""Pruebas unitarias para identity.animal."""

import unittest

from identity.animal import ACTIVE, CAT, FEMALE, MALE, Animal


class AnimalTests(unittest.TestCase):
    def test_normalization_aliases_and_matching(self):
        animal = Animal(
            name="  Funcionario  ",
            species=" CAT ",
            aliases=["Funció", " función ", "Funció"],
            sex=MALE,
            status=ACTIVE,
        )
        self.assertEqual(animal.name, "Funcionario")
        self.assertEqual(animal.species, CAT)
        self.assertEqual(animal.aliases, ["Funció", "función"])
        self.assertTrue(animal.matches_name("FUNCIÓ"))

    def test_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            Animal(name="", species=CAT)
        with self.assertRaises(ValueError):
            Animal(name="Estrella", species="")
        with self.assertRaises(ValueError):
            Animal(name="Estrella", species="dog", sex="invalid")
        with self.assertRaises(ValueError):
            Animal(name="Estrella", species="dog", encounter_count=-1)

    def test_updates_and_serialization(self):
        animal = Animal(name="Estrella", species="dog", sex=FEMALE)
        animal.update_summary("Perra de los abuelos de Saray")
        animal.register_encounter("2026-07-14T12:00:00")
        restored = Animal.from_dict(animal.to_dict())
        self.assertEqual(restored.to_dict(), animal.to_dict())


if __name__ == "__main__":
    unittest.main()

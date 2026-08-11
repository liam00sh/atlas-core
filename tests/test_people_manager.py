"""Pruebas unitarias para PeopleManager."""

import tempfile
import unittest
from pathlib import Path

from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager


class PeopleManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manager = PeopleManager(IdentityStorage(Path(self.temp_dir.name)))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_and_finds_person_by_name_alias_and_profile(self):
        person = self.manager.create_user_person(
            "Alex Romero",
            "Alex",
            aliases=["Alex", "AlexAnterior"],
            grammatical_gender="masculine",
        )
        self.assertIsNotNone(person)
        self.assertEqual(self.manager.find_person_by_name("AlexAnterior").id, person.id)
        self.assertEqual(self.manager.find_person_by_user_profile("Alex").id, person.id)

    def test_does_not_duplicate_obvious_person(self):
        self.assertIsNotNone(self.manager.create_person("Vega", aliases=["Sari"]))
        self.assertIsNone(self.manager.create_person("Vega"))

    def test_ambiguous_alias_returns_multiple_people(self):
        self.manager.create_person("Zoe Soler", aliases=["Zoe"])
        self.manager.create_person("Zoe Vidal", aliases=["Zoe"])
        matches = self.manager.find_people_by_name("Zoe")
        self.assertEqual(len(matches), 2)
        self.assertIsNone(self.manager.find_person_by_name("Zoe"))

    def test_creates_and_resolves_animal(self):
        animal = self.manager.create_animal("Nube", "cat", aliases=["Nube"])
        entity_type, resolved = self.manager.resolve_entity("Nube", preferred_type="animal")
        self.assertEqual(entity_type, "animal")
        self.assertEqual(resolved.id, animal.id)


if __name__ == "__main__":
    unittest.main()

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
            "Liam Vicente Martínez",
            "Liam",
            aliases=["Liam", "Nerea Vicente Martínez"],
            grammatical_gender="masculine",
        )
        self.assertIsNotNone(person)
        self.assertEqual(self.manager.find_person_by_name("nerea vicente martínez").id, person.id)
        self.assertEqual(self.manager.find_person_by_user_profile("liam").id, person.id)

    def test_does_not_duplicate_obvious_person(self):
        self.assertIsNotNone(self.manager.create_person("Saray", aliases=["Sari"]))
        self.assertIsNone(self.manager.create_person("saray"))

    def test_ambiguous_alias_returns_multiple_people(self):
        self.manager.create_person("Pepi Vicente Navarro", aliases=["Pepi"])
        self.manager.create_person("Pepi Carreres López", aliases=["Pepi"])
        matches = self.manager.find_people_by_name("Pepi")
        self.assertEqual(len(matches), 2)
        self.assertIsNone(self.manager.find_person_by_name("Pepi"))

    def test_creates_and_resolves_animal(self):
        animal = self.manager.create_animal("Funcionario", "cat", aliases=["Funcio"])
        entity_type, resolved = self.manager.resolve_entity("Funcio", preferred_type="animal")
        self.assertEqual(entity_type, "animal")
        self.assertEqual(resolved.id, animal.id)


if __name__ == "__main__":
    unittest.main()

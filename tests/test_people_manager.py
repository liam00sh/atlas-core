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
            "REDACTED_46087f8d7037",
            "REDACTED_2c7b6821719d",
            aliases=["REDACTED_2c7b6821719d", "REDACTED_e97345c31916"],
            grammatical_gender="masculine",
        )
        self.assertIsNotNone(person)
        self.assertEqual(self.manager.find_person_by_name("REDACTED_c4f17676a981").id, person.id)
        self.assertEqual(self.manager.find_person_by_user_profile("REDACTED_f73137d930c3").id, person.id)

    def test_does_not_duplicate_obvious_person(self):
        self.assertIsNotNone(self.manager.create_person("REDACTED_bc04a68d9192", aliases=["Sari"]))
        self.assertIsNone(self.manager.create_person("REDACTED_7b9528898599"))

    def test_ambiguous_alias_returns_multiple_people(self):
        self.manager.create_person("REDACTED_32885d880536", aliases=["REDACTED_342ad0893cb2"])
        self.manager.create_person("REDACTED_e3b252570a2f", aliases=["REDACTED_342ad0893cb2"])
        matches = self.manager.find_people_by_name("REDACTED_342ad0893cb2")
        self.assertEqual(len(matches), 2)
        self.assertIsNone(self.manager.find_person_by_name("REDACTED_342ad0893cb2"))

    def test_creates_and_resolves_animal(self):
        animal = self.manager.create_animal("REDACTED_c0240dd983fa", "cat", aliases=["REDACTED_0f38c2ded26f"])
        entity_type, resolved = self.manager.resolve_entity("REDACTED_0f38c2ded26f", preferred_type="animal")
        self.assertEqual(entity_type, "animal")
        self.assertEqual(resolved.id, animal.id)


if __name__ == "__main__":
    unittest.main()

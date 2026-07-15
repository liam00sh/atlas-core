"""Pruebas de persistencia aislada para IdentityStorage."""

import json
import tempfile
import unittest
from pathlib import Path

from identity.animal import Animal
from identity.identity_storage import IdentityStorage
from identity.person import Person
from identity.people_manager import PeopleManager
from identity.relationship import MOTHER, Relationship


class IdentityStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = IdentityStorage(Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_storage_files(self):
        for filename in ("people.json", "animals.json", "relationships.json"):
            path = Path(self.temp_dir.name) / filename
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), [])

    def test_round_trip_entities(self):
        person = Person(name="Liam")
        animal = Animal(name="Gato", species="cat")
        self.assertTrue(self.storage.add_person(person))
        self.assertTrue(self.storage.add_animal(animal))
        self.assertEqual(self.storage.get_person_by_id(person.id).name, "Liam")
        self.assertEqual(self.storage.get_animal_by_id(animal.id).name, "Gato")

    def test_rejects_duplicate_ids(self):
        person = Person(name="Liam")
        self.assertTrue(self.storage.add_person(person))
        self.assertFalse(self.storage.add_person(person))

    def test_delete_entity_removes_associated_relationships(self):
        mother = Person(name="Mary")
        child = Person(name="Liam")
        self.storage.add_person(mother)
        self.storage.add_person(child)
        relationship = Relationship(
            source_entity_id=mother.id,
            relationship_type=MOTHER,
            target_entity_id=child.id,
        )
        self.storage.add_relationship(relationship)
        manager = PeopleManager(self.storage)
        self.assertTrue(manager.delete_person(mother.id))
        self.assertEqual(self.storage.load_relationships(), [])


if __name__ == "__main__":
    unittest.main()

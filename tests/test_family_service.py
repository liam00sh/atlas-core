"""Pruebas para el servicio de consultas familiares."""

import tempfile
import unittest
from pathlib import Path

from identity.family_initializer import FamilyInitializer
from identity.family_service import FamilyService
from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.relationship_engine import RelationshipEngine


class FamilyServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.storage = IdentityStorage(Path(cls.temp_dir.name))
        cls.people = PeopleManager(cls.storage)
        cls.engine = RelationshipEngine(cls.people, cls.storage)
        FamilyInitializer(cls.people, cls.engine).initialize()
        cls.service = FamilyService(cls.people, cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_describes_known_person_and_handles_unknown(self):
        description = self.service.describe_person_family("Liam Vicente Martínez")
        self.assertIsInstance(description, str)
        self.assertTrue(description.strip())
        self.assertIn("No conozco", self.service.describe_person_family("Persona inexistente"))

    def test_ambiguous_name_is_reported_without_arbitrary_selection(self):
        description = self.service.describe_person_family("Pepi")
        self.assertIn("ambigua", description.casefold())
        self.assertIn("Pepi Vicente Navarro", description)
        self.assertIn("Pepi Carreres López", description)

    def test_liam_alias_resolves_to_same_family(self):
        current = self.service.describe_person_family("Liam Vicente Martínez")
        previous = self.service.describe_person_family("Nerea Vicente Martínez")
        self.assertEqual(current, previous)

    def test_family_description_contains_people_and_animals(self):
        description = self.service.describe_person_family("Liam Vicente Martínez")
        self.assertIn("Saray", description)
        self.assertIn("Don Gato", description)

    def test_finds_direct_or_two_step_family_connections(self):
        self.assertIsInstance(self.service.find_connection("Liam Vicente Martínez", "Adra"), list)
        self.assertIsInstance(self.service.find_connection("Saray Izquierdo Carreres", "Noa Melinte Carreres"), list)
        self.assertIsInstance(self.service.find_connection("Liam Vicente Martínez", "Estrella"), list)

    def test_unknown_or_ambiguous_connection_returns_empty_list(self):
        self.assertEqual(self.service.find_connection("Persona inexistente", "Liam Vicente Martínez"), [])
        self.assertEqual(self.service.find_connection("Pepi", "Liam Vicente Martínez"), [])


if __name__ == "__main__":
    unittest.main()

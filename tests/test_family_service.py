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
        description = self.service.describe_person_family("REDACTED_46087f8d7037")
        self.assertIsInstance(description, str)
        self.assertTrue(description.strip())
        self.assertIn("No conozco", self.service.describe_person_family("Persona inexistente"))

    def test_ambiguous_name_is_reported_without_arbitrary_selection(self):
        description = self.service.describe_person_family("REDACTED_342ad0893cb2")
        self.assertIn("ambigua", description.casefold())
        self.assertIn("REDACTED_32885d880536", description)
        self.assertIn("REDACTED_e3b252570a2f", description)

    def test_REDACTED_f73137d930c3_alias_resolves_to_same_family(self):
        current = self.service.describe_person_family("REDACTED_46087f8d7037")
        previous = self.service.describe_person_family("REDACTED_e97345c31916")
        self.assertEqual(current, previous)

    def test_family_description_contains_people_and_animals(self):
        description = self.service.describe_person_family("REDACTED_46087f8d7037")
        self.assertIn("REDACTED_bc04a68d9192", description)
        self.assertIn("REDACTED_73007cb40c65", description)

    def test_finds_direct_or_two_step_family_connections(self):
        self.assertIsInstance(self.service.find_connection("REDACTED_46087f8d7037", "REDACTED_32e08b362c19"), list)
        self.assertIsInstance(self.service.find_connection("REDACTED_8762331d93e2", "REDACTED_91f6198b34bc"), list)
        self.assertIsInstance(self.service.find_connection("REDACTED_46087f8d7037", "REDACTED_06768d0d9b38"), list)

    def test_resolves_relationships_for_people_from_every_family_branch(self):
        cases = (
            ("REDACTED_8762331d93e2", "REDACTED_65dc3df1f2c0", "cuñada"),
            ("REDACTED_8762331d93e2", "REDACTED_d3969f681ba1", "cuñada"),
            ("REDACTED_8762331d93e2", "REDACTED_ba2c2b03ba9a", "nuera"),
            ("REDACTED_8762331d93e2", "REDACTED_0a0e53340b75", "nuera"),
            ("REDACTED_ba2c2b03ba9a", "REDACTED_8762331d93e2", "suegra"),
            ("REDACTED_e3b252570a2f", "REDACTED_46087f8d7037", "suegra"),
            ("REDACTED_7ac2d8ee0281", "REDACTED_8762331d93e2", "tía"),
            ("REDACTED_8762331d93e2", "REDACTED_7ac2d8ee0281", "sobrina"),
        )
        for source, target, expected in cases:
            with self.subTest(source=source, target=target):
                description = self.service.describe_relationship_between(
                    source,
                    target,
                )
                self.assertIn(expected, description.casefold())

    def test_every_direct_relationship_is_describable_in_both_directions(self):
        entities = {
            ("person", person.id): person
            for person in self.people.get_people()
        }
        entities.update({
            ("animal", animal.id): animal
            for animal in self.people.get_animals()
        })

        for relationship in self.engine.get_relationships():
            source = entities[(
                relationship.source_entity_type,
                relationship.source_entity_id,
            )]
            target = entities[(
                relationship.target_entity_type,
                relationship.target_entity_id,
            )]
            for first, second in ((source, target), (target, source)):
                with self.subTest(source=first.name, target=second.name):
                    description = self.service.describe_relationship_between(
                        first.name,
                        second.name,
                    )
                    self.assertTrue(description.strip())
                    self.assertNotIn("None", description)

    def test_every_person_and_animal_pair_has_a_safe_answer(self):
        entities = [
            *[("person", person) for person in self.people.get_people()],
            *[("animal", animal) for animal in self.people.get_animals()],
        ]

        for index, (source_type, source) in enumerate(entities):
            for target_type, target in entities[index + 1:]:
                with self.subTest(source=source.name, target=target.name):
                    forward = (
                        self.engine
                        .describe_relationship_between_entities(
                            source.id,
                            source_type,
                            target.id,
                            target_type,
                        )
                    )
                    reverse = (
                        self.engine
                        .describe_relationship_between_entities(
                            target.id,
                            target_type,
                            source.id,
                            source_type,
                        )
                    )
                    self.assertTrue(forward.strip())
                    self.assertTrue(reverse.strip())
                    self.assertNotIn("None", forward)
                    self.assertNotIn("None", reverse)
                    if not self.engine.find_shortest_relationship_path(
                        source.id,
                        source_type,
                        target.id,
                        target_type,
                        max_depth=4,
                    ):
                        self.assertIn("no hay", forward.casefold())
                        self.assertIn("no hay", reverse.casefold())

    def test_unknown_or_ambiguous_connection_returns_empty_list(self):
        self.assertEqual(self.service.find_connection("Persona inexistente", "REDACTED_46087f8d7037"), [])
        self.assertEqual(self.service.find_connection("REDACTED_342ad0893cb2", "REDACTED_46087f8d7037"), [])


if __name__ == "__main__":
    unittest.main()

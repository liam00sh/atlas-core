"""Pruebas de integración aislada para RelationshipEngine."""

import tempfile
import unittest
from pathlib import Path

from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.relationship import BROTHER, COUSIN, PARTNER, SISTER
from identity.relationship_engine import RelationshipEngine


class RelationshipEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = IdentityStorage(Path(self.temp_dir.name))
        self.people = PeopleManager(self.storage)
        self.engine = RelationshipEngine(self.people, self.storage)
        self.REDACTED_f73137d930c3 = self.people.create_user_person("REDACTED_2c7b6821719d", "REDACTED_2c7b6821719d", grammatical_gender="masculine")
        self.REDACTED_7b9528898599 = self.people.create_user_person("REDACTED_bc04a68d9192", "REDACTED_bc04a68d9192", grammatical_gender="feminine")
        self.REDACTED_1029b731cc39 = self.people.create_person("REDACTED_2ff76a67ecfb", grammatical_gender="masculine")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_direct_and_inverse_relationship(self):
        direct, inverse = self.engine.create_relationship_by_name(
            source="REDACTED_2ff76a67ecfb", relationship_type=BROTHER, target="REDACTED_bc04a68d9192", create_inverse=True
        )
        self.assertIsNotNone(direct)
        self.assertIsNotNone(inverse)
        self.assertEqual(inverse.relationship_type, SISTER)

    def test_allows_multiple_distinct_relationships_between_same_people(self):
        self.engine.create_relationship_by_name(source="REDACTED_2ff76a67ecfb", relationship_type=BROTHER, target="REDACTED_2c7b6821719d")
        self.engine.create_relationship_by_name(source="REDACTED_2ff76a67ecfb", relationship_type=COUSIN, target="REDACTED_2c7b6821719d")
        types = {
            rel.relationship_type
            for rel in self.engine.get_outgoing_relationships(self.REDACTED_1029b731cc39.id, "person")
            if rel.target_entity_id == self.REDACTED_f73137d930c3.id
        }
        self.assertIn(BROTHER, types)
        self.assertIn(COUSIN, types)

    def test_exact_duplicate_is_idempotent(self):
        first = self.engine.create_relationship_by_name(source="REDACTED_2c7b6821719d", relationship_type=PARTNER, target="REDACTED_bc04a68d9192")
        count = self.engine.get_relationship_count()
        second = self.engine.create_relationship_by_name(source="REDACTED_2c7b6821719d", relationship_type=PARTNER, target="REDACTED_bc04a68d9192")
        self.assertEqual(self.engine.get_relationship_count(), count)
        self.assertEqual(first[0].id, second[0].id)

    def test_missing_entity_raises_clear_error(self):
        with self.assertRaises(ValueError):
            self.engine.create_relationship_by_name(source="Desconocido", relationship_type=PARTNER, target="REDACTED_bc04a68d9192")


if __name__ == "__main__":
    unittest.main()

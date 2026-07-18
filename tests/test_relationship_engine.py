"""Pruebas de integración aislada para RelationshipEngine."""

import tempfile
import unittest
from pathlib import Path

from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.relationship import BROTHER, COUSIN, DAUGHTER, MOTHER, PARTNER, SISTER, SON
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

    def test_infers_in_law_relationships_from_partner_and_family(self):
        mother = self.people.create_person(
            "María", grammatical_gender="feminine"
        )
        brother = self.people.create_person(
            "REDACTED_1b4b1a7f2126", grammatical_gender="masculine"
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_2c7b6821719d",
            relationship_type=PARTNER,
            target="REDACTED_bc04a68d9192",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_2c7b6821719d",
            relationship_type=SON,
            target="María",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_1b4b1a7f2126",
            relationship_type=BROTHER,
            target="REDACTED_2c7b6821719d",
            create_inverse=True,
        )

        self.assertEqual(
            self.engine.infer_relationship_label(
                self.REDACTED_7b9528898599.id, "person", mother.id, "person"
            ),
            "nuera",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                mother.id, "person", self.REDACTED_7b9528898599.id, "person"
            ),
            "suegra",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                self.REDACTED_7b9528898599.id, "person", brother.id, "person"
            ),
            "cuñada",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                brother.id, "person", self.REDACTED_7b9528898599.id, "person"
            ),
            "cuñado",
        )

    def test_infers_grandparent_aunt_and_niece_relationships(self):
        grandmother = self.people.create_person(
            "Abuela", grammatical_gender="feminine"
        )
        aunt = self.people.create_person(
            "REDACTED_abbdcaee9944", grammatical_gender="feminine"
        )
        child = self.people.create_person(
            "REDACTED_d296a64095dd", grammatical_gender="feminine"
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_bc04a68d9192",
            relationship_type=DAUGHTER,
            target="REDACTED_2c7b6821719d",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_2c7b6821719d",
            relationship_type=SON,
            target="Abuela",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_abbdcaee9944",
            relationship_type=SISTER,
            target="REDACTED_2c7b6821719d",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_d296a64095dd",
            relationship_type=DAUGHTER,
            target="REDACTED_abbdcaee9944",
            create_inverse=True,
        )

        self.assertEqual(
            self.engine.infer_relationship_label(
                grandmother.id, "person", self.REDACTED_7b9528898599.id, "person"
            ),
            "abuela",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                aunt.id, "person", self.REDACTED_7b9528898599.id, "person"
            ),
            "tía",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                self.REDACTED_7b9528898599.id, "person", aunt.id, "person"
            ),
            "sobrina",
        )

    def test_shortest_path_and_description_support_animals(self):
        pet = self.people.create_animal(
            "REDACTED_864fbc635ba2",
            species="cat",
            sex="male",
            grammatical_gender="masculine",
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_2c7b6821719d",
            relationship_type="pet_owner",
            target="REDACTED_864fbc635ba2",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="REDACTED_2c7b6821719d",
            relationship_type=PARTNER,
            target="REDACTED_bc04a68d9192",
            create_inverse=True,
        )

        path = self.engine.find_shortest_relationship_path(
            self.REDACTED_7b9528898599.id,
            "person",
            pet.id,
            "animal",
        )
        self.assertTrue(path)
        description = self.engine.describe_relationship_between_entities(
            self.REDACTED_7b9528898599.id,
            "person",
            pet.id,
            "animal",
        )
        self.assertIn("REDACTED_bc04a68d9192", description)
        self.assertIn("REDACTED_864fbc635ba2", description)
        self.assertNotIn("None", description)

    def test_missing_entity_raises_clear_error(self):
        with self.assertRaises(ValueError):
            self.engine.create_relationship_by_name(source="Desconocido", relationship_type=PARTNER, target="REDACTED_bc04a68d9192")


if __name__ == "__main__":
    unittest.main()

"""Pruebas de carga idempotente del árbol familiar."""

import tempfile
import unittest
from pathlib import Path

from identity.family_data import FAMILY_ANIMALS, FAMILY_PEOPLE, FAMILY_RELATIONSHIPS
from identity.family_initializer import FamilyInitializer
from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.relationship_engine import RelationshipEngine


class FamilyInitializerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name)
        self.storage = IdentityStorage(self.storage_path)
        self.people = PeopleManager(self.storage)
        self.engine = RelationshipEngine(self.people, self.storage)
        self.initializer = FamilyInitializer(self.people, self.engine)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_run_populates_and_second_run_is_idempotent(self):
        first = self.initializer.initialize()
        self.assertEqual(first["created_people"], len(FAMILY_PEOPLE))
        self.assertEqual(first["created_animals"], len(FAMILY_ANIMALS))
        self.assertEqual(first["created_relationships"], len(FAMILY_RELATIONSHIPS) * 2)
        totals = (
            self.people.get_person_count(),
            self.people.get_animal_count(),
            self.engine.get_relationship_count(),
        )
        second = self.initializer.initialize()
        self.assertEqual(second, {"created_people": 0, "created_animals": 0, "created_relationships": 0})
        self.assertEqual(
            totals,
            (
                self.people.get_person_count(),
                self.people.get_animal_count(),
                self.engine.get_relationship_count(),
            ),
        )

    def test_reloading_storage_remains_idempotent(self):
        self.initializer.initialize()
        reloaded_storage = IdentityStorage(self.storage_path)
        reloaded_people = PeopleManager(reloaded_storage)
        reloaded_engine = RelationshipEngine(reloaded_people, reloaded_storage)
        result = FamilyInitializer(reloaded_people, reloaded_engine).initialize()
        self.assertEqual(result, {"created_people": 0, "created_animals": 0, "created_relationships": 0})
        self.assertEqual(reloaded_people.get_person_count(), len(FAMILY_PEOPLE))
        self.assertEqual(reloaded_people.get_animal_count(), len(FAMILY_ANIMALS))
        self.assertEqual(reloaded_engine.get_relationship_count(), len(FAMILY_RELATIONSHIPS) * 2)

    def test_REDACTED_f73137d930c3_aliases_resolve_to_one_record(self):
        self.initializer.initialize()
        REDACTED_f73137d930c3 = self.people.find_person_by_name("REDACTED_46087f8d7037")
        previous_name = self.people.find_person_by_name("REDACTED_e97345c31916")
        self.assertIsNotNone(REDACTED_f73137d930c3)
        self.assertIsNotNone(previous_name)
        self.assertEqual(REDACTED_f73137d930c3.id, previous_name.id)
        self.assertEqual(REDACTED_f73137d930c3.user_profile, "REDACTED_2c7b6821719d")

    def test_ambiguous_REDACTED_e899cf89ab27_is_not_arbitrarily_resolved(self):
        self.initializer.initialize()
        matches = self.people.find_people_by_name("REDACTED_342ad0893cb2")
        self.assertEqual({person.name for person in matches}, {"REDACTED_32885d880536", "REDACTED_e3b252570a2f"})
        self.assertIsNone(self.people.find_person_by_name("REDACTED_342ad0893cb2"))

    def test_all_declared_animals_are_created_and_resolvable_by_alias(self):
        self.initializer.initialize()
        self.assertIsNotNone(self.people.find_animal_by_name("REDACTED_73007cb40c65"))
        self.assertIsNotNone(self.people.find_animal_by_name("REDACTED_0f38c2ded26f"))
        self.assertIsNone(self.people.find_animal_by_name("Funció"))
        self.assertIsNotNone(self.people.find_animal_by_name("REDACTED_52d7d8604bf7"))
        self.assertIsNotNone(self.people.find_animal_by_name("REDACTED_06768d0d9b38"))

    def test_delicate_multiple_relationships_survive_initialization(self):
        self.initializer.initialize()
        REDACTED_f73137d930c3 = self.people.find_person_by_name("REDACTED_46087f8d7037")
        REDACTED_1029b731cc39 = self.people.find_person_by_name("REDACTED_516d7f9914e7")
        REDACTED_065352dc563a = self.people.find_person_by_name("REDACTED_a57a306cce03")

        REDACTED_1029b731cc39_types = {
            relationship.relationship_type
            for relationship in self.engine.get_outgoing_relationships(REDACTED_1029b731cc39.id, "person")
            if relationship.target_entity_id == REDACTED_f73137d930c3.id
        }
        REDACTED_065352dc563a_types = {
            relationship.relationship_type
            for relationship in self.engine.get_outgoing_relationships(REDACTED_065352dc563a.id, "person")
            if relationship.target_entity_id == REDACTED_f73137d930c3.id
        }
        self.assertTrue({"brother", "cousin"}.issubset(REDACTED_1029b731cc39_types))
        self.assertTrue({"sister", "cousin"}.issubset(REDACTED_065352dc563a_types))

    def test_pet_relationships_generate_inverse_relations(self):
        self.initializer.initialize()
        REDACTED_f73137d930c3 = self.people.find_person_by_name("REDACTED_46087f8d7037")
        gato = self.people.find_animal_by_name("REDACTED_a786bf1bf655")
        direct = [
            relationship
            for relationship in self.engine.get_outgoing_relationships(REDACTED_f73137d930c3.id, "person")
            if relationship.target_entity_id == gato.id
        ]
        inverse = [
            relationship
            for relationship in self.engine.get_outgoing_relationships(gato.id, "animal")
            if relationship.target_entity_id == REDACTED_f73137d930c3.id
        ]
        self.assertIn("pet_owner", {relationship.relationship_type for relationship in direct})
        self.assertIn("pet_of", {relationship.relationship_type for relationship in inverse})

    def test_initializer_removes_obsolete_animal_aliases(self):
        self.people.create_animal(
            "REDACTED_c0240dd983fa",
            "cat",
            aliases=["REDACTED_0f38c2ded26f", "Funció"],
            sex="male",
            grammatical_gender="masculine",
        )

        self.initializer.initialize()

        REDACTED_24d96a103e85 = self.people.find_animal_by_name(
            "REDACTED_c0240dd983fa"
        )

        self.assertIsNotNone(REDACTED_24d96a103e85)
        self.assertEqual(REDACTED_24d96a103e85.aliases, ["REDACTED_0f38c2ded26f"])
        self.assertIsNone(
            self.people.find_animal_by_name("Funció")
        )


if __name__ == "__main__":
    unittest.main()

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

    def test_liam_aliases_resolve_to_one_record(self):
        self.initializer.initialize()
        liam = self.people.find_person_by_name("Liam Vicente Martínez")
        previous_name = self.people.find_person_by_name("Nerea Vicente Martínez")
        self.assertIsNotNone(liam)
        self.assertIsNotNone(previous_name)
        self.assertEqual(liam.id, previous_name.id)
        self.assertEqual(liam.user_profile, "Liam")

    def test_ambiguous_pepi_is_not_arbitrarily_resolved(self):
        self.initializer.initialize()
        matches = self.people.find_people_by_name("Pepi")
        self.assertEqual({person.name for person in matches}, {"Pepi Vicente Navarro", "Pepi Carreres López"})
        self.assertIsNone(self.people.find_person_by_name("Pepi"))

    def test_all_declared_animals_are_created_and_resolvable_by_alias(self):
        self.initializer.initialize()
        self.assertIsNotNone(self.people.find_animal_by_name("Don Gato"))
        self.assertIsNotNone(self.people.find_animal_by_name("Funcio"))
        self.assertIsNone(self.people.find_animal_by_name("Funció"))
        self.assertIsNotNone(self.people.find_animal_by_name("Lucas"))
        self.assertIsNotNone(self.people.find_animal_by_name("Estrella"))

    def test_delicate_multiple_relationships_survive_initialization(self):
        self.initializer.initialize()
        liam = self.people.find_person_by_name("Liam Vicente Martínez")
        txipi = self.people.find_person_by_name("José Manuel Martínez Pérez")
        alba = self.people.find_person_by_name("Alba Martínez Pérez")

        txipi_types = {
            relationship.relationship_type
            for relationship in self.engine.get_outgoing_relationships(txipi.id, "person")
            if relationship.target_entity_id == liam.id
        }
        alba_types = {
            relationship.relationship_type
            for relationship in self.engine.get_outgoing_relationships(alba.id, "person")
            if relationship.target_entity_id == liam.id
        }
        self.assertTrue({"brother", "cousin"}.issubset(txipi_types))
        self.assertTrue({"sister", "cousin"}.issubset(alba_types))

    def test_pet_relationships_generate_inverse_relations(self):
        self.initializer.initialize()
        liam = self.people.find_person_by_name("Liam Vicente Martínez")
        gato = self.people.find_animal_by_name("Don Gato Mishi Van Gogh")
        direct = [
            relationship
            for relationship in self.engine.get_outgoing_relationships(liam.id, "person")
            if relationship.target_entity_id == gato.id
        ]
        inverse = [
            relationship
            for relationship in self.engine.get_outgoing_relationships(gato.id, "animal")
            if relationship.target_entity_id == liam.id
        ]
        self.assertIn("pet_owner", {relationship.relationship_type for relationship in direct})
        self.assertIn("pet_of", {relationship.relationship_type for relationship in inverse})

    def test_initializer_removes_obsolete_animal_aliases(self):
        self.people.create_animal(
            "Funcionario",
            "cat",
            aliases=["Funcio", "Funció"],
            sex="male",
            grammatical_gender="masculine",
        )

        self.initializer.initialize()

        funcionario = self.people.find_animal_by_name(
            "Funcionario"
        )

        self.assertIsNotNone(funcionario)
        self.assertEqual(funcionario.aliases, ["Funcio"])
        self.assertIsNone(
            self.people.find_animal_by_name("Funció")
        )

    def test_short_jose_vicente_resolves_only_to_grandfather(self):
        self.initializer.initialize()
        father = self.people.find_person_by_name("José Vicente Navarro")
        grandfather = self.people.find_person_by_name("José Vicente")

        self.assertIsNotNone(father)
        self.assertIsNotNone(grandfather)
        self.assertNotEqual(father.id, grandfather.id)
        self.assertNotIn("José Vicente", father.aliases)
        self.assertEqual(grandfather.name, "José Vicente")

    def test_obsolete_corrected_people_are_removed(self):
        self.people.create_person(name="Evaristo Maestre Esteve")
        self.people.create_person(name="Fermina Pérez")

        self.initializer.initialize()

        self.assertIsNone(self.people.find_person_by_name("Evaristo Maestre Esteve"))
        self.assertIsNone(self.people.find_person_by_name("Fermina Pérez"))
        self.assertIsNotNone(self.people.find_person_by_name("Evaristo Maestre Domenech"))
        self.assertIsNotNone(self.people.find_person_by_name("Fina Pérez"))



if __name__ == "__main__":
    unittest.main()

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
        self.Alex = self.people.create_user_person("Alex", "Alex", grammatical_gender="masculine")
        self.alias_ejemplo_44_01 = self.people.create_user_person("Vega", "Vega", grammatical_gender="feminine")
        self.alias_ejemplo_05_01 = self.people.create_person("Marco", grammatical_gender="masculine")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_direct_and_inverse_relationship(self):
        direct, inverse = self.engine.create_relationship_by_name(
            source="Marco", relationship_type=BROTHER, target="Vega", create_inverse=True
        )
        self.assertIsNotNone(direct)
        self.assertIsNotNone(inverse)
        self.assertEqual(inverse.relationship_type, SISTER)

    def test_allows_multiple_distinct_relationships_between_same_people(self):
        self.engine.create_relationship_by_name(source="Marco", relationship_type=BROTHER, target="Alex")
        self.engine.create_relationship_by_name(source="Marco", relationship_type=COUSIN, target="Alex")
        types = {
            rel.relationship_type
            for rel in self.engine.get_outgoing_relationships(self.alias_ejemplo_05_01.id, "person")
            if rel.target_entity_id == self.Alex.id
        }
        self.assertIn(BROTHER, types)
        self.assertIn(COUSIN, types)

    def test_exact_duplicate_is_idempotent(self):
        first = self.engine.create_relationship_by_name(source="Alex", relationship_type=PARTNER, target="Vega")
        count = self.engine.get_relationship_count()
        second = self.engine.create_relationship_by_name(source="Alex", relationship_type=PARTNER, target="Vega")
        self.assertEqual(self.engine.get_relationship_count(), count)
        self.assertEqual(first[0].id, second[0].id)

    def test_infers_in_law_relationships_from_partner_and_family(self):
        mother = self.people.create_person(
            "María", grammatical_gender="feminine"
        )
        brother = self.people.create_person(
            "Diego", grammatical_gender="masculine"
        )
        self.engine.create_relationship_by_name(
            source="Alex",
            relationship_type=PARTNER,
            target="Vega",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="Alex",
            relationship_type=SON,
            target="María",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="Diego",
            relationship_type=BROTHER,
            target="Alex",
            create_inverse=True,
        )

        self.assertEqual(
            self.engine.infer_relationship_label(
                self.alias_ejemplo_44_01.id, "person", mother.id, "person"
            ),
            "nuera",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                mother.id, "person", self.alias_ejemplo_44_01.id, "person"
            ),
            "suegra",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                self.alias_ejemplo_44_01.id, "person", brother.id, "person"
            ),
            "cuñada",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                brother.id, "person", self.alias_ejemplo_44_01.id, "person"
            ),
            "cuñado",
        )

    def test_infers_grandparent_aunt_and_niece_relationships(self):
        grandmother = self.people.create_person(
            "Abuela", grammatical_gender="feminine"
        )
        aunt = self.people.create_person(
            "Aroa", grammatical_gender="feminine"
        )
        child = self.people.create_person(
            "Vega", grammatical_gender="feminine"
        )
        self.engine.create_relationship_by_name(
            source="Vega",
            relationship_type=DAUGHTER,
            target="Alex",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="Alex",
            relationship_type=SON,
            target="Abuela",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="Aroa",
            relationship_type=SISTER,
            target="Alex",
            create_inverse=True,
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                grandmother.id, "person", self.alias_ejemplo_44_01.id, "person"
            ),
            "abuela",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                aunt.id, "person", self.alias_ejemplo_44_01.id, "person"
            ),
            "tía",
        )
        self.assertEqual(
            self.engine.infer_relationship_label(
                self.alias_ejemplo_44_01.id, "person", aunt.id, "person"
            ),
            "sobrina",
        )

    def test_shortest_path_and_description_support_animals(self):
        pet = self.people.create_animal(
            "Nube",
            species="cat",
            sex="male",
            grammatical_gender="masculine",
        )
        self.engine.create_relationship_by_name(
            source="Alex",
            relationship_type="pet_owner",
            target="Nube",
            create_inverse=True,
        )
        self.engine.create_relationship_by_name(
            source="Alex",
            relationship_type=PARTNER,
            target="Vega",
            create_inverse=True,
        )

        path = self.engine.find_shortest_relationship_path(
            self.alias_ejemplo_44_01.id,
            "person",
            pet.id,
            "animal",
        )
        self.assertTrue(path)
        description = self.engine.describe_relationship_between_entities(
            self.alias_ejemplo_44_01.id,
            "person",
            pet.id,
            "animal",
        )
        self.assertIn("Vega", description)
        self.assertIn("Nube", description)
        self.assertNotIn("None", description)

    def test_missing_entity_raises_clear_error(self):
        with self.assertRaises(ValueError):
            self.engine.create_relationship_by_name(source="Desconocido", relationship_type=PARTNER, target="Vega")


if __name__ == "__main__":
    unittest.main()

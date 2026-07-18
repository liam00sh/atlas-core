"""Validación estática del árbol familiar declarativo."""

import unittest

from identity.family_data import FAMILY_ANIMALS, FAMILY_PEOPLE, FAMILY_RELATIONSHIPS
from identity.relationship import RELATIONSHIP_TYPES


class FamilyDataTests(unittest.TestCase):
    def setUp(self):
        self.people_names = {item["name"] for item in FAMILY_PEOPLE}
        self.animal_names = {item["name"] for item in FAMILY_ANIMALS}
        self.all_names = self.people_names | self.animal_names
        self.triples = {
            (item["source"], item["relationship_type"], item["target"])
            for item in FAMILY_RELATIONSHIPS
        }

    def test_expected_dataset_size(self):
        self.assertEqual(len(FAMILY_PEOPLE), 44)
        self.assertEqual(len(FAMILY_ANIMALS), 4)
        self.assertEqual(len(FAMILY_RELATIONSHIPS), 127)

    def test_primary_names_are_unique_and_references_exist(self):
        names = [item["name"] for item in FAMILY_PEOPLE + FAMILY_ANIMALS]
        self.assertEqual(len(names), len({name.casefold() for name in names}))
        missing = [
            (rel["source"], rel["target"])
            for rel in FAMILY_RELATIONSHIPS
            if rel["source"] not in self.all_names or rel["target"] not in self.all_names
        ]
        self.assertEqual(missing, [])

    def test_all_relationship_types_and_entity_types_are_valid(self):
        for relationship in FAMILY_RELATIONSHIPS:
            with self.subTest(relationship=relationship):
                self.assertIn(relationship["relationship_type"], RELATIONSHIP_TYPES)
                source_type = relationship.get("source_type", "person")
                target_type = relationship.get("target_type", "person")
                self.assertIn(source_type, {"person", "animal"})
                self.assertIn(target_type, {"person", "animal"})
                if source_type == "person":
                    self.assertIn(relationship["source"], self.people_names)
                else:
                    self.assertIn(relationship["source"], self.animal_names)
                if target_type == "person":
                    self.assertIn(relationship["target"], self.people_names)
                else:
                    self.assertIn(relationship["target"], self.animal_names)

    def test_no_exact_duplicate_relationships(self):
        keys = [
            (
                rel["source"], rel.get("source_type", "person"),
                rel["relationship_type"], rel["target"],
                rel.get("target_type", "person"),
            )
            for rel in FAMILY_RELATIONSHIPS
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_delicate_family_relationships_are_explicit(self):
        expected = {
            ("REDACTED_46087f8d7037", "partner", "REDACTED_8762331d93e2"),
            ("REDACTED_516d7f9914e7", "brother", "REDACTED_46087f8d7037"),
            ("REDACTED_516d7f9914e7", "cousin", "REDACTED_46087f8d7037"),
            ("REDACTED_a57a306cce03", "sister", "REDACTED_46087f8d7037"),
            ("REDACTED_a57a306cce03", "cousin", "REDACTED_46087f8d7037"),
            ("REDACTED_ba2c2b03ba9a", "mother", "REDACTED_516d7f9914e7"),
        }
        self.assertTrue(expected.issubset(self.triples))

    def test_parental_and_grandparent_branches_are_connected(self):
        expected = {
            ("REDACTED_ba2c2b03ba9a", "mother", "REDACTED_46087f8d7037"),
            ("REDACTED_0a0e53340b75", "father", "REDACTED_46087f8d7037"),
            ("REDACTED_fd70e667da43", "grandfather", "REDACTED_46087f8d7037"),
            ("REDACTED_7e476572dd1d", "grandmother", "REDACTED_46087f8d7037"),
            ("REDACTED_8085794bfe8c", "grandmother", "REDACTED_46087f8d7037"),
            ("REDACTED_4017eca8b313", "grandfather", "REDACTED_46087f8d7037"),
            ("REDACTED_1d30a2a8cb4e", "grandmother", "REDACTED_46087f8d7037"),
            ("REDACTED_020164a43a4e", "father", "REDACTED_8762331d93e2"),
            ("REDACTED_e3b252570a2f", "mother", "REDACTED_8762331d93e2"),
            ("REDACTED_a8e7422bbc91", "grandfather", "REDACTED_8762331d93e2"),
            ("REDACTED_a593facd4dfb", "grandmother", "REDACTED_8762331d93e2"),
        }
        self.assertTrue(expected.issubset(self.triples))

    def test_animals_have_expected_owners_and_caregivers(self):
        expected = {
            ("REDACTED_46087f8d7037", "pet_owner", "REDACTED_a786bf1bf655"),
            ("REDACTED_65dc3df1f2c0", "pet_owner", "REDACTED_c0240dd983fa"),
            ("REDACTED_29f4c4bcf01a", "pet_owner", "REDACTED_52d7d8604bf7"),
            ("REDACTED_a593facd4dfb", "pet_owner", "REDACTED_06768d0d9b38"),
            ("REDACTED_a8e7422bbc91", "pet_owner", "REDACTED_06768d0d9b38"),
            ("REDACTED_46087f8d7037", "cares_for", "REDACTED_06768d0d9b38"),
            ("REDACTED_8762331d93e2", "cares_for", "REDACTED_06768d0d9b38"),
        }
        self.assertTrue(expected.issubset(self.triples))
        for relationship in FAMILY_RELATIONSHIPS:
            if relationship["target"] in self.animal_names:
                self.assertEqual(relationship.get("target_type"), "animal")

    def test_REDACTED_f73137d930c3_previous_name_is_alias_not_primary_person(self):
        REDACTED_f73137d930c3 = next(item for item in FAMILY_PEOPLE if item["name"] == "REDACTED_46087f8d7037")
        self.assertIn("REDACTED_e97345c31916", REDACTED_f73137d930c3["aliases"])
        self.assertNotIn("REDACTED_e97345c31916", self.people_names)

    def test_ambiguous_REDACTED_e899cf89ab27_alias_is_intentional(self):
        REDACTED_e899cf89ab27_alias_owners = {
            item["name"]
            for item in FAMILY_PEOPLE
            if "REDACTED_342ad0893cb2" in item.get("aliases", [])
        }
        self.assertEqual(REDACTED_e899cf89ab27_alias_owners, {"REDACTED_32885d880536", "REDACTED_e3b252570a2f"})

    def test_corrected_names_and_family_boundaries(self):
        people_by_name = {item["name"]: item for item in FAMILY_PEOPLE}
        animals_by_name = {item["name"]: item for item in FAMILY_ANIMALS}

        self.assertIn("REDACTED_7e476572dd1d", people_by_name)
        self.assertIn("REDACTED_678ace636439", people_by_name["REDACTED_7e476572dd1d"]["aliases"])

        self.assertIn("REDACTED_af0a5ccf569c", people_by_name)
        self.assertIn("REDACTED_3ae65da8646e", people_by_name)
        self.assertIn("REDACTED_91f6198b34bc", people_by_name)

        self.assertEqual(
            animals_by_name["REDACTED_c0240dd983fa"]["aliases"],
            ["REDACTED_0f38c2ded26f"],
        )

        direct_REDACTED_6915771be1c5_REDACTED_7b9528898599 = [
            relationship
            for relationship in FAMILY_RELATIONSHIPS
            if {
                relationship["source"],
                relationship["target"],
            } == {
                "REDACTED_ba2c2b03ba9a",
                "REDACTED_8762331d93e2",
            }
        ]

        self.assertEqual(direct_REDACTED_6915771be1c5_REDACTED_7b9528898599, [])

        self.assertIn(
            (
                "REDACTED_46087f8d7037",
                "partner",
                "REDACTED_8762331d93e2",
            ),
            self.triples,
        )

    def test_canonical_names_do_not_collide_with_other_people_aliases(self):
        alias_to_people = {}
        for person in FAMILY_PEOPLE:
            for reference in [person["name"], *person.get("aliases", [])]:
                key = reference.casefold().strip()
                alias_to_people.setdefault(key, set()).add(person["name"])

        allowed_ambiguous = {"REDACTED_e899cf89ab27", "REDACTED_321cb76b7d6e"}
        collisions = {
            alias: names
            for alias, names in alias_to_people.items()
            if len(names) > 1 and alias not in allowed_ambiguous
        }
        self.assertEqual(collisions, {})



if __name__ == "__main__":
    unittest.main()

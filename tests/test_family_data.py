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
        self.assertEqual(len(FAMILY_RELATIONSHIPS), 124)

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
            ("Liam Vicente Martínez", "partner", "Saray Izquierdo Carreres"),
            ("José Manuel Martínez Pérez", "brother", "Liam Vicente Martínez"),
            ("José Manuel Martínez Pérez", "cousin", "Liam Vicente Martínez"),
            ("Alba Martínez Pérez", "sister", "Liam Vicente Martínez"),
            ("Alba Martínez Pérez", "cousin", "Liam Vicente Martínez"),
            ("María José Martínez Sanz", "mother", "José Manuel Martínez Pérez"),
        }
        self.assertTrue(expected.issubset(self.triples))

    def test_parental_and_grandparent_branches_are_connected(self):
        expected = {
            ("María José Martínez Sanz", "mother", "Liam Vicente Martínez"),
            ("José Vicente Navarro", "father", "Liam Vicente Martínez"),
            ("José Vicente", "grandfather", "Liam Vicente Martínez"),
            ("Fermina Navarro", "grandmother", "Liam Vicente Martínez"),
            ("Lola Payá", "grandmother", "Liam Vicente Martínez"),
            ("Pepe Martínez", "grandfather", "Liam Vicente Martínez"),
            ("Consuelo Sanz Esteve", "grandmother", "Liam Vicente Martínez"),
            ("José Miguel Izquierdo Catalán", "father", "Saray Izquierdo Carreres"),
            ("Pepi Carreres López", "mother", "Saray Izquierdo Carreres"),
            ("Antonio Carreres Hernández", "grandfather", "Saray Izquierdo Carreres"),
            ("Manuela López Serrano", "grandmother", "Saray Izquierdo Carreres"),
        }
        self.assertTrue(expected.issubset(self.triples))

    def test_animals_have_expected_owners_and_caregivers(self):
        expected = {
            ("Liam Vicente Martínez", "pet_owner", "Don Gato Mishi Van Gogh"),
            ("Lidia Vicente Martínez", "pet_owner", "Funcionario"),
            ("Roberto Amarillo Navarro", "pet_owner", "Lucas"),
            ("Manuela López Serrano", "pet_owner", "Estrella"),
            ("Antonio Carreres Hernández", "cares_for", "Estrella"),
            ("Liam Vicente Martínez", "cares_for", "Estrella"),
            ("Saray Izquierdo Carreres", "cares_for", "Estrella"),
        }
        self.assertTrue(expected.issubset(self.triples))
        for relationship in FAMILY_RELATIONSHIPS:
            if relationship["target"] in self.animal_names:
                self.assertEqual(relationship.get("target_type"), "animal")

    def test_liam_previous_name_is_alias_not_primary_person(self):
        liam = next(item for item in FAMILY_PEOPLE if item["name"] == "Liam Vicente Martínez")
        self.assertIn("Nerea Vicente Martínez", liam["aliases"])
        self.assertNotIn("Nerea Vicente Martínez", self.people_names)

    def test_ambiguous_pepi_alias_is_intentional(self):
        pepi_alias_owners = {
            item["name"]
            for item in FAMILY_PEOPLE
            if "Pepi" in item.get("aliases", [])
        }
        self.assertEqual(pepi_alias_owners, {"Pepi Vicente Navarro", "Pepi Carreres López"})

    def test_corrected_names_and_family_boundaries(self):
        people_by_name = {item["name"]: item for item in FAMILY_PEOPLE}
        animals_by_name = {item["name"]: item for item in FAMILY_ANIMALS}

        self.assertIn("Fermina Navarro", people_by_name)
        self.assertIn("Fermina", people_by_name["Fermina Navarro"]["aliases"])

        self.assertIn("Jorge Carreres López", people_by_name)
        self.assertIn("Georgel Melinte", people_by_name)
        self.assertIn("Noa Melinte Carreres", people_by_name)

        self.assertEqual(
            animals_by_name["Funcionario"]["aliases"],
            ["Funcio"],
        )

        direct_mary_saray = [
            relationship
            for relationship in FAMILY_RELATIONSHIPS
            if {
                relationship["source"],
                relationship["target"],
            } == {
                "María José Martínez Sanz",
                "Saray Izquierdo Carreres",
            }
        ]

        self.assertEqual(direct_mary_saray, [])

        self.assertIn(
            (
                "Liam Vicente Martínez",
                "partner",
                "Saray Izquierdo Carreres",
            ),
            self.triples,
        )


if __name__ == "__main__":
    unittest.main()

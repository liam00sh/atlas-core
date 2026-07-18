"""Regresiones de datos y relaciones corregidas durante la Fase 3.1.

Estas pruebas trabajan contra los JSON reales del proyecto. Su objetivo es
impedir que una regeneración de datos o un cambio futuro vuelva a introducir
nombres, parentescos o descripciones que ya fueron corregidos.
"""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "identity" / "data"


class Phase31DataIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.people = json.loads(
            (DATA_DIR / "people.json").read_text(encoding="utf-8")
        )
        cls.animals = json.loads(
            (DATA_DIR / "animals.json").read_text(encoding="utf-8")
        )
        cls.relationships = json.loads(
            (DATA_DIR / "relationships.json").read_text(encoding="utf-8")
        )
        cls.people_by_name = {person["name"]: person for person in cls.people}
        cls.people_by_id = {person["id"]: person for person in cls.people}
        cls.animals_by_id = {animal["id"]: animal for animal in cls.animals}

    def _person_id(self, name: str) -> str:
        return self.people_by_name[name]["id"]

    def _relations_between(self, first_name: str, second_name: str) -> list[dict]:
        first_id = self._person_id(first_name)
        second_id = self._person_id(second_name)
        return [
            relation
            for relation in self.relationships
            if {
                relation["source_entity_id"],
                relation["target_entity_id"],
            }
            == {first_id, second_id}
        ]

    def test_entity_and_relationship_ids_are_unique(self):
        entity_ids = [person["id"] for person in self.people]
        entity_ids.extend(animal["id"] for animal in self.animals)
        relationship_ids = [relation["id"] for relation in self.relationships]

        self.assertEqual(len(entity_ids), len(set(entity_ids)))
        self.assertEqual(len(relationship_ids), len(set(relationship_ids)))

    def test_every_relationship_endpoint_exists(self):
        valid_ids = set(self.people_by_id) | set(self.animals_by_id)
        for relation in self.relationships:
            with self.subTest(relationship_id=relation["id"]):
                self.assertIn(relation["source_entity_id"], valid_ids)
                self.assertIn(relation["target_entity_id"], valid_ids)
                self.assertNotEqual(
                    relation["source_entity_id"],
                    relation["target_entity_id"],
                )

    def test_all_current_relationships_are_confirmed_and_high_confidence(self):
        for relation in self.relationships:
            with self.subTest(relationship_id=relation["id"]):
                self.assertIs(relation["confirmed"], True)
                self.assertEqual(relation["confidence"], 1.0)

    def test_liam_name_is_exact_and_not_duplicated(self):
        liam = self.people_by_name["Liam Vicente Martínez"]
        self.assertIn("Liam", liam["aliases"])
        self.assertNotIn("Liam Vicente Martínez Martínez", self.people_by_name)
        self.assertNotIn("Liam Navarro", liam["aliases"])

    def test_liam_sensitive_information_is_not_for_spontaneous_use(self):
        summary = self.people_by_name["Liam Vicente Martínez"]["summary"].casefold()
        self.assertIn("personal y sensible", summary)
        self.assertIn("no debe mencionarse espontáneamente", summary)
        self.assertIn("nombre anterior", summary)

    def test_saray_education_is_finished_and_not_university(self):
        summary = self.people_by_name["Saray Izquierdo Carreres"]["summary"].casefold()
        self.assertIn("grado superior", summary)
        self.assertIn("instituto", summary)
        self.assertIn("ya terminó", summary)
        self.assertIn("no estudia en la universidad", summary)
        self.assertIn("no debe afirmarse que siga estudiando", summary)

    def test_rauls_full_and_preferred_names_are_correct(self):
        raul = self.people_by_name["Raúl Isidro Vicente Martínez"]
        self.assertIn("Raúl", raul["aliases"])
        self.assertIn("nombre habitual es Raúl", raul["summary"])

    def test_pepi_records_are_distinct_and_have_correct_scope(self):
        pepi_vicente = self.people_by_name["Pepi Vicente Navarro"]
        pepi_carreres = self.people_by_name["Pepi Carreres López"]

        self.assertNotEqual(pepi_vicente["id"], pepi_carreres["id"])
        self.assertIn("Pepa", pepi_vicente["aliases"])
        self.assertIn("Pepi Carreras", pepi_carreres["aliases"])
        self.assertIn("madre de saray", pepi_carreres["summary"].casefold())
        self.assertIn("tía paterna de liam", pepi_vicente["summary"].casefold())

        carreres_saray = self._relations_between(
            "Pepi Carreres López",
            "Saray Izquierdo Carreres",
        )
        vicente_liam = self._relations_between(
            "Pepi Vicente Navarro",
            "Liam Vicente Martínez",
        )
        vicente_saray = self._relations_between(
            "Pepi Vicente Navarro",
            "Saray Izquierdo Carreres",
        )

        self.assertIn("mother", {relation["relationship_type"] for relation in carreres_saray})
        self.assertIn("aunt", {relation["relationship_type"] for relation in vicente_liam})
        self.assertEqual(vicente_saray, [])

    def test_ruben_and_manoli_are_not_liams_cousins(self):
        ruben_summary = self.people_by_name["Rubén Izquierdo Carreres"]["summary"].casefold()
        manoli_summary = self.people_by_name["Manoli Carreres López"]["summary"].casefold()
        self.assertIn("hermano de saray", ruben_summary)
        self.assertIn("tía materna de saray", manoli_summary)

        for name in ("Rubén Izquierdo Carreres", "Manoli Carreres López"):
            relations = self._relations_between(name, "Liam Vicente Martínez")
            self.assertNotIn(
                "cousin",
                {relation["relationship_type"] for relation in relations},
            )

    def test_txipi_internal_data_is_preserved_but_public_summary_is_cousin_only(self):
        relations = self._relations_between(
            "José Manuel Martínez Pérez",
            "Liam Vicente Martínez",
        )
        types = Counter(relation["relationship_type"] for relation in relations)
        notes = " ".join(relation.get("notes", "") for relation in relations).casefold()

        self.assertGreaterEqual(types["cousin"], 2)
        self.assertGreaterEqual(types["brother"], 2)
        self.assertIn("primos", notes)
        self.assertIn("no exponer", notes)

        summary = self.people_by_name["José Manuel Martínez Pérez"]["summary"].casefold()
        self.assertIn("primo de liam", summary)
        self.assertNotIn("hermano de liam", summary)
        self.assertNotIn("adoptivo", summary)
        self.assertNotIn("afectivo", summary)

    def test_alba_internal_data_is_preserved_but_public_summary_is_cousin_only(self):
        relations = self._relations_between(
            "Alba Martínez Pérez",
            "Liam Vicente Martínez",
        )
        types = {relation["relationship_type"] for relation in relations}
        notes = " ".join(relation.get("notes", "") for relation in relations).casefold()

        self.assertIn("cousin", types)
        self.assertTrue({"sister", "brother"} & types)
        self.assertIn("primos", notes)
        self.assertIn("no exponer", notes)

        summary = self.people_by_name["Alba Martínez Pérez"]["summary"].casefold()
        self.assertIn("prima de liam", summary)
        self.assertNotIn("hermana afectiva", summary)
        self.assertNotIn("hermana legal", summary)

    def test_alba_adoption_and_adoptive_siblings_are_explicit(self):
        alba = "Alba Martínez Pérez"
        chelo = "Consuelo Martínez Sanz"
        maria_teresa = "María Teresa Maestre Martínez"
        jose_evaristo = "José Evaristo Maestre Martínez"

        adoption_notes = " ".join(
            relation.get("notes", "")
            for relation in self._relations_between(alba, chelo)
        ).casefold()
        self.assertIn("adoptiva legal", adoption_notes)
        self.assertIn("no", adoption_notes)
        self.assertIn("biológica", adoption_notes)

        for sibling in (maria_teresa, jose_evaristo):
            notes = " ".join(
                relation.get("notes", "")
                for relation in self._relations_between(alba, sibling)
            ).casefold()
            self.assertIn("por adopción", notes)
            self.assertIn("no", notes)
            self.assertIn("biológ", notes)

    def test_animals_explicitly_reject_human_projects_and_hobbies(self):
        required_concepts = (
            ("no tiene proyectos",),
            ("trabajo", "empleo"),
            ("estudios",),
            ("aficiones", "hobbies"),
            ("objetivos", "aspiraciones"),
            ("ilusiones humanas",),
        )
        for animal in self.animals:
            summary = animal["summary"].casefold()
            with self.subTest(animal=animal["name"]):
                for alternatives in required_concepts:
                    self.assertTrue(
                        any(fragment in summary for fragment in alternatives),
                        msg=(
                            f"{animal['name']} no declara el concepto requerido: "
                            f"{' / '.join(alternatives)}"
                        ),
                    )


if __name__ == "__main__":
    unittest.main()

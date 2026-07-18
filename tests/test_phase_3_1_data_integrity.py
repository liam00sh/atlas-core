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

    def test_REDACTED_f73137d930c3_name_is_exact_and_not_duplicated(self):
        REDACTED_f73137d930c3 = self.people_by_name["REDACTED_46087f8d7037"]
        self.assertIn("REDACTED_2c7b6821719d", REDACTED_f73137d930c3["aliases"])
        self.assertNotIn("REDACTED_46087f8d7037 REDACTED_6311e2faf08cez", self.people_by_name)
        self.assertNotIn("REDACTED_2c7b6821719d Navarro", REDACTED_f73137d930c3["aliases"])

    def test_REDACTED_f73137d930c3_sensitive_information_is_not_for_spontaneous_use(self):
        summary = self.people_by_name["REDACTED_46087f8d7037"]["summary"].casefold()
        self.assertIn("personal y sensible", summary)
        self.assertIn("no debe mencionarse espontáneamente", summary)
        self.assertIn("REDACTED_2e31c44a7f7f", summary)

    def test_REDACTED_7b9528898599_education_is_finished_and_not_university(self):
        summary = self.people_by_name["REDACTED_8762331d93e2"]["summary"].casefold()
        self.assertIn("grado superior", summary)
        self.assertIn("instituto", summary)
        self.assertIn("ya terminó", summary)
        self.assertIn("no estudia en la universidad", summary)
        self.assertIn("no debe afirmarse que siga estudiando", summary)

    def test_rauls_full_and_preferred_names_are_correct(self):
        raul = self.people_by_name["REDACTED_d3969f681ba1"]
        self.assertIn("REDACTED_de9c80449aae", raul["aliases"])
        self.assertIn("nombre habitual es REDACTED_de9c80449aae", raul["summary"])

    def test_REDACTED_e899cf89ab27_records_are_distinct_and_have_correct_scope(self):
        REDACTED_e899cf89ab27_vicente = self.people_by_name["REDACTED_32885d880536"]
        REDACTED_e899cf89ab27_carreres = self.people_by_name["REDACTED_e3b252570a2f"]

        self.assertNotEqual(REDACTED_e899cf89ab27_vicente["id"], REDACTED_e899cf89ab27_carreres["id"])
        self.assertIn("REDACTED_2c910d64bd54", REDACTED_e899cf89ab27_vicente["aliases"])
        self.assertIn("REDACTED_6b8e6a2f600a", REDACTED_e899cf89ab27_carreres["aliases"])
        self.assertIn("REDACTED_f5bf7c3405d3", REDACTED_e899cf89ab27_carreres["summary"].casefold())
        self.assertIn("tía paterna de REDACTED_f73137d930c3", REDACTED_e899cf89ab27_vicente["summary"].casefold())

        carreres_REDACTED_7b9528898599 = self._relations_between(
            "REDACTED_e3b252570a2f",
            "REDACTED_8762331d93e2",
        )
        vicente_REDACTED_f73137d930c3 = self._relations_between(
            "REDACTED_32885d880536",
            "REDACTED_46087f8d7037",
        )
        vicente_REDACTED_7b9528898599 = self._relations_between(
            "REDACTED_32885d880536",
            "REDACTED_8762331d93e2",
        )

        self.assertIn("mother", {relation["relationship_type"] for relation in carreres_REDACTED_7b9528898599})
        self.assertIn("aunt", {relation["relationship_type"] for relation in vicente_REDACTED_f73137d930c3})
        self.assertEqual(vicente_REDACTED_7b9528898599, [])

    def test_ruben_and_REDACTED_944f53978b12_are_not_liams_cousins(self):
        ruben_summary = self.people_by_name["REDACTED_7b2ab41fc4b5"]["summary"].casefold()
        REDACTED_944f53978b12_summary = self.people_by_name["REDACTED_7ac2d8ee0281"]["summary"].casefold()
        self.assertIn("hermano de REDACTED_7b9528898599", ruben_summary)
        self.assertIn("tía materna de REDACTED_7b9528898599", REDACTED_944f53978b12_summary)

        for name in ("REDACTED_7b2ab41fc4b5", "REDACTED_7ac2d8ee0281"):
            relations = self._relations_between(name, "REDACTED_46087f8d7037")
            self.assertNotIn(
                "cousin",
                {relation["relationship_type"] for relation in relations},
            )

    def test_REDACTED_1029b731cc39_internal_data_is_preserved_but_public_summary_is_cousin_only(self):
        relations = self._relations_between(
            "REDACTED_516d7f9914e7",
            "REDACTED_46087f8d7037",
        )
        types = Counter(relation["relationship_type"] for relation in relations)
        notes = " ".join(relation.get("notes", "") for relation in relations).casefold()

        self.assertGreaterEqual(types["cousin"], 2)
        self.assertGreaterEqual(types["brother"], 2)
        self.assertIn("primos", notes)
        self.assertIn("no exponer", notes)

        summary = self.people_by_name["REDACTED_516d7f9914e7"]["summary"].casefold()
        self.assertIn("primo de REDACTED_f73137d930c3", summary)
        self.assertNotIn("hermano de REDACTED_f73137d930c3", summary)
        self.assertNotIn("adoptivo", summary)
        self.assertNotIn("afectivo", summary)

    def test_REDACTED_065352dc563a_internal_data_is_preserved_but_public_summary_is_cousin_only(self):
        relations = self._relations_between(
            "REDACTED_a57a306cce03",
            "REDACTED_46087f8d7037",
        )
        types = {relation["relationship_type"] for relation in relations}
        notes = " ".join(relation.get("notes", "") for relation in relations).casefold()

        self.assertIn("cousin", types)
        self.assertTrue({"sister", "brother"} & types)
        self.assertIn("primos", notes)
        self.assertIn("no exponer", notes)

        summary = self.people_by_name["REDACTED_a57a306cce03"]["summary"].casefold()
        self.assertIn("prima de REDACTED_f73137d930c3", summary)
        self.assertNotIn("hermana afectiva", summary)
        self.assertNotIn("hermana legal", summary)

    def test_REDACTED_065352dc563a_adoption_and_adoptive_siblings_are_explicit(self):
        REDACTED_065352dc563a = "REDACTED_a57a306cce03"
        REDACTED_fb0a23056df7 = "REDACTED_6a825c7b6da7"
        maria_teresa = "REDACTED_2130eea91209"
        REDACTED_1ec4ed037766_REDACTED_afbfeca7d9fc = "REDACTED_8f775d9efc06"

        adoption_notes = " ".join(
            relation.get("notes", "")
            for relation in self._relations_between(REDACTED_065352dc563a, REDACTED_fb0a23056df7)
        ).casefold()
        self.assertIn("adoptiva legal", adoption_notes)
        self.assertIn("no", adoption_notes)
        self.assertIn("biológica", adoption_notes)

        for sibling in (maria_teresa, REDACTED_1ec4ed037766_REDACTED_afbfeca7d9fc):
            notes = " ".join(
                relation.get("notes", "")
                for relation in self._relations_between(REDACTED_065352dc563a, sibling)
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

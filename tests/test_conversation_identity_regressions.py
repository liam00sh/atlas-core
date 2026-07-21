"""Regresiones de identidad, relaciones, ambigüedad y limpieza de texto."""

import re
import unittest
from types import SimpleNamespace

from ai.providers.ollama_provider import OllamaProvider
from conversation import personality
from core.atlas_ai import AtlasAIMixin


class _Person:
    def __init__(self, person_id, name, aliases=()):
        self.id = person_id
        self.name = name
        self.aliases = list(aliases)
        self.user_profile = None
        self.summary = ""


class _Animal:
    def __init__(self, animal_id, name, aliases=()):
        self.id = animal_id
        self.name = name
        self.aliases = list(aliases)
        self.summary = ""


class _PeopleManager:
    def __init__(self):
        self.people = [
            _Person("REDACTED_f73137d930c3", "REDACTED_2c7b6821719d", ()),
            _Person("REDACTED_e899cf89ab27_REDACTED_7b9528898599", "REDACTED_e3b252570a2f", ("REDACTED_342ad0893cb2",)),
            _Person("REDACTED_e899cf89ab27_REDACTED_f73137d930c3", "REDACTED_32885d880536", ("REDACTED_342ad0893cb2",)),
            _Person("REDACTED_7b9528898599", "REDACTED_8762331d93e2", ("REDACTED_bc04a68d9192",)),
            _Person("REDACTED_1552db05a755", "REDACTED_65dc3df1f2c0", ("REDACTED_0392c3d1b4d3",)),
            _Person("raul", "REDACTED_d3969f681ba1", ("REDACTED_de9c80449aae",)),
            _Person("REDACTED_6915771be1c5", "REDACTED_ba2c2b03ba9a", ("REDACTED_aebac53c46bb",)),
            _Person("ruben", "REDACTED_7b2ab41fc4b5", ("REDACTED_1b4b1a7f2126",)),
            _Person("REDACTED_944f53978b12", "REDACTED_7ac2d8ee0281", ("REDACTED_abbdcaee9944",)),
            _Person("REDACTED_7467b914d771", "REDACTED_91f6198b34bc", ("REDACTED_d296a64095dd",)),
        ]
        self.animals = [
            _Animal("REDACTED_b4096f88779e", "REDACTED_c0240dd983fa", ("REDACTED_0f38c2ded26f",)),
        ]

    def get_people(self):
        return self.people

    def get_animals(self):
        return self.animals

    def find_person_by_name(self, name):
        normalized = str(name).casefold()
        for person in self.people:
            references = [person.name, *person.aliases]
            if any(normalized == reference.casefold() for reference in references):
                return person
        return None


class _RelationshipEngine:
    def __init__(self):
        self.relationships = [
            SimpleNamespace(
                source_entity_id="REDACTED_7b9528898599",
                source_entity_type="person",
                relationship_type="partner",
                target_entity_id="REDACTED_f73137d930c3",
                target_entity_type="person",
            ),
            SimpleNamespace(
                source_entity_id="REDACTED_e899cf89ab27_REDACTED_7b9528898599",
                source_entity_type="person",
                relationship_type="mother",
                target_entity_id="REDACTED_7b9528898599",
                target_entity_type="person",
            ),
            SimpleNamespace(
                source_entity_id="REDACTED_e899cf89ab27_REDACTED_f73137d930c3",
                source_entity_type="person",
                relationship_type="aunt",
                target_entity_id="REDACTED_f73137d930c3",
                target_entity_type="person",
            ),
        ]

    def describe_relationships_for_entity(self, entity_id, entity_type):
        del entity_type
        return {
            "REDACTED_e899cf89ab27_REDACTED_7b9528898599": ["REDACTED_e3b252570a2f es madre de REDACTED_bc04a68d9192"],
            "REDACTED_e899cf89ab27_REDACTED_f73137d930c3": ["REDACTED_32885d880536 es tía de REDACTED_2c7b6821719d"],
            "REDACTED_7b9528898599": ["REDACTED_8762331d93e2 es pareja de REDACTED_2c7b6821719d"],
        }.get(entity_id, [])

    def get_relationships_for_entity(self, entity_id, entity_type):
        del entity_type
        return [
            relationship
            for relationship in self.relationships
            if entity_id in {
                relationship.source_entity_id,
                relationship.target_entity_id,
            }
        ]

    def describe_relationship(self, relationship):
        descriptions = {
            ("REDACTED_7b9528898599", "partner", "REDACTED_f73137d930c3"):
                "REDACTED_8762331d93e2 es pareja de REDACTED_2c7b6821719d.",
            ("REDACTED_e899cf89ab27_REDACTED_7b9528898599", "mother", "REDACTED_7b9528898599"):
                "REDACTED_e3b252570a2f es madre de REDACTED_bc04a68d9192.",
            ("REDACTED_e899cf89ab27_REDACTED_f73137d930c3", "aunt", "REDACTED_f73137d930c3"):
                "REDACTED_32885d880536 es tía de REDACTED_2c7b6821719d.",
        }
        return descriptions.get(
            (
                relationship.source_entity_id,
                relationship.relationship_type,
                relationship.target_entity_id,
            ),
            "",
        )

    def infer_relationship_label(
        self,
        source_entity_id,
        source_entity_type,
        target_entity_id,
        target_entity_type,
    ):
        del source_entity_type, target_entity_type
        labels = {
            ("REDACTED_7b9528898599", "REDACTED_f73137d930c3"): "pareja",
            ("REDACTED_f73137d930c3", "REDACTED_7b9528898599"): "pareja",
            ("REDACTED_e899cf89ab27_REDACTED_7b9528898599", "REDACTED_7b9528898599"): "madre",
            ("REDACTED_7b9528898599", "REDACTED_e899cf89ab27_REDACTED_7b9528898599"): "hija",
            ("REDACTED_e899cf89ab27_REDACTED_f73137d930c3", "REDACTED_f73137d930c3"): "tía",
            ("REDACTED_f73137d930c3", "REDACTED_e899cf89ab27_REDACTED_f73137d930c3"): "sobrino",
            ("REDACTED_1552db05a755", "REDACTED_f73137d930c3"): "hermana",
            ("raul", "REDACTED_f73137d930c3"): "hermano",
            ("REDACTED_6915771be1c5", "REDACTED_f73137d930c3"): "madre",
            ("ruben", "REDACTED_7b9528898599"): "hermano",
            ("REDACTED_944f53978b12", "REDACTED_7b9528898599"): "tía",
            ("REDACTED_7467b914d771", "REDACTED_944f53978b12"): "hija",
        }
        return labels.get((source_entity_id, target_entity_id))

    def describe_relationship_between_entities(
        self,
        source_entity_id,
        source_entity_type,
        target_entity_id,
        target_entity_type,
    ):
        del source_entity_type, target_entity_type
        names = {
            "REDACTED_f73137d930c3": "REDACTED_2c7b6821719d",
            "REDACTED_7b9528898599": "REDACTED_8762331d93e2",
            "REDACTED_e899cf89ab27_REDACTED_7b9528898599": "REDACTED_e3b252570a2f",
            "REDACTED_e899cf89ab27_REDACTED_f73137d930c3": "REDACTED_32885d880536",
            "REDACTED_b4096f88779e": "REDACTED_c0240dd983fa",
            "REDACTED_1552db05a755": "REDACTED_65dc3df1f2c0",
            "raul": "REDACTED_d3969f681ba1",
            "REDACTED_6915771be1c5": "REDACTED_ba2c2b03ba9a",
            "ruben": "REDACTED_7b2ab41fc4b5",
            "REDACTED_944f53978b12": "REDACTED_7ac2d8ee0281",
            "REDACTED_7467b914d771": "REDACTED_91f6198b34bc",
        }
        label = self.infer_relationship_label(
            source_entity_id,
            "person",
            target_entity_id,
            "person",
        )
        if label:
            return (
                f"{names[source_entity_id]} es {label} de "
                f"{names[target_entity_id]}."
            )
        return (
            f"No hay un parentesco o vínculo verificado entre "
            f"{names.get(source_entity_id, source_entity_id)} y "
            f"{names.get(target_entity_id, target_entity_id)}."
        )

    def find_two_step_connections(self, **kwargs):
        del kwargs
        return []

    def describe_two_step_connection(self, first, second):
        del first, second
        return ""


class _AtlasAI(AtlasAIMixin):
    def __init__(self):
        self.people_manager = _PeopleManager()
        self.relationship_engine = _RelationshipEngine()

    def _get_current_conversation_user(self):
        return "REDACTED_2c7b6821719d"


class ConversationIdentityRegressionTests(unittest.TestCase):
    def test_identity_answer_is_not_repeated_consecutively(self):
        first = personality.identity("Coco", "Proyecto Atlas")
        second = personality.identity("Coco", "Proyecto Atlas")
        self.assertNotEqual(first, second)

    def test_ambiguous_REDACTED_e899cf89ab27_requests_clarification(self):
        atlas = _AtlasAI()
        _, handled = atlas._prepare_entity_clarification("quien es REDACTED_342ad0893cb2")
        self.assertTrue(handled)
        self.assertEqual(
            len(atlas._pending_entity_clarification["candidate_ids"]),
            2,
        )

    def test_ordinal_variants_are_accepted(self):
        variants = {
            "1": 0,
            "la 1": 0,
            "el primero": 0,
            "primera": 0,
            "2": 1,
            "la segunda": 1,
            "segundo": 1,
        }
        for text, expected in variants.items():
            with self.subTest(text=text):
                self.assertEqual(
                    _AtlasAI._parse_ordinal_selection(text),
                    expected,
                )

    def test_follow_up_can_resolve_by_surname_or_relationship(self):
        for answer in ("Carreres", "López", "la madre de REDACTED_bc04a68d9192"):
            atlas = _AtlasAI()
            atlas._prepare_entity_clarification("quien es REDACTED_342ad0893cb2")
            rewritten, handled = atlas._prepare_entity_clarification(answer)
            self.assertFalse(handled)
            self.assertIn("REDACTED_e3b252570a2f", rewritten)

    def test_context_uses_speaker_perspective_and_singular(self):
        atlas = _AtlasAI()
        context = atlas._build_referenced_entities_context("quien es REDACTED_bc04a68d9192")
        self.assertIn("Interlocutor actual: REDACTED_2c7b6821719d", context)
        self.assertIn("usa tercera persona singular", context)
        self.assertIn("nunca uses «mi»", context)
        self.assertIn("REDACTED_8762331d93e2 es pareja de REDACTED_2c7b6821719d", context)

    def test_animal_context_prefers_alias_without_article(self):
        atlas = _AtlasAI()
        context = atlas._build_referenced_entities_context("quien es REDACTED_0f38c2ded26f")
        self.assertIn("Nombre habitual preferido: REDACTED_0f38c2ded26f", context)
        self.assertIn("nunca «el REDACTED_c0240dd983fa»", context)

    def test_response_cleanup_fixes_detected_errors(self):
        prompt = (
            "Animal mencionado: REDACTED_c0240dd983fa.\n"
            "Nombre habitual preferido: REDACTED_0f38c2ded26f.\n"
            "Responde ahora como Coco."
        )
        dirty = (
            "Daxter: Hola REDACTED_2c7b6821719d,\n\n"
            "¡\n"
            "Me refieres al REDACTED_c0240dd983fa. Perhaps viven en REDACTED_039ed2c608a5 con ti.\n"
            "¡"
        )
        cleaned = OllamaProvider._clean_generated_text(dirty, prompt)
        self.assertNotIn("Daxter:", cleaned)
        self.assertNotIn("Me refieres", cleaned)
        self.assertNotIn("REDACTED_c0240dd983fa", cleaned)
        self.assertNotIn("Perhaps", cleaned)
        self.assertNotIn("con ti", cleaned)
        self.assertFalse(cleaned.endswith("¡"))
        self.assertIn("Te refieres a REDACTED_0f38c2ded26f", cleaned)


    def test_current_user_answer_is_varied(self):
        first = personality.current_user_identity("REDACTED_2c7b6821719d", "Daxter")
        second = personality.current_user_identity("REDACTED_2c7b6821719d", "Daxter")
        self.assertNotEqual(first, second)
        self.assertIn("REDACTED_2c7b6821719d", first)
        self.assertIn("REDACTED_2c7b6821719d", second)

    def test_fuzzy_carreras_resolves_to_carreres(self):
        atlas = _AtlasAI()
        atlas._prepare_entity_clarification("quien es REDACTED_342ad0893cb2")
        rewritten, handled = atlas._prepare_entity_clarification("REDACTED_6b8e6a2f600a")
        self.assertFalse(handled)
        self.assertIn("REDACTED_e3b252570a2f", rewritten)

    def test_REDACTED_7b9528898599_can_resolve_her_own_mother(self):
        atlas = _AtlasAI()
        atlas._get_current_conversation_user = lambda: "REDACTED_bc04a68d9192"
        atlas._prepare_entity_clarification("quien es REDACTED_342ad0893cb2")
        rewritten, handled = atlas._prepare_entity_clarification("su madre")
        self.assertFalse(handled)
        self.assertIn("REDACTED_e3b252570a2f", rewritten)

    def test_verified_relationship_query_bypasses_model(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Qué relación tiene REDACTED_bc04a68d9192 con REDACTED_2c7b6821719d?"
        )
        self.assertEqual(
            answer,
            "REDACTED_8762331d93e2 es pareja de REDACTED_2c7b6821719d.",
        )

    def test_REDACTED_1ec4ed037766_miguel_style_multiword_reference_is_not_reduced(self):
        atlas = _AtlasAI()
        atlas.people_manager.people.append(
            _Person(
                "REDACTED_1ec4ed037766_miguel",
                "REDACTED_020164a43a4e",
                ("REDACTED_77c013518681",),
            )
        )
        ambiguous = atlas._find_ambiguous_person_reference(
            "¿Cuándo nació REDACTED_77c013518681?"
        )
        self.assertIsNone(ambiguous)

    def test_similarity_detection_catches_repeated_answers(self):
        self.assertTrue(
            _AtlasAI._responses_are_too_similar(
                "REDACTED_bc04a68d9192 es tu pareja y vive en REDACTED_039ed2c608a5.",
                "REDACTED_bc04a68d9192 es tu pareja y vive en REDACTED_039ed2c608a5.",
            )
        )
        self.assertFalse(
            _AtlasAI._responses_are_too_similar(
                "REDACTED_bc04a68d9192 es tu pareja y vive en REDACTED_039ed2c608a5.",
                "REDACTED_342ad0893cb2 es la madre de REDACTED_bc04a68d9192.",
            )
        )

    def test_cleanup_fixes_pronouns_conjugation_and_stray_question(self):
        prompt = (
            "MENSAJE DEL USUARIO:\nquien es REDACTED_bc04a68d9192\n\n"
            "Persona mencionada: REDACTED_8762331d93e2.\n"
            "Nombre habitual preferido: REDACTED_bc04a68d9192.\n"
        )
        dirty = (
            "REDACTED_bc04a68d9192 es tu pareja. Eres tan suerte teniéndola a su lado. "
            "Puedo mostrar una foto nuestra juntos. ¿Cómo estás hoy? ¡"
        )
        cleaned = OllamaProvider._clean_generated_text(dirty, prompt)
        self.assertIn("tienes mucha suerte de tenerla a tu lado", cleaned.lower())
        self.assertIn("foto vuestra juntos", cleaned.lower())
        self.assertNotIn("¿Cómo estás", cleaned)
        self.assertFalse(cleaned.endswith("¡"))



    def test_relationship_description_exposes_only_cousin_for_REDACTED_1029b731cc39_and_REDACTED_f73137d930c3(self):
        """La salida pública debe ocultar los matices internos de REDACTED_2ff76a67ecfb."""

        from identity.relationship import Relationship
        from identity.relationship_engine import RelationshipEngine

        relationship = Relationship(
            source_entity_id="REDACTED_1029b731cc39",
            source_entity_type="person",
            relationship_type="brother",
            target_entity_id="REDACTED_f73137d930c3",
            target_entity_type="person",
            confirmed=True,
            confidence=1.0,
            notes="Dato interno confirmado.",
        )

        engine = object.__new__(RelationshipEngine)
        engine._resolve_entity_by_id = lambda entity_id, entity_type: SimpleNamespace(
            name=(
                "REDACTED_516d7f9914e7"
                if entity_id == "REDACTED_1029b731cc39"
                else "REDACTED_46087f8d7037"
            )
        )

        description = engine.describe_relationship(relationship)

        self.assertIn("son primos", description.casefold())
        self.assertNotIn("hermano", description.casefold())
        self.assertNotIn("adoptivo", description.casefold())
        self.assertNotIn("afectivo", description.casefold())

    def test_relationship_description_exposes_only_cousin_for_REDACTED_065352dc563a_and_REDACTED_f73137d930c3(self):
        """La salida pública debe ocultar los matices internos de REDACTED_6ced0406ed4d."""

        from identity.relationship import Relationship
        from identity.relationship_engine import RelationshipEngine

        relationship = Relationship(
            source_entity_id="REDACTED_065352dc563a",
            source_entity_type="person",
            relationship_type="sister",
            target_entity_id="REDACTED_f73137d930c3",
            target_entity_type="person",
            confirmed=True,
            confidence=1.0,
            notes="Dato interno confirmado.",
        )

        engine = object.__new__(RelationshipEngine)
        engine._resolve_entity_by_id = lambda entity_id, entity_type: SimpleNamespace(
            name=(
                "REDACTED_a57a306cce03"
                if entity_id == "REDACTED_065352dc563a"
                else "REDACTED_46087f8d7037"
            )
        )

        description = engine.describe_relationship(relationship)

        self.assertIn("son primos", description.casefold())
        self.assertNotIn("hermana", description.casefold())
        self.assertNotIn("legal", description.casefold())
        self.assertNotIn("afectiva", description.casefold())

    def test_inverse_technical_note_is_not_exposed(self):
        """Las notas técnicas de inversión no deben ensuciar el contexto."""

        from identity.relationship import Relationship
        from identity.relationship_engine import RelationshipEngine

        relationship = Relationship(
            source_entity_id="REDACTED_f73137d930c3",
            source_entity_type="person",
            relationship_type="cousin",
            target_entity_id="REDACTED_1029b731cc39",
            target_entity_type="person",
            confirmed=True,
            confidence=1.0,
            notes="Relación inversa generada a partir de abc123.",
        )

        engine = object.__new__(RelationshipEngine)
        engine._resolve_entity_by_id = lambda entity_id, entity_type: (
            SimpleNamespace(name=entity_id)
        )

        description = engine.describe_relationship(relationship)

        self.assertNotIn("inversa generada", description.casefold())


    def test_identity_and_current_user_use_different_topic_keys(self):
        """Las preguntas sobre Atlas y el interlocutor no deben mezclarse."""

        assistant_key = _AtlasAI._response_topic_key(
            "quien eres",
            "REDACTED_2c7b6821719d",
        )
        user_key = _AtlasAI._response_topic_key(
            "quien soy",
            "REDACTED_2c7b6821719d",
        )

        self.assertNotEqual(assistant_key, user_key)
        self.assertTrue(assistant_key.endswith("identidad_asistente"))
        self.assertTrue(user_key.endswith("identidad_interlocutor"))

    def test_cleanup_does_not_mutilate_sentence_after_unpunctuated_greeting(self):
        """«Hola REDACTED_2c7b6821719d es...» debe conservar el sujeto y el contenido."""

        cleaned = OllamaProvider._clean_generated_text(
            "Hola REDACTED_2c7b6821719d es el usuario principal de Atlas.",
            "MENSAJE DEL USUARIO:\nquien es REDACTED_2c7b6821719d\n\n",
        )

        self.assertEqual(
            cleaned,
            "Hola REDACTED_2c7b6821719d es el usuario principal de Atlas.",
        )

    def test_cleanup_replaces_relationship_tautology_with_safe_message(self):
        """Una relación tautológica no debe acabar en una frase incompleta."""

        cleaned = OllamaProvider._clean_generated_text(
            "La madre de REDACTED_bc04a68d9192 es la madre de REDACTED_bc04a68d9192.",
            "MENSAJE DEL USUARIO:\nquien es la madre de REDACTED_bc04a68d9192\n\n",
        )

        self.assertIn(
            "No he identificado correctamente quién es la madre de REDACTED_bc04a68d9192",
            cleaned,
        )
        self.assertNotIn("la madre de REDACTED_bc04a68d9192 es.", cleaned.casefold())




    def test_who_is_my_sister_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quién es mi hermana?"
        )
        self.assertEqual(
            answer,
            "Tu hermana es REDACTED_65dc3df1f2c0.",
        )

    def test_how_is_my_girlfriend_called_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama mi novia?"
        )
        self.assertEqual(
            answer,
            "Tu novia es REDACTED_8762331d93e2.",
        )

    def test_who_is_my_mother_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quién es mi madre?"
        )
        self.assertEqual(
            answer,
            "Tu madre es REDACTED_ba2c2b03ba9a.",
        )

    def test_sarays_brother_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama el hermano de REDACTED_bc04a68d9192?"
        )
        self.assertEqual(
            answer,
            "El hermano de REDACTED_8762331d93e2 "
            "es REDACTED_7b2ab41fc4b5.",
        )

    def test_plural_siblings_are_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quiénes son mis hermanos?"
        )
        self.assertIn("REDACTED_65dc3df1f2c0", answer)
        self.assertIn("REDACTED_d3969f681ba1", answer)



    def test_brother_of_my_girlfriend_uses_two_steps(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quién es el hermano de mi novia?"
        )
        self.assertEqual(
            answer,
            "El hermano de tu novia es "
            "REDACTED_7b2ab41fc4b5.",
        )

    def test_mother_of_my_girlfriend_uses_two_steps(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama la madre de mi novia?"
        )
        self.assertEqual(
            answer,
            "La madre de tu novia es "
            "REDACTED_e3b252570a2f.",
        )

    def test_daughter_of_sarays_aunt_uses_three_steps(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama la hija de la tía de REDACTED_bc04a68d9192?"
        )
        self.assertEqual(
            answer,
            "La hija de la tía de REDACTED_8762331d93e2 es "
            "REDACTED_91f6198b34bc.",
        )



    def test_relationship_pattern_groups_all_aliases(self):
        atlas = _AtlasAI()
        pattern = atlas._relationship_pattern()

        self.assertIsNotNone(
            re.fullmatch(
                rf"(?:mi|mis)\s+{pattern}",
                "mi hermana",
            )
        )
        self.assertIsNotNone(
            re.fullmatch(
                rf"(?:mi|mis)\s+{pattern}",
                "mi madre",
            )
        )
        self.assertIsNotNone(
            re.fullmatch(
                rf"(?:mi|mis)\s+{pattern}",
                "mi novia",
            )
        )

    def test_relationship_articles_include_madre(self):
        atlas = _AtlasAI()

        self.assertEqual(
            atlas._relationship_article(
                "madre",
                plural=False,
            ),
            "La",
        )
        self.assertEqual(
            atlas._relationship_article(
                "hermano",
                plural=False,
            ),
            "El",
        )

    def test_nested_subject_phrase_preserves_article_and_name(self):
        atlas = _AtlasAI()

        self.assertEqual(
            atlas._relationship_subject_phrase(
                "tía de REDACTED_bc04a68d9192"
            ),
            "la tía de REDACTED_8762331d93e2",
        )


if __name__ == "__main__":
    unittest.main()

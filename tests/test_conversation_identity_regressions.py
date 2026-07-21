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
            _Person("liam", "Liam", ()),
            _Person("pepi_saray", "Pepi Carreres López", ("Pepi",)),
            _Person("pepi_liam", "Pepi Vicente Navarro", ("Pepi",)),
            _Person("saray", "Saray Izquierdo Carreres", ("Saray",)),
            _Person("lidia", "Lidia Vicente Martínez", ("Lidia",)),
            _Person("raul", "Raúl Isidro Vicente Martínez", ("Raúl",)),
            _Person("mary", "María José Martínez Sanz", ("Mary",)),
            _Person("ruben", "Rubén Izquierdo Carreres", ("Rubén",)),
            _Person("manoli", "Manoli Carreres López", ("Manoli",)),
            _Person("noa", "Noa Melinte Carreres", ("Noa",)),
        ]
        self.animals = [
            _Animal("funcio", "Funcionario", ("Funcio",)),
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
                source_entity_id="saray",
                source_entity_type="person",
                relationship_type="partner",
                target_entity_id="liam",
                target_entity_type="person",
            ),
            SimpleNamespace(
                source_entity_id="pepi_saray",
                source_entity_type="person",
                relationship_type="mother",
                target_entity_id="saray",
                target_entity_type="person",
            ),
            SimpleNamespace(
                source_entity_id="pepi_liam",
                source_entity_type="person",
                relationship_type="aunt",
                target_entity_id="liam",
                target_entity_type="person",
            ),
        ]

    def describe_relationships_for_entity(self, entity_id, entity_type):
        del entity_type
        return {
            "pepi_saray": ["Pepi Carreres López es madre de Saray"],
            "pepi_liam": ["Pepi Vicente Navarro es tía de Liam"],
            "saray": ["Saray Izquierdo Carreres es pareja de Liam"],
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
            ("saray", "partner", "liam"):
                "Saray Izquierdo Carreres es pareja de Liam.",
            ("pepi_saray", "mother", "saray"):
                "Pepi Carreres López es madre de Saray.",
            ("pepi_liam", "aunt", "liam"):
                "Pepi Vicente Navarro es tía de Liam.",
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
            ("saray", "liam"): "pareja",
            ("liam", "saray"): "pareja",
            ("pepi_saray", "saray"): "madre",
            ("saray", "pepi_saray"): "hija",
            ("pepi_liam", "liam"): "tía",
            ("liam", "pepi_liam"): "sobrino",
            ("lidia", "liam"): "hermana",
            ("raul", "liam"): "hermano",
            ("mary", "liam"): "madre",
            ("ruben", "saray"): "hermano",
            ("manoli", "saray"): "tía",
            ("noa", "manoli"): "hija",
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
            "liam": "Liam",
            "saray": "Saray Izquierdo Carreres",
            "pepi_saray": "Pepi Carreres López",
            "pepi_liam": "Pepi Vicente Navarro",
            "funcio": "Funcionario",
            "lidia": "Lidia Vicente Martínez",
            "raul": "Raúl Isidro Vicente Martínez",
            "mary": "María José Martínez Sanz",
            "ruben": "Rubén Izquierdo Carreres",
            "manoli": "Manoli Carreres López",
            "noa": "Noa Melinte Carreres",
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
        return "Liam"


class ConversationIdentityRegressionTests(unittest.TestCase):
    def test_identity_answer_is_not_repeated_consecutively(self):
        first = personality.identity("Coco", "Proyecto Atlas")
        second = personality.identity("Coco", "Proyecto Atlas")
        self.assertNotEqual(first, second)

    def test_ambiguous_pepi_requests_clarification(self):
        atlas = _AtlasAI()
        _, handled = atlas._prepare_entity_clarification("quien es Pepi")
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
        for answer in ("Carreres", "López", "la madre de Saray"):
            atlas = _AtlasAI()
            atlas._prepare_entity_clarification("quien es Pepi")
            rewritten, handled = atlas._prepare_entity_clarification(answer)
            self.assertFalse(handled)
            self.assertIn("Pepi Carreres López", rewritten)

    def test_context_uses_speaker_perspective_and_singular(self):
        atlas = _AtlasAI()
        context = atlas._build_referenced_entities_context("quien es Saray")
        self.assertIn("Interlocutor actual: Liam", context)
        self.assertIn("usa tercera persona singular", context)
        self.assertIn("nunca uses «mi»", context)
        self.assertIn("Saray Izquierdo Carreres es pareja de Liam", context)

    def test_animal_context_prefers_alias_without_article(self):
        atlas = _AtlasAI()
        context = atlas._build_referenced_entities_context("quien es Funcio")
        self.assertIn("Nombre habitual preferido: Funcio", context)
        self.assertIn("nunca «el Funcionario»", context)

    def test_response_cleanup_fixes_detected_errors(self):
        prompt = (
            "Animal mencionado: Funcionario.\n"
            "Nombre habitual preferido: Funcio.\n"
            "Responde ahora como Coco."
        )
        dirty = (
            "Daxter: Hola Liam,\n\n"
            "¡\n"
            "Me refieres al Funcionario. Perhaps viven en Caudete con ti.\n"
            "¡"
        )
        cleaned = OllamaProvider._clean_generated_text(dirty, prompt)
        self.assertNotIn("Daxter:", cleaned)
        self.assertNotIn("Me refieres", cleaned)
        self.assertNotIn("Funcionario", cleaned)
        self.assertNotIn("Perhaps", cleaned)
        self.assertNotIn("con ti", cleaned)
        self.assertFalse(cleaned.endswith("¡"))
        self.assertIn("Te refieres a Funcio", cleaned)


    def test_current_user_answer_is_varied(self):
        first = personality.current_user_identity("Liam", "Daxter")
        second = personality.current_user_identity("Liam", "Daxter")
        self.assertNotEqual(first, second)
        self.assertIn("Liam", first)
        self.assertIn("Liam", second)

    def test_fuzzy_carreras_resolves_to_carreres(self):
        atlas = _AtlasAI()
        atlas._prepare_entity_clarification("quien es Pepi")
        rewritten, handled = atlas._prepare_entity_clarification("Pepi Carreras")
        self.assertFalse(handled)
        self.assertIn("Pepi Carreres López", rewritten)

    def test_saray_can_resolve_her_own_mother(self):
        atlas = _AtlasAI()
        atlas._get_current_conversation_user = lambda: "Saray"
        atlas._prepare_entity_clarification("quien es Pepi")
        rewritten, handled = atlas._prepare_entity_clarification("su madre")
        self.assertFalse(handled)
        self.assertIn("Pepi Carreres López", rewritten)

    def test_verified_relationship_query_bypasses_model(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Qué relación tiene Saray con Liam?"
        )
        self.assertEqual(
            answer,
            "Saray Izquierdo Carreres es pareja de Liam.",
        )

    def test_jose_miguel_style_multiword_reference_is_not_reduced(self):
        atlas = _AtlasAI()
        atlas.people_manager.people.append(
            _Person(
                "jose_miguel",
                "José Miguel Izquierdo Catalán",
                ("José Miguel",),
            )
        )
        ambiguous = atlas._find_ambiguous_person_reference(
            "¿Cuándo nació José Miguel?"
        )
        self.assertIsNone(ambiguous)

    def test_similarity_detection_catches_repeated_answers(self):
        self.assertTrue(
            _AtlasAI._responses_are_too_similar(
                "Saray es tu pareja y vive en Caudete.",
                "Saray es tu pareja y vive en Caudete.",
            )
        )
        self.assertFalse(
            _AtlasAI._responses_are_too_similar(
                "Saray es tu pareja y vive en Caudete.",
                "Pepi es la madre de Saray.",
            )
        )

    def test_cleanup_fixes_pronouns_conjugation_and_stray_question(self):
        prompt = (
            "MENSAJE DEL USUARIO:\nquien es Saray\n\n"
            "Persona mencionada: Saray Izquierdo Carreres.\n"
            "Nombre habitual preferido: Saray.\n"
        )
        dirty = (
            "Saray es tu pareja. Eres tan suerte teniéndola a su lado. "
            "Puedo mostrar una foto nuestra juntos. ¿Cómo estás hoy? ¡"
        )
        cleaned = OllamaProvider._clean_generated_text(dirty, prompt)
        self.assertIn("tienes mucha suerte de tenerla a tu lado", cleaned.lower())
        self.assertIn("foto vuestra juntos", cleaned.lower())
        self.assertNotIn("¿Cómo estás", cleaned)
        self.assertFalse(cleaned.endswith("¡"))



    def test_relationship_description_exposes_only_cousin_for_txipi_and_liam(self):
        """La salida pública debe ocultar los matices internos de Txipi."""

        from identity.relationship import Relationship
        from identity.relationship_engine import RelationshipEngine

        relationship = Relationship(
            source_entity_id="txipi",
            source_entity_type="person",
            relationship_type="brother",
            target_entity_id="liam",
            target_entity_type="person",
            confirmed=True,
            confidence=1.0,
            notes="Dato interno confirmado.",
        )

        engine = object.__new__(RelationshipEngine)
        engine._resolve_entity_by_id = lambda entity_id, entity_type: SimpleNamespace(
            name=(
                "José Manuel Martínez Pérez"
                if entity_id == "txipi"
                else "Liam Vicente Martínez"
            )
        )

        description = engine.describe_relationship(relationship)

        self.assertIn("son primos", description.casefold())
        self.assertNotIn("hermano", description.casefold())
        self.assertNotIn("adoptivo", description.casefold())
        self.assertNotIn("afectivo", description.casefold())

    def test_relationship_description_exposes_only_cousin_for_alba_and_liam(self):
        """La salida pública debe ocultar los matices internos de Alba."""

        from identity.relationship import Relationship
        from identity.relationship_engine import RelationshipEngine

        relationship = Relationship(
            source_entity_id="alba",
            source_entity_type="person",
            relationship_type="sister",
            target_entity_id="liam",
            target_entity_type="person",
            confirmed=True,
            confidence=1.0,
            notes="Dato interno confirmado.",
        )

        engine = object.__new__(RelationshipEngine)
        engine._resolve_entity_by_id = lambda entity_id, entity_type: SimpleNamespace(
            name=(
                "Alba Martínez Pérez"
                if entity_id == "alba"
                else "Liam Vicente Martínez"
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
            source_entity_id="liam",
            source_entity_type="person",
            relationship_type="cousin",
            target_entity_id="txipi",
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
            "Liam",
        )
        user_key = _AtlasAI._response_topic_key(
            "quien soy",
            "Liam",
        )

        self.assertNotEqual(assistant_key, user_key)
        self.assertTrue(assistant_key.endswith("identidad_asistente"))
        self.assertTrue(user_key.endswith("identidad_interlocutor"))

    def test_cleanup_does_not_mutilate_sentence_after_unpunctuated_greeting(self):
        """«Hola Liam es...» debe conservar el sujeto y el contenido."""

        cleaned = OllamaProvider._clean_generated_text(
            "Hola Liam es el usuario principal de Atlas.",
            "MENSAJE DEL USUARIO:\nquien es Liam\n\n",
        )

        self.assertEqual(
            cleaned,
            "Hola Liam es el usuario principal de Atlas.",
        )

    def test_cleanup_replaces_relationship_tautology_with_safe_message(self):
        """Una relación tautológica no debe acabar en una frase incompleta."""

        cleaned = OllamaProvider._clean_generated_text(
            "La madre de Saray es la madre de Saray.",
            "MENSAJE DEL USUARIO:\nquien es la madre de Saray\n\n",
        )

        self.assertIn(
            "No he identificado correctamente quién es la madre de Saray",
            cleaned,
        )
        self.assertNotIn("la madre de Saray es.", cleaned.casefold())




    def test_who_is_my_sister_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quién es mi hermana?"
        )
        self.assertEqual(
            answer,
            "Tu hermana es Lidia Vicente Martínez.",
        )

    def test_how_is_my_girlfriend_called_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama mi novia?"
        )
        self.assertEqual(
            answer,
            "Tu novia es Saray Izquierdo Carreres.",
        )

    def test_who_is_my_mother_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quién es mi madre?"
        )
        self.assertEqual(
            answer,
            "Tu madre es María José Martínez Sanz.",
        )

    def test_sarays_brother_is_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama el hermano de Saray?"
        )
        self.assertEqual(
            answer,
            "El hermano de Saray Izquierdo Carreres "
            "es Rubén Izquierdo Carreres.",
        )

    def test_plural_siblings_are_resolved_from_graph(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quiénes son mis hermanos?"
        )
        self.assertIn("Lidia Vicente Martínez", answer)
        self.assertIn("Raúl Isidro Vicente Martínez", answer)



    def test_brother_of_my_girlfriend_uses_two_steps(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Quién es el hermano de mi novia?"
        )
        self.assertEqual(
            answer,
            "El hermano de tu novia es "
            "Rubén Izquierdo Carreres.",
        )

    def test_mother_of_my_girlfriend_uses_two_steps(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama la madre de mi novia?"
        )
        self.assertEqual(
            answer,
            "La madre de tu novia es "
            "Pepi Carreres López.",
        )

    def test_daughter_of_sarays_aunt_uses_three_steps(self):
        atlas = _AtlasAI()
        answer = atlas._answer_verified_entity_query(
            "¿Cómo se llama la hija de la tía de Saray?"
        )
        self.assertEqual(
            answer,
            "La hija de la tía de Saray Izquierdo Carreres es "
            "Noa Melinte Carreres.",
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
                "tía de Saray"
            ),
            "la tía de Saray Izquierdo Carreres",
        )


if __name__ == "__main__":
    unittest.main()

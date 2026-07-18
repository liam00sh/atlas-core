"""Pruebas para la construcción del prompt final."""

import unittest

from ai.prompts.builder import PromptBuilder


class PromptBuilderTests(unittest.TestCase):
    def setUp(self):
        self.builder = PromptBuilder("Prompt base neutral")

    def _build(self, assistant="Coco", identity_context="Identidad activa: Coco. Modo: Trabajo."):
        return self.builder.build(
            user_message="Ayúdame con Python",
            user_name="Saray",
            project_name="Proyecto Atlas",
            assistant_name=assistant,
            atlas_version="0.3.1",
            capabilities={"ai": {"enabled": True, "description": "IA local"}},
            system_information="Sistema de prueba",
            identity_context=identity_context,
            relevant_memories="Saray estudia en Alicante.",
            conversation_context="Saray: Hola",
        )

    def test_uses_dynamic_identity_not_hardcoded_daxter(self):
        prompt = self._build("Coco")
        self.assertIn("Responde ahora como Coco", prompt)
        self.assertNotIn("Responde ahora como Daxter", prompt)

    def test_contains_separated_context_sections(self):
        prompt = self._build()
        for heading in (
            "INFORMACIÓN ACTUAL DE ATLAS", "CAPACIDADES REALES DE ATLAS",
            "IDENTIDADES, PERSONALIDAD Y PERMISOS", "INFORMACIÓN REAL DEL SISTEMA",
            "RECUERDOS AUTORIZADOS Y RELEVANTES", "CONVERSACIÓN RECIENTE",
            "MENSAJE ACTUAL DEL INTERLOCUTOR",
        ):
            self.assertIn(heading, prompt)

    def test_enforces_speaker_and_assistant_gender_rules(self):
        prompt = self._build("Coco")
        self.assertIn(
            "Coco habla de sí misma en femenino",
            prompt,
        )
        self.assertIn(
            "Un nombre mencionado en la pregunta",
            prompt,
        )
        self.assertIn(
            "nunca cambia automáticamente quién habla",
            prompt,
        )

    def test_rejects_required_empty_values(self):
        with self.assertRaises(ValueError):
            self.builder.build("", "Liam", "Atlas", "Daxter", "0.3", {})
        with self.assertRaises(ValueError):
            self.builder.build("Hola", "", "Atlas", "Daxter", "0.3", {})


if __name__ == "__main__":
    unittest.main()

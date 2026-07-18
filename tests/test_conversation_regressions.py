"""Pruebas de regresión para identidad, animales y estilo de respuestas."""


import unittest
from unittest.mock import Mock, patch


from ai.providers.ollama_provider import OllamaProvider
from conversation import intent
from utils.text_normalizer import normalize_text




class ConversationRegressionTests(unittest.TestCase):
    def test_xambia_is_normalized_as_cambia(self):
        self.assertEqual(
            normalize_text("xambia a coco"),
            "cambia a coco",
        )


    def test_failed_animal_login_keeps_current_user(self):
        atlas = Mock()
        atlas.get_user.return_value = "Liam"
        animal = Mock()
        animal.name = "Funcionario"
        animal.aliases = ["Funcio"]
        atlas.people_manager.find_animal_by_name.return_value = animal


        with patch.object(intent.context, "atlas", atlas):
            response = intent.detect("ahora soy Funcio")


        self.assertIn("Funcio es un animal", response)
        self.assertIn("Sigues siendo Liam", response)
        atlas.change_user.assert_not_called()


    def test_xambia_changes_identity_without_falling_through_to_ai(self):
        atlas = Mock()
        atlas.get_user.return_value = "Liam"
        atlas.identity_manager.change_identity.return_value = True
        atlas.identity_manager.get_active_display_name.side_effect = ["Daxter", "Coco"]
        atlas.identity_manager.get_phrase.return_value = "Coco al mando."


        with patch.object(intent.context, "atlas", atlas):
            response = intent.detect("xambia a coco")


        self.assertEqual(response, "Coco al mando.")
        atlas.identity_manager.change_identity.assert_called_once_with("coco")


    def test_declaring_current_user_does_not_reinitialize_profile(self):
        atlas = Mock()
        atlas.get_user.return_value = "Liam"
        atlas.get_name.return_value = "Daxter"
        atlas.people_manager.find_animal_by_name.return_value = None
        atlas.people_manager.find_person_by_name.return_value = None

        with patch.object(intent.context, "atlas", atlas):
            response = intent.detect("soy Liam")

        self.assertIn("Liam", response)
        atlas.change_user.assert_not_called()

    def test_presentate_is_consumed_without_falling_through_to_ai(self):
        atlas = Mock()
        atlas.get_name.return_value = "Daxter"
        atlas.get_project.return_value = "Proyecto Atlas"
        with patch.object(intent.context, "atlas", atlas):
            response = intent.detect("preséntate")
        self.assertIsInstance(response, str)
        self.assertIn("Daxter", response)

    def test_response_cleaner_removes_repetitive_wrapping(self):
        response = (
            "¡Hola Liam!\n\n"
            "Saray es tu pareja.\n\n"
            "¿Cómo estás hoy? Estoy aquí para ayudarte si lo necesitas.\n\n"
            "Saludos,\nCoco"
        )
        cleaned = OllamaProvider._clean_generated_text(
            response,
            "Responde ahora como Coco. Coco habla de sí misma en femenino.",
        )
        self.assertEqual(cleaned, "Saray es tu pareja.")


    def test_response_cleaner_fixes_agreement_and_coco_gender(self):
        response = (
            "Eres muy felices juntos y estaré encantado de ayudarte."
        )
        cleaned = OllamaProvider._clean_generated_text(
            response,
            "Responde ahora como Coco. Coco habla de sí misma en femenino.",
        )
        self.assertIn("sois muy felices juntos", cleaned.casefold())
        self.assertIn("estaré encantada", cleaned)




if __name__ == "__main__":
    unittest.main()
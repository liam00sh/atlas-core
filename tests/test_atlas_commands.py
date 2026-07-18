"""Pruebas de comandos internos de identidad y modo."""

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from assistant_identity.identity_manager import IdentityManager
from assistant_identity.mode import CLASSIC_MODE, FUN_MODE, WORK_MODE
from core.atlas_commands import AtlasCommandsMixin


class CommandAtlas(AtlasCommandsMixin):
    def __init__(self, path):
        self.identity_manager = IdentityManager(preferences_path=path)
        self.identity_manager.load_user("Liam")

    def get_project(self):
        return "Proyecto Atlas"


class AtlasCommandsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.atlas = CommandAtlas(Path(self.temp_dir.name) / "preferences.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_command(self, original, normalized):
        stream = StringIO()
        with redirect_stdout(stream):
            result = self.atlas._handle_command(original, normalized)
        return result, stream.getvalue()

    def test_changes_identity_and_mode(self):
        result, _ = self.run_command("Cambia a Coco", "cambia a coco")
        self.assertTrue(result)
        self.assertEqual(self.atlas.identity_manager.get_active_identity_name(), "coco")

        result, _ = self.run_command("Modo trabajo", "modo trabajo")
        self.assertTrue(result)
        self.assertEqual(self.atlas.identity_manager.get_active_mode_name(), WORK_MODE)
        self.assertTrue(self.atlas.identity_manager.is_manual_mode_locked())

    def test_change_to_identity_resets_previous_mode(self):
        self.run_command("Cambia a modo bromista", "cambia a modo bromista")
        self.assertEqual(self.atlas.identity_manager.get_active_mode_name(), FUN_MODE)
        self.assertTrue(self.atlas.identity_manager.is_manual_mode_locked())

        self.run_command("Cambia a Coco", "cambia a coco")
        self.assertEqual(self.atlas.identity_manager.get_active_identity_name(), "coco")
        self.assertEqual(self.atlas.identity_manager.get_active_mode_name(), CLASSIC_MODE)
        self.assertFalse(self.atlas.identity_manager.is_manual_mode_locked())

    def test_new_mode_aliases_are_consumed_as_commands(self):
        aliases = {
            "cambia a modo trabajo": WORK_MODE,
            "cambia al modo trabajo": WORK_MODE,
            "cambia a modo bromista": FUN_MODE,
            "cambia a modo divertido": FUN_MODE,
            "cambia a modo normal": CLASSIC_MODE,
            "cambia a modo clasico": CLASSIC_MODE,
        }
        for command, expected_mode in aliases.items():
            with self.subTest(command=command):
                result, _ = self.run_command(command, command)
                self.assertTrue(result)
                self.assertEqual(self.atlas.identity_manager.get_active_mode_name(), expected_mode)

    def test_mode_query_is_consumed_and_does_not_change_state(self):
        self.run_command("Cambia a modo trabajo", "cambia a modo trabajo")
        before = self.atlas.identity_manager.get_state().copy()
        result, output = self.run_command("En qué modo estás", "en que modo estas")
        after = self.atlas.identity_manager.get_state()
        self.assertTrue(result)
        self.assertIn("Trabajo", output)
        self.assertEqual(after["identity"], before["identity"])
        self.assertEqual(after["current_mode"], before["current_mode"])
        self.assertEqual(after["manual_mode_lock"], before["manual_mode_lock"])

    def test_identity_query_reports_active_identity(self):
        self.run_command("Cambia a Coco", "cambia a coco")
        result, output = self.run_command("Quién eres", "quien eres")
        self.assertTrue(result)
        self.assertIn("Coco", output)
        self.assertNotIn("hablando con Daxter", output)

    def test_unlock_and_automatic_commands(self):
        self.run_command("Modo divertido", "modo divertido")
        self.run_command("Libera el modo", "libera el modo")
        self.assertFalse(self.atlas.identity_manager.is_manual_mode_locked())
        self.run_command("Desactiva el cambio automático", "desactiva el cambio automatico")
        self.assertFalse(self.atlas.identity_manager.is_automatic_mode_enabled())

    def test_unknown_text_is_not_consumed(self):
        result, _ = self.run_command("Esto es conversación", "esto es conversacion")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

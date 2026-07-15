"""Pruebas de preferencias, identidades y modos del asistente."""

import json
import tempfile
import unittest
from pathlib import Path

from assistant_identity.identity_manager import IdentityManager
from assistant_identity.mode import CLASSIC_MODE, EMPATHETIC_MODE, FUN_MODE, WORK_MODE


class IdentityManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "preferences.json"
        self.manager = IdentityManager(preferences_path=self.path)
        self.manager.load_user("Liam")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_state(self):
        self.assertEqual(self.manager.get_current_user(), "liam")
        self.assertEqual(self.manager.get_active_identity_name(), "daxter")
        self.assertEqual(self.manager.get_active_mode_name(), CLASSIC_MODE)
        self.assertFalse(self.manager.is_manual_mode_locked())
        self.assertFalse(self.manager.is_temporary_mode_active())
        self.assertTrue(self.manager.is_automatic_mode_enabled())

    def test_identity_change_persists(self):
        self.assertTrue(self.manager.change_identity("coco"))
        reloaded = IdentityManager(preferences_path=self.path)
        reloaded.load_user("Liam")
        self.assertEqual(reloaded.get_active_identity_name(), "coco")
        self.assertEqual(reloaded.get_active_mode_name(), CLASSIC_MODE)

    def test_identity_change_resets_mode_and_locks(self):
        self.manager.set_mode(FUN_MODE, manual=True)
        self.assertTrue(self.manager.is_manual_mode_locked())
        self.assertEqual(self.manager.get_active_mode_name(), FUN_MODE)

        self.assertTrue(self.manager.change_identity("coco"))
        self.assertEqual(self.manager.get_active_identity_name(), "coco")
        self.assertEqual(self.manager.get_active_mode_name(), CLASSIC_MODE)
        self.assertEqual(self.manager.get_default_mode_name(), CLASSIC_MODE)
        self.assertFalse(self.manager.is_manual_mode_locked())
        self.assertFalse(self.manager.is_temporary_mode_active())

        self.manager.set_mode(WORK_MODE, manual=True)
        self.assertTrue(self.manager.change_identity("daxter"))
        self.assertEqual(self.manager.get_active_mode_name(), CLASSIC_MODE)
        self.assertFalse(self.manager.is_manual_mode_locked())

    def test_manual_mode_blocks_automatic_changes(self):
        self.assertTrue(self.manager.set_mode(WORK_MODE, manual=True))
        self.assertTrue(self.manager.is_manual_mode_locked())
        self.manager.apply_automatic_mode("Estoy muy triste y necesito apoyo")
        self.assertEqual(self.manager.get_active_mode_name(), WORK_MODE)

    def test_unlock_allows_automatic_temporary_mode(self):
        self.manager.set_mode(WORK_MODE, manual=True)
        self.manager.unlock_manual_mode()
        self.manager.set_automatic_mode(True)
        selection = self.manager.apply_automatic_mode(
            "Estoy muy triste, me siento fatal y necesito ayuda; "
            "quiero desahogarme y que me escuches."
        )
        self.assertEqual(selection.mode_name, EMPATHETIC_MODE)
        self.assertEqual(self.manager.get_active_mode_name(), EMPATHETIC_MODE)
        self.assertTrue(self.manager.is_temporary_mode_active())

    def test_return_to_default_mode_clears_transient_state(self):
        self.manager.set_mode(FUN_MODE, manual=True)
        self.manager.return_to_default_mode()
        self.assertEqual(self.manager.get_active_mode_name(), CLASSIC_MODE)
        self.assertFalse(self.manager.is_manual_mode_locked())
        self.assertFalse(self.manager.is_temporary_mode_active())

    def test_preferences_are_independent_per_user(self):
        self.manager.change_identity("coco")
        self.manager.set_mode(FUN_MODE, manual=True)

        self.manager.load_user("Saray")
        self.assertEqual(self.manager.get_active_identity_name(), "daxter")
        self.assertEqual(self.manager.get_active_mode_name(), CLASSIC_MODE)

        self.manager.load_user("Liam")
        self.assertEqual(self.manager.get_active_identity_name(), "coco")
        self.assertEqual(self.manager.get_active_mode_name(), FUN_MODE)
        self.assertIn("liam", json.loads(self.path.read_text(encoding="utf-8")))

    def test_both_identities_support_all_modes_and_context(self):
        for identity_name in ("daxter", "coco"):
            self.assertTrue(self.manager.change_identity(identity_name))
            for mode_name in (CLASSIC_MODE, WORK_MODE, FUN_MODE, EMPATHETIC_MODE):
                self.assertTrue(self.manager.set_mode(mode_name, manual=True))
                context = self.manager.build_prompt_context()
                self.assertIn(self.manager.get_active_display_name(), context)
                self.assertIn(self.manager.get_active_mode_label(), context)

    def test_unknown_identity_or_mode_does_not_change_state(self):
        before = self.manager.get_state().copy()
        self.assertFalse(self.manager.change_identity("desconocida"))
        self.assertFalse(self.manager.set_mode("desconocido"))
        after = self.manager.get_state()
        self.assertEqual(after["identity"], before["identity"])
        self.assertEqual(after["current_mode"], before["current_mode"])


if __name__ == "__main__":
    unittest.main()

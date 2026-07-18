"""Pruebas del mixin de usuarios y sincronización de identidades."""

import unittest
from unittest.mock import Mock

from core.atlas_users import AtlasUsersMixin
from core.user_manager import UserManager


class AtlasUsersMixinTests(unittest.TestCase):
    def test_get_name_uses_active_assistant_identity(self):
        atlas = object.__new__(AtlasUsersMixin)
        atlas.name = "Daxter"
        atlas.identity_manager = Mock()
        atlas.identity_manager.get_active_display_name.return_value = "Coco"
        self.assertEqual(atlas.get_name(), "Coco")

    def test_get_name_has_safe_startup_fallback(self):
        atlas = object.__new__(AtlasUsersMixin)
        atlas.name = "Daxter"
        self.assertEqual(atlas.get_name(), "Daxter")

    def test_change_user_synchronizes_all_user_scoped_services(self):
        atlas = object.__new__(AtlasUsersMixin)
        atlas.users = Mock()
        atlas.users.get_current_user.side_effect = ["Liam", "Saray"]
        atlas.confirmations = Mock()
        atlas.confirmations.has_pending_confirmation.return_value = False
        atlas.conversation_identity = Mock()
        atlas.identity_manager = Mock()
        atlas._get_ai_context_for_user = Mock()
        atlas.change_user("Saray")
        atlas.users.change_user.assert_called_once_with("Saray")
        atlas.conversation_identity.set_authenticated_user.assert_called_once_with("Saray")
        atlas.conversation_identity.identify_person.assert_called_once_with("Saray")
        atlas.identity_manager.load_user.assert_called_once_with("Saray")

    def test_animal_cannot_become_active_user(self):
        atlas = object.__new__(AtlasUsersMixin)
        atlas.users = Mock()
        atlas.users.get_current_user.return_value = "Liam"
        atlas.confirmations = Mock()
        atlas.people_manager = Mock()
        atlas.people_manager.find_animal_by_name.return_value = Mock(name="Funcio")

        result = atlas.change_user("Funcio")

        self.assertFalse(result)
        atlas.users.change_user.assert_not_called()

    def test_animal_cannot_have_user_profile(self):
        users = UserManager()
        users.set_profile_validator(
            lambda name: str(name).strip().casefold() != "funcio"
        )

        with self.assertRaises(ValueError):
            users.get_profile("Funcio")

        with self.assertRaises(ValueError):
            users.change_user("Funcio")

        self.assertEqual(users.get_current_user(), "Liam")
        self.assertNotIn("funcio", users.profiles)


if __name__ == "__main__":
    unittest.main()

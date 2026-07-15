"""Pruebas del mixin de usuarios y sincronización de identidades."""

import unittest
from unittest.mock import Mock

from core.atlas_users import AtlasUsersMixin


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


if __name__ == "__main__":
    unittest.main()

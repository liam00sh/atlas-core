"""Pruebas aisladas del mixin de IA sin invocar Ollama."""

import unittest
from unittest.mock import Mock

from core.atlas_ai import AtlasAIMixin


class AtlasAIMixinTests(unittest.TestCase):
    def test_normalizes_context_user(self):
        self.assertEqual(AtlasAIMixin._normalize_ai_context_user("  Liam  "), "liam")
        with self.assertRaises(ValueError):
            AtlasAIMixin._normalize_ai_context_user("   ")

    def test_current_conversation_user_prefers_interlocutor(self):
        atlas = object.__new__(AtlasAIMixin)
        atlas.conversation_identity = Mock()
        atlas.conversation_identity.get_conversation_owner.return_value = "Saray"
        atlas.get_user = Mock(return_value="Liam")
        self.assertEqual(atlas._get_current_conversation_user(), "Saray")

    def test_falls_back_to_authenticated_user(self):
        atlas = object.__new__(AtlasAIMixin)
        atlas.conversation_identity = Mock()
        atlas.conversation_identity.get_conversation_owner.return_value = None
        atlas.get_user = Mock(return_value="Liam")
        self.assertEqual(atlas._get_current_conversation_user(), "Liam")

    def test_permissions_use_permission_viewer_not_session_owner(self):
        atlas = object.__new__(AtlasAIMixin)
        atlas.conversation_identity = Mock()
        atlas.conversation_identity.get_permission_viewer.return_value = "Saray"
        atlas.users = Mock()
        atlas.users.get_profile.return_value = {"roles": []}
        atlas.get_user = Mock(return_value="Liam")
        self.assertFalse(atlas.can_manage_user_contexts())
        atlas.users.get_profile.assert_called_once_with("Saray")


if __name__ == "__main__":
    unittest.main()

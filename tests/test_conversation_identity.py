"""Pruebas para la separación entre sesión e interlocutor."""

import tempfile
import unittest
from pathlib import Path

from identity.conversation_identity import ConversationIdentity
from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.visitor_manager import VisitorManager


class ConversationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.people = PeopleManager(IdentityStorage(Path(self.temp_dir.name)))
        self.Alex = self.people.create_user_person("Alex Romero", "Alex", aliases=["Alex"])
        self.alias_ejemplo_44_01 = self.people.create_user_person("Vega Ferrer", "Vega", aliases=["Vega"])
        self.identity = ConversationIdentity(self.people, VisitorManager(self.people))
        self.identity.set_authenticated_user("Alex")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_uses_user_profile_as_canonical_identity_key(self):
        self.identity.set_current_person(self.Alex)
        self.assertEqual(self.identity.get_current_identity_key(), "Alex")
        self.assertEqual(self.identity.get_permission_viewer(), "Alex")

    def test_guest_speaker_does_not_inherit_authenticated_user(self):
        self.identity.set_current_person(self.alias_ejemplo_44_01)
        self.assertEqual(self.identity.get_authenticated_user(), "Alex")
        self.assertEqual(self.identity.get_conversation_owner(), "Vega")
        self.assertEqual(self.identity.get_permission_viewer(), "Vega")
        self.assertFalse(self.identity.is_authenticated_user_speaking())

    def test_restore_authenticated_user(self):
        self.identity.set_current_person(self.alias_ejemplo_44_01)
        restored = self.identity.restore_authenticated_user()
        self.assertEqual(restored.id, self.Alex.id)
        self.assertTrue(self.identity.is_authenticated_user_speaking())

    def test_prompt_context_names_both_roles(self):
        self.identity.set_current_person(self.alias_ejemplo_44_01)
        context = self.identity.build_prompt_context()
        self.assertIn("Alex", context)
        self.assertIn("Vega", context)


if __name__ == "__main__":
    unittest.main()

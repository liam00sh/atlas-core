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
        self.liam = self.people.create_user_person("Liam Vicente Martínez", "Liam", aliases=["Liam"])
        self.saray = self.people.create_user_person("Saray Izquierdo Carreres", "Saray", aliases=["Saray"])
        self.identity = ConversationIdentity(self.people, VisitorManager(self.people))
        self.identity.set_authenticated_user("Liam")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_uses_user_profile_as_canonical_identity_key(self):
        self.identity.set_current_person(self.liam)
        self.assertEqual(self.identity.get_current_identity_key(), "Liam")
        self.assertEqual(self.identity.get_permission_viewer(), "Liam")

    def test_guest_speaker_does_not_inherit_authenticated_user(self):
        self.identity.set_current_person(self.saray)
        self.assertEqual(self.identity.get_authenticated_user(), "Liam")
        self.assertEqual(self.identity.get_conversation_owner(), "Saray")
        self.assertEqual(self.identity.get_permission_viewer(), "Saray")
        self.assertFalse(self.identity.is_authenticated_user_speaking())

    def test_restore_authenticated_user(self):
        self.identity.set_current_person(self.saray)
        restored = self.identity.restore_authenticated_user()
        self.assertEqual(restored.id, self.liam.id)
        self.assertTrue(self.identity.is_authenticated_user_speaking())

    def test_prompt_context_names_both_roles(self):
        self.identity.set_current_person(self.saray)
        context = self.identity.build_prompt_context()
        self.assertIn("Liam", context)
        self.assertIn("Saray", context)


if __name__ == "__main__":
    unittest.main()

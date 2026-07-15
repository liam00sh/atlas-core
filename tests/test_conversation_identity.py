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
        self.REDACTED_f73137d930c3 = self.people.create_user_person("REDACTED_46087f8d7037", "REDACTED_2c7b6821719d", aliases=["REDACTED_2c7b6821719d"])
        self.REDACTED_7b9528898599 = self.people.create_user_person("REDACTED_8762331d93e2", "REDACTED_bc04a68d9192", aliases=["REDACTED_bc04a68d9192"])
        self.identity = ConversationIdentity(self.people, VisitorManager(self.people))
        self.identity.set_authenticated_user("REDACTED_2c7b6821719d")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_uses_user_profile_as_canonical_identity_key(self):
        self.identity.set_current_person(self.REDACTED_f73137d930c3)
        self.assertEqual(self.identity.get_current_identity_key(), "REDACTED_2c7b6821719d")
        self.assertEqual(self.identity.get_permission_viewer(), "REDACTED_2c7b6821719d")

    def test_guest_speaker_does_not_inherit_authenticated_user(self):
        self.identity.set_current_person(self.REDACTED_7b9528898599)
        self.assertEqual(self.identity.get_authenticated_user(), "REDACTED_2c7b6821719d")
        self.assertEqual(self.identity.get_conversation_owner(), "REDACTED_bc04a68d9192")
        self.assertEqual(self.identity.get_permission_viewer(), "REDACTED_bc04a68d9192")
        self.assertFalse(self.identity.is_authenticated_user_speaking())

    def test_restore_authenticated_user(self):
        self.identity.set_current_person(self.REDACTED_7b9528898599)
        restored = self.identity.restore_authenticated_user()
        self.assertEqual(restored.id, self.REDACTED_f73137d930c3.id)
        self.assertTrue(self.identity.is_authenticated_user_speaking())

    def test_prompt_context_names_both_roles(self):
        self.identity.set_current_person(self.REDACTED_7b9528898599)
        context = self.identity.build_prompt_context()
        self.assertIn("REDACTED_2c7b6821719d", context)
        self.assertIn("REDACTED_bc04a68d9192", context)


if __name__ == "__main__":
    unittest.main()

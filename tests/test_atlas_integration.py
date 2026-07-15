"""Pruebas de humo e integración de los subsistemas principales."""

import tempfile
import unittest
from pathlib import Path

from assistant_identity.identity_manager import IdentityManager
from assistant_identity.mode import CLASSIC_MODE, FUN_MODE, WORK_MODE
from identity.conversation_identity import ConversationIdentity
from identity.family_initializer import FamilyInitializer
from identity.family_service import FamilyService
from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.relationship_engine import RelationshipEngine
from identity.visitor_manager import VisitorManager


class AtlasSubsystemIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.storage = IdentityStorage(root / "identity")
        self.people = PeopleManager(self.storage)
        self.relationships = RelationshipEngine(self.people, self.storage)
        FamilyInitializer(self.people, self.relationships).initialize()
        self.family = FamilyService(self.people, self.relationships)
        self.conversation = ConversationIdentity(self.people, VisitorManager(self.people))
        self.assistant = IdentityManager(preferences_path=root / "assistant_preferences.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_liam_session_with_saray_speaking_keeps_scopes_separate(self):
        self.conversation.set_authenticated_user("Liam")
        self.conversation.identify_person("Saray")
        self.assistant.load_user(self.conversation.get_conversation_owner())
        self.assertEqual(self.conversation.get_authenticated_user(), "Liam")
        self.assertEqual(self.conversation.get_permission_viewer(), "Saray")
        self.assertEqual(self.assistant.get_current_user(), "saray")

    def test_family_and_identity_survive_reinitialization(self):
        liam = self.people.find_person_by_name("Nerea Vicente Martínez")
        self.assertEqual(liam.name, "Liam Vicente Martínez")
        first_count = self.relationships.get_relationship_count()
        FamilyInitializer(self.people, self.relationships).initialize()
        self.assertEqual(self.relationships.get_relationship_count(), first_count)
        self.assertTrue(self.family.describe_person_family("Liam Vicente Martínez"))

    def test_assistant_identity_and_mode_context_is_dynamic(self):
        self.assistant.load_user("Liam")
        self.assistant.change_identity("coco")
        self.assistant.set_mode(WORK_MODE, manual=True)
        context = self.assistant.build_prompt_context()
        self.assertIn("Coco", context)
        self.assertIn("Trabajo", context)

    def test_identity_switch_does_not_leak_mode_between_daxter_and_coco(self):
        self.assistant.load_user("Liam")
        self.assistant.set_mode(FUN_MODE, manual=True)
        self.assertEqual(self.assistant.get_active_mode_name(), FUN_MODE)

        self.assistant.change_identity("coco")
        self.assertEqual(self.assistant.get_active_identity_name(), "coco")
        self.assertEqual(self.assistant.get_active_mode_name(), CLASSIC_MODE)
        self.assertFalse(self.assistant.is_manual_mode_locked())

        self.assistant.set_mode(WORK_MODE, manual=True)
        self.assistant.change_identity("daxter")
        self.assertEqual(self.assistant.get_active_identity_name(), "daxter")
        self.assertEqual(self.assistant.get_active_mode_name(), CLASSIC_MODE)

    def test_person_and_animal_relations_are_queryable_together(self):
        description = self.family.describe_person_family("Liam Vicente Martínez")
        self.assertIn("Saray", description)
        self.assertIn("Don Gato", description)

        estrella_connections = self.family.find_connection("Liam Vicente Martínez", "Estrella")
        self.assertIsInstance(estrella_connections, list)

    def test_process_source_handles_commands_before_automatic_mode(self):
        atlas_source = (
            Path(__file__).resolve().parents[1] / "core" / "atlas.py"
        ).read_text(encoding="utf-8")
        process_start = atlas_source.index("    def process(")
        process_source = atlas_source[process_start:]
        command_position = process_source.index("self._handle_command(")
        automatic_position = process_source.index(".apply_automatic_mode(")
        self.assertLess(command_position, automatic_position)


if __name__ == "__main__":
    unittest.main()

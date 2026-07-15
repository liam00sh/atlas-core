"""Pruebas para VisitorManager."""

import tempfile
import unittest
from pathlib import Path

from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.person_status import GUEST, KNOWN, REGULAR
from identity.visitor_manager import VisitorManager


class VisitorManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.people = PeopleManager(IdentityStorage(Path(self.temp_dir.name)))
        self.visitors = VisitorManager(self.people)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registers_new_visitor_and_visits(self):
        person = self.visitors.register_new_visitor("Invitado")
        self.assertIsNotNone(person)
        self.assertEqual(person.status, GUEST)

        self.assertEqual(
            self.people.get_person_by_id(person.id).encounter_count,
            1,
        )

        self.visitors.register_visit(
            person.id,
            "2026-07-14T10:00:00",
        )
        self.assertEqual(
            self.people.get_person_by_id(person.id).encounter_count,
            2,
        )

    def test_promotion_requires_confirmation(self):
        person = self.visitors.register_new_visitor("Habitual")
        self.assertIsNotNone(person)
        self.assertEqual(person.status, GUEST)

        self.visitors.register_visit(
            person.id,
            "2026-07-12T10:00:00",
        )
        self.assertTrue(self.visitors.has_pending_promotion(person.id))

        promoted = self.visitors.confirm_promotion(person.id)
        self.assertIsNotNone(promoted)
        self.assertEqual(
            self.people.get_person_by_id(person.id).status,
            KNOWN,
        )

        for day in (13, 14, 15):
            self.visitors.register_visit(
                person.id,
                f"2026-07-{day:02d}T10:00:00",
            )

        self.assertTrue(self.visitors.has_pending_promotion(person.id))

        promoted = self.visitors.confirm_promotion(person.id)
        self.assertIsNotNone(promoted)
        self.assertEqual(
            self.people.get_person_by_id(person.id).status,
            REGULAR,
        )


if __name__ == "__main__":
    unittest.main()

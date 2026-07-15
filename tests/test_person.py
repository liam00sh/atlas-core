"""Pruebas unitarias para identity.person."""

import unittest

from identity.person import Person
from identity.person_status import GUEST, USER


class PersonTests(unittest.TestCase):
    def test_normalizes_name_aliases_and_summary(self):
        person = Person(
            name="  REDACTED_46087f8d7037  ",
            aliases=["REDACTED_2c7b6821719d", " REDACTED_f73137d930c3 ", "", "REDACTED_49d9fe5d7698"],
            summary="  Usuario principal  ",
        )
        self.assertEqual(person.name, "REDACTED_46087f8d7037")
        self.assertEqual(person.aliases, ["REDACTED_2c7b6821719d", "REDACTED_49d9fe5d7698"])
        self.assertEqual(person.summary, "Usuario principal")
        self.assertTrue(person.matches_name("REDACTED_f73137d930c3"))
        self.assertTrue(person.matches_name("REDACTED_76b53ef7b2bf"))

    def test_rejects_invalid_data(self):
        with self.assertRaises(ValueError):
            Person(name="")
        with self.assertRaises(ValueError):
            Person(name="REDACTED_2c7b6821719d", status="invalid")
        with self.assertRaises(ValueError):
            Person(name="REDACTED_2c7b6821719d", encounter_count=-1)
        with self.assertRaises(ValueError):
            Person(name="REDACTED_2c7b6821719d", status=USER)

    def test_alias_encounters_and_serialization(self):
        person = Person(name="REDACTED_bc04a68d9192", status=GUEST)
        self.assertTrue(person.add_alias("REDACTED_53b1fb446230"))
        self.assertFalse(person.add_alias("REDACTED_3a6d64c24cf8"))
        person.register_encounter("2026-07-14T12:00:00")
        self.assertEqual(person.encounter_count, 1)
        restored = Person.from_dict(person.to_dict())
        self.assertEqual(restored.to_dict(), person.to_dict())

    def test_linking_user_profile_sets_user_status(self):
        person = Person(name="REDACTED_bc04a68d9192")
        person.link_user_profile("REDACTED_bc04a68d9192")
        self.assertTrue(person.is_user())
        self.assertEqual(person.status, USER)
        self.assertEqual(person.user_profile, "REDACTED_bc04a68d9192")


if __name__ == "__main__":
    unittest.main()
